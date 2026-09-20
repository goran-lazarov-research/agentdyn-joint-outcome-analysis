"""Create the portable joint-outcome analysis package; exclude articles and QA."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'package_stage' / 'ITT2026_Pilot_podaci_i_kod'
OUT = ROOT.parent / 'itt2026_output' / 'ITT2026_Pilot_podaci_i_kod.zip'
if STAGE.exists():
    shutil.rmtree(STAGE)
STAGE.mkdir(parents=True, exist_ok=True)

manifest = json.loads((ROOT / 'data/pilot_manifest.json').read_text())
selected = {item['path'] for item in manifest['jobs']}
copy_paths = [
    'README.md', 'requirements.txt', 'REPRODUCTION.json',
    'data/pilot_manifest.json', 'data/download_report.json',
    'analysis/analyze_pilot.py', 'analysis/download_pilot.py',
    'analysis/build_documents.py',
    'analysis/package_pilot.py',
    'analysis/results/pilot_outcomes.json',
    'analysis/results/pilot_summary.json',
    'analysis/results/published_table3.json',
    'analysis/results/pilot_joint_outcomes.png',
    'analysis/results/pilot_joint_outcomes.svg',
    'sources/agentdyn_commit.json', 'sources/agentdyn_table3.html',
    'sources/AgentDyn_LICENSE.txt', 'sources/base_tasks.py',
    'sources/task_suite.py', 'sources/benchmark.py',
    'extended/analysis_plan.json',
    'extended/analysis/analyze_extended.py',
    'extended/analysis/build_empirical_manuscript.py',
    'extended/analysis/finalize_itt2026.py',
    'extended/analysis/apply_itt2026_template.py',
    'extended/template/conference-template-a4.docx',
    'extended/template_alignment.json',
    'extended/document_validation.json',
    'extended/sources/published_numeric_tables.html',
    'extended/results/published_marginals.json',
    'extended/results/extended_results.json',
    'extended/results/joint_bounds_gpt4o.png',
    'extended/results/joint_bounds_gpt4o.svg',
    'extended/results/joint_bounds_ieee.png',
    'extended/results/joint_bounds_ieee.svg',
    'extended/results/resolved_pairs.png',
    'extended/results/resolved_pairs.svg',
]
copy_paths += ['data/raw/' + path for path in sorted(selected)]
for relative in copy_paths:
    target = STAGE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / relative, target)

tree = json.loads((ROOT / 'sources/agentdyn_tree.json').read_text())
subset = {key: tree[key] for key in ['sha', 'url', 'truncated']}
subset['tree'] = [item for item in tree['tree'] if item['path'] in selected]
assert len(subset['tree']) == 288
subset['package_note'] = (
    'Selected entries only, filtered from the truncated upstream inventory. '
    'Not a complete repository tree. The original API sha field identifies '
    'the requested revision; agentdyn_commit.json records the commit tree hash.'
)
(STAGE / 'sources/agentdyn_tree.json').write_text(json.dumps(subset, indent=2))

provenance = {
    'package_checkpoint': '2026-09-16',
    'source_repository': manifest['source_repository'],
    'commit': manifest['commit'],
    'raw_file_url_pattern': 'https://raw.githubusercontent.com/SaFo-Lab/AgentDyn/{commit}/{source_path}',
    'selected_records': 288,
    'attacked_records': 192,
    'clean_records': 96,
    'distinct_user_tasks': 12,
    'fresh_model_executions': 0,
    'published_tables': {
        'source': 'https://arxiv.org/html/2602.03117v3',
        'tables': list(range(9, 18)),
        'reported_configurations': 122,
        'suite_configuration_rows': 366,
        'primary_conditions': 120,
        'within_model_pairs': 540,
        'note': 'Published marginals; distinct from the 288-log pilot. Full raw archive not reanalyzed.',
    },
    'sampling_timestamp': manifest['sampling_time_utc'],
    'sampling_seed': manifest['sampling_seed'],
    'reference_source_paths': {
        'base_tasks.py': 'src/agentdojo/base_tasks.py',
        'task_suite.py': 'src/agentdojo/task_suite/task_suite.py',
        'benchmark.py': 'src/agentdojo/benchmark.py',
    },
    'outcome_convention': 'Attacked security=True means injection objective success.',
    'analysis_environment': {'python': '3.12.14', 'requirements': 'requirements.txt'},
}
# Preserve exact upstream paths instead of assuming a source directory layout.
for name in list(provenance['reference_source_paths']):
    content = (ROOT / 'sources' / name).read_bytes()
    blob = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
    matches = [entry['path'] for entry in tree['tree'] if entry.get('sha') == blob]
    provenance['reference_source_paths'][name] = matches or 'Source path not resolved from truncated inventory'
(STAGE / 'PROVENANCE.json').write_text(json.dumps(provenance, indent=2))

files = sorted(path for path in STAGE.rglob('*') if path.is_file()
               and path.name != 'CHECKSUMS.sha256')
(STAGE / 'CHECKSUMS.sha256').write_text(''.join(
    hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(STAGE).as_posix() + '\n'
    for path in files
))
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(STAGE.parent).as_posix())
print(json.dumps({'file': str(OUT), 'bytes': OUT.stat().st_size,
                  'source_logs': len(selected), 'files': len(files) + 1}))
