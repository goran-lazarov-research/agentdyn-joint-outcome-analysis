"""Download a predetermined sample of public AgentDyn logs; never run an agent."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import random
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TREE = json.loads((ROOT / 'sources/agentdyn_tree.json').read_text())
COMMIT = TREE['sha']
SEED = 20260915
MODELS = ['gpt-4o-2024-08-06', 'google_gemini-2.5-pro']
DEFENSES = {'none': '', 'spotlighting': '-spotlighting_with_delimiting',
            'tool_filter': '-tool_filter', 'progent': '-progent'}
SUITES = {'shopping': 9, 'github': 9, 'dailylife': 10}
INDEX = {x['path']: x for x in TREE['tree'] if x['type'] == 'blob'}
rng = random.Random(SEED)
selection = {}
for suite, attack_count in SUITES.items():
    selection[suite] = {}
    for task in sorted(rng.sample(range(20), 4)):
        selection[suite][str(task)] = sorted(rng.sample(range(attack_count), 2))

jobs = []
for model in MODELS:
    for defense, suffix in DEFENSES.items():
        for suite, tasks in selection.items():
            for task, attacks in tasks.items():
                prefix = f'runs/{model}{suffix}/{suite}/user_task_{task}'
                for attack in [None] + attacks:
                    end = 'none/none.json' if attack is None else f'important_instructions/injection_task_{attack}.json'
                    path = f'{prefix}/{end}'
                    if path not in INDEX:
                        raise RuntimeError(f'Missing predetermined path in repository tree: {path}')
                    jobs.append({'model': model, 'defense': defense, 'suite': suite,
                                 'task_id': f'user_task_{task}', 'attack_id': attack,
                                 'path': path, 'git_blob_sha1': INDEX[path]['sha'],
                                 'bytes_expected': INDEX[path]['size']})

manifest = {'source_repository': 'https://github.com/SaFo-Lab/AgentDyn',
            'commit': COMMIT, 'repository_tree_truncated': TREE['truncated'],
            'sampling_seed': SEED, 'tasks_per_suite': 4, 'attacks_per_task': 2,
            'sampling_frame': 'user_task_0 through user_task_19 in each suite',
            'sampling_time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'selection': selection, 'expected_files': len(jobs), 'jobs': jobs}
manifest_path = ROOT / 'data/pilot_manifest.json'
if manifest_path.exists():
    previous = json.loads(manifest_path.read_text())
    assert previous['selection'] == manifest['selection'] and previous['jobs'] == jobs
    manifest = previous  # Preserve the original selection timestamp on transfer retries.
else:
    manifest_path.write_text(json.dumps(manifest, indent=2))
print(f'Selection saved before outcomes: {len(jobs)} files; {selection}', flush=True)

def download(job):
    target = ROOT / 'data/raw' / job['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f'https://raw.githubusercontent.com/SaFo-Lab/AgentDyn/{COMMIT}/{job["path"]}'
    if not target.exists():
        p = subprocess.run(['curl', '-sS', '-L', '--fail', '--retry', '1', '--connect-timeout',
                            '15', '--max-time', '45', url, '-o', str(target)], capture_output=True)
        if p.returncode:
            return {'path': job['path'], 'ok': False, 'error': f'curl exit {p.returncode}'}
    raw = target.read_bytes()
    blob = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    if blob != job['git_blob_sha1']:
        return {'path': job['path'], 'ok': False, 'error': 'Git blob hash mismatch'}
    json.loads(raw)
    return {'path': job['path'], 'ok': True, 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}

done = []
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for i, result in enumerate(pool.map(download, jobs), 1):
        done.append(result)
        if i % 32 == 0 or i == len(jobs):
            print(f'Downloaded {i}/{len(jobs)}; failures {sum(not r["ok"] for r in done)}', flush=True)
(ROOT / 'data/download_report.json').write_text(json.dumps(done, indent=2))
if any(not r['ok'] for r in done):
    raise SystemExit('Some predetermined files could not be downloaded; inspect the report.')
