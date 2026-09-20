"""Secondary analysis of published marginals and an archived-log pilot.

All inputs are local. This program never calls a model or downloads data.
Identification intervals quantify missing dependence, not sampling error.
"""
from pathlib import Path
import itertools
import json
import os
import collections
import math

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
OUT = ROOT / 'results'
OUT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(WORK / 'analysis/mpl_cache'))
import numpy as np
from lxml import html
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def native(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)

EPS = 0.005  # half of one displayed hundredth of a percentage point
SUITES = ['Shopping', 'Github', 'Dailylife']
DEFENSES = ['None', 'Prompt Sandwiching', 'Spotlighting', 'ProtectAI',
            'PIGuard', 'PromptGuard2', 'Tool Filter', 'CaMeL', 'Progent', 'DRIFT']
source = html.parse(str(ROOT / 'sources/published_numeric_tables.html'))


def expand_table(number):
    figure = source.xpath(f'//figure[@id="A7.T{number}"]')[0]
    grid, rows = {}, []
    for ri, tr in enumerate(figure.xpath('.//table//tr')):
        ci = 0
        for cell in tr.xpath('./td|./th'):
            while (ri, ci) in grid:
                ci += 1
            value = ' '.join(' '.join(cell.itertext()).split())
            for rr in range(ri, ri + int(cell.get('rowspan', '1'))):
                for cc in range(ci, ci + int(cell.get('colspan', '1'))):
                    grid[rr, cc] = value
            ci += int(cell.get('colspan', '1'))
        rows.append([grid.get((ri, c), '') for c in range(6)])
    assert rows[0] == ['Defense', 'Model', 'Overall', *SUITES], rows[0]
    output = []
    for row in rows[1:]:
        output.append({'defense': row[0], 'model': row[1], 'table': number,
                       'reported_overall': float(row[2]),
                       'suites': dict(zip(SUITES, map(float, row[3:]))),
                       'source_cells': row})
    return output


metrics = {}
for metric, numbers in [('clean', range(9, 12)), ('utility', range(12, 15)),
                        ('asr', range(15, 18))]:
    rows = [r for number in numbers for r in expand_table(number)]
    metrics[metric] = {(r['model'], r['defense']): r for r in rows}
    assert len(rows) == len(metrics[metric]) == 122
assert set(metrics['clean']) == set(metrics['utility']) == set(metrics['asr'])


def interval(value):
    return max(0.0, value - EPS), min(100.0, value + EPS)


def bounds(u, a, rounding=True):
    if rounding:
        ulo, uhi = interval(u)
        alo, ahi = interval(a)
    else:
        ulo = uhi = u
        alo = ahi = a
    return [max(0.0, ulo - ahi), min(uhi, 100.0 - alo)]


# Exhaustive checks at feasible Bernoulli tables, independent of published data.
for n00 in range(5):
    for n01 in range(5):
        for n10 in range(5):
            for n11 in range(5):
                n = n00+n01+n10+n11
                if n:
                    u = 100*(n10+n11)/n
                    a = 100*(n01+n11)/n
                    lo, hi = bounds(u, a, False)
                    assert lo-1e-10 <= 100*n10/n <= hi+1e-10

conditions, discrepancies, extracted = [], [], []
for key in metrics['utility']:
    model, defense = key
    item = {'model': model, 'defense': defense, 'suites': {}}
    for metric in metrics:
        row = metrics[metric][key]
        values = list(row['suites'].values())
        assert all(0 <= x <= 100 for x in values + [row['reported_overall']])
        macro = float(np.mean(values))
        item[metric+'_macro_pct'] = macro
        item[metric+'_reported_overall_pct'] = row['reported_overall']
        deviation = row['reported_overall']-macro
        # Difference above 0.01 pp cannot be explained by independent 0.005 rounding.
        if abs(deviation) > 0.0100001:
            discrepancies.append({'model': model, 'defense': defense,
                                  'metric': metric, 'table': row['table'],
                                  'reported_overall': row['reported_overall'],
                                  'mean_of_suite_cells': macro,
                                  'difference_pp': deviation})
        extracted.append({'metric': metric, **row})
    for suite in SUITES:
        u = metrics['utility'][key]['suites'][suite]
        a = metrics['asr'][key]['suites'][suite]
        item['suites'][suite] = {'utility_pct': u, 'asr_pct': a,
                                'joint_bounds_pct': bounds(u, a)}
    u, a = item['utility_macro_pct'], item['asr_macro_pct']
    item['pooled_joint_bounds_pct'] = bounds(u, a)
    item['stratified_joint_bounds_pct'] = list(np.mean(
        [item['suites'][s]['joint_bounds_pct'] for s in SUITES], axis=0))
    lo, hi = item['stratified_joint_bounds_pct']
    plo, phi = item['pooled_joint_bounds_pct']
    assert plo-1e-9 <= lo <= hi <= phi+1e-9
    item['pooled_width_pp'] = phi-plo
    item['stratified_width_pp'] = hi-lo
    item['width_reduction_pp'] = (phi-plo)-(hi-lo)
    item['rectangular_panel'] = defense in DEFENSES
    conditions.append(item)

panel = [r for r in conditions if r['rectangular_panel']]
models = list(dict.fromkeys(r['model'] for r in panel))
assert len(panel) == 120 and len(models) == 12
for model in models:
    assert {r['defense'] for r in panel if r['model'] == model} == set(DEFENSES)


def ordering(x, y, bound_key):
    xl, xh = x[bound_key]
    yl, yh = y[bound_key]
    return 1 if xl > yh+1e-9 else -1 if yl > xh+1e-9 else 0


pairwise, model_summaries = [], []
for model in models:
    rows = [next(r for r in panel if r['model'] == model and r['defense'] == d)
            for d in DEFENSES]
    pairs = []
    for x, y in itertools.combinations(rows, 2):
        pooled = ordering(x, y, 'pooled_joint_bounds_pct')
        strat = ordering(x, y, 'stratified_joint_bounds_pct')
        assert not pooled or pooled == strat
        axl, axh = interval(x['asr_macro_pct'])
        ayl, ayh = interval(y['asr_macro_pct'])
        # Higher order means preferred under this criterion.
        asr_order = 1 if axh < ayl else -1 if ayh < axl else 0
        p = {'model': model, 'left': x['defense'], 'right': y['defense'],
             'pooled_joint_order': pooled, 'stratified_joint_order': strat,
             'asr_order': asr_order,
             'certified_reversal_against_asr': bool(asr_order and strat and asr_order != strat)}
        pairs.append(p)
    max_lower = max(r['stratified_joint_bounds_pct'][0] for r in rows)
    potential = [r['defense'] for r in rows if r['stratified_joint_bounds_pct'][1] >= max_lower-1e-9]
    summary = {'model': model, 'pairs': len(pairs),
               'pooled_resolved_pairs': sum(p['pooled_joint_order'] != 0 for p in pairs),
               'stratified_resolved_pairs': sum(p['stratified_joint_order'] != 0 for p in pairs),
               'certified_asr_reversals': sum(p['certified_reversal_against_asr'] for p in pairs),
               'possible_joint_winners': potential,
               'mean_pooled_width_pp': float(np.mean([r['pooled_width_pp'] for r in rows])),
               'mean_stratified_width_pp': float(np.mean([r['stratified_width_pp'] for r in rows]))}
    pairwise += pairs
    model_summaries.append(summary)

decision = []
for model in models:
    rows = [r for r in panel if r['model'] == model]
    for weight in [0, 0.1, 0.25, 0.5, 1, 2, 5]:
        scored = []
        for row in rows:
            # Suite-wise endpoint optimization is monotone in u and a.
            lower, upper = [], []
            for suite in SUITES:
                z = row['suites'][suite]
                al, ah = interval(z['asr_pct'])
                jl, jh = z['joint_bounds_pct']
                lower.append(jl-weight*ah)
                upper.append(jh-weight*al)
            scored.append({'defense': row['defense'],
                           'score_lower': float(np.mean(lower)),
                           'score_upper': float(np.mean(upper))})
        best_lower = max(x['score_lower'] for x in scored)
        possible = [x['defense'] for x in scored if x['score_upper'] >= best_lower-1e-9]
        decision.append({'model': model, 'lambda': weight,
                         'possible_winners': possible, 'scores': scored})

# Exact joint outcomes and sampling uncertainty remain separate from identification.
pilot = json.loads((WORK / 'analysis/results/pilot_outcomes.json').read_text())
pilot_summary = json.loads((WORK / 'analysis/results/pilot_summary.json').read_text())
pilot_checks = []
for row in pilot_summary['conditions']:
    attacked = [r for r in pilot if r['model'] == row['model']
                and r['defense'] == row['defense'] and r['attacked']]
    assert len(attacked) == 24 and not any(r['technical_error'] for r in attacked)
    u = 100*np.mean([r['utility'] for r in attacked])
    a = 100*np.mean([r['attack_success'] for r in attacked])
    j = 100*np.mean([r['joint_success'] for r in attacked])
    count = collections.Counter(f"{r['utility']}{r['attack_success']}" for r in attacked)
    b = bounds(u, a, False)
    assert b[0]-1e-9 <= j <= b[1]+1e-9
    independence = u*(1-a/100)
    pilot_checks.append({'model': row['model'], 'defense': row['defense'],
                         'n': 24, 'counts_UA': dict(count), 'utility_pct': float(u),
                         'asr_pct': float(a), 'joint_pct': float(j),
                         'joint_bounds_pct': b,
                         'independence_proxy_pct': float(independence),
                         'proxy_error_pp': float(independence-j),
                         'bootstrap_ci95_pct': row['joint_success']['ci95_pct']})

totals = {'reported_conditions': len(conditions), 'suite_rows': 3*len(conditions),
          'rectangular_conditions': len(panel), 'models': len(models),
          'configurations_per_model': len(DEFENSES), 'within_model_pairs': len(pairwise),
          'pooled_resolved_pairs': sum(p['pooled_joint_order'] != 0 for p in pairwise),
          'stratified_resolved_pairs': sum(p['stratified_joint_order'] != 0 for p in pairwise),
          'certified_asr_reversals': sum(p['certified_reversal_against_asr'] for p in pairwise),
          'mean_pooled_width_pp': float(np.mean([r['pooled_width_pp'] for r in panel])),
          'mean_stratified_width_pp': float(np.mean([r['stratified_width_pp'] for r in panel])),
          'conditions_with_narrower_bounds': sum(r['width_reduction_pp'] > 1e-6 for r in panel),
          'max_width_reduction_pp': max(r['width_reduction_pp'] for r in panel),
          'source_overall_discrepancies': len(discrepancies),
          'source_rows_checked': len(extracted),
          'pilot_max_abs_independence_error_pp': max(abs(r['proxy_error_pp']) for r in pilot_checks),
          'fresh_model_executions': 0}
flagged = {(x['model'], x['defense']) for x in discrepancies}
unflagged_pairs = [p for p in pairwise if (p['model'], p['left']) not in flagged
                  and (p['model'], p['right']) not in flagged]
sensitivity = {'exclude_flagged_conditions': {
    'conditions': len(panel)-sum((r['model'], r['defense']) in flagged for r in panel),
    'pairs': len(unflagged_pairs),
    'pooled_resolved_pairs': sum(p['pooled_joint_order'] != 0 for p in unflagged_pairs),
    'stratified_resolved_pairs': sum(p['stratified_joint_order'] != 0 for p in unflagged_pairs),
    'certified_asr_reversals': sum(p['certified_reversal_against_asr'] for p in unflagged_pairs)}}
results = {'totals': totals, 'conditions': conditions, 'model_summaries': model_summaries,
           'pairwise': pairwise, 'decision_sensitivity': decision,
           'pilot_validation': pilot_checks, 'source_discrepancies': discrepancies,
           'sensitivity': sensitivity,
           'assumptions': ['The two reported marginals in a suite refer to the same evaluated population and weights.',
                           'Printed cells are rounded to the nearest 0.01 percentage point.',
                           'Primary model-level comparisons use an equal mixture of the three suites.',
                           'Identification bounds are conditional on the source metrics and are not confidence intervals.',
                           'Comparisons describe archived configurations, not present-day implementations.']}
(OUT/'published_marginals.json').write_text(json.dumps(extracted, indent=2))
(OUT/'extended_results.json').write_text(json.dumps(results, indent=2, default=native))

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8,
                     'axes.spines.top': False, 'axes.spines.right': False})
# Publication-sized single-column chart; suite information can narrow the ranges.
rows = [next(r for r in panel if r['model'] == 'GPT-4o' and r['defense'] == d) for d in DEFENSES]
fig, ax = plt.subplots(figsize=(3.45, 2.75))
for y, row in enumerate(rows):
    lo, hi = row['pooled_joint_bounds_pct']
    sl, sh = row['stratified_joint_bounds_pct']
    ax.plot([lo, hi], [y, y], color='#BAC8D0', linewidth=5, solid_capstyle='butt')
    ax.plot([sl, sh], [y, y], color='#245B78', linewidth=2.2, solid_capstyle='butt')
    if sh-sl < .1: ax.plot([.03], [y], marker='|', color='#245B78', markersize=5)
ax.set_yticks(range(len(rows)), DEFENSES, fontsize=7)
ax.invert_yaxis();ax.set_xlim(0, 65)
ax.set_xlabel('Feasible joint completion (%)', fontsize=8)
ax.grid(axis='x', alpha=.2);ax.set_axisbelow(True)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0],[0], color='#BAC8D0', lw=5, label='Pooled marginals'),
                   Line2D([0],[0], color='#245B78', lw=2, label='Suite marginals')],
          loc='lower right', frameon=False, fontsize=6.5)
fig.subplots_adjust(left=.34, bottom=.17, right=.98, top=.98)
fig.savefig(OUT/'joint_bounds_gpt4o.png', dpi=300)
fig.savefig(OUT/'joint_bounds_gpt4o.svg')
plt.close(fig)

fig, ax = plt.subplots(figsize=(3.45, 2.4))
labels=[s['model'].replace('Gemini-2.5 ', 'Gemini ').replace('Claude-Sonnet-', 'Claude ') for s in model_summaries]
x=np.arange(len(labels))
base=np.array([s['pooled_resolved_pairs'] for s in model_summaries])
extra=np.array([s['stratified_resolved_pairs'] for s in model_summaries])-base
ax.bar(x,base,color='#AEC1CD',label='Pooled marginals')
ax.bar(x,extra,bottom=base,color='#245B78',label='Added by suite marginals')
ax.set_xticks(x,labels,rotation=65,ha='right',fontsize=6)
ax.set_ylim(0,45);ax.set_yticks([0,15,30,45]);ax.set_ylabel('Separated pairs out of 45',fontsize=8)
ax.legend(frameon=False,fontsize=6,loc='upper left')
ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
fig.subplots_adjust(left=.14,bottom=.39,right=.99,top=.98)
fig.savefig(OUT/'resolved_pairs.png',dpi=300)
fig.savefig(OUT/'resolved_pairs.svg')
plt.close(fig)
print(json.dumps({'totals': totals, 'models': model_summaries,
                  'discrepancies': discrepancies}, indent=2, default=native))
