"""Extract the best-looking passed reasoning traces into readable markdown files."""
import json, glob, os, re
from pathlib import Path

root = Path('runs/full-keywords-v4-reviewed-gpu-v2')
outdir = root / 'analysis' / 'good-traces'
outdir.mkdir(parents=True, exist_ok=True)

cands = []
for p in sorted(glob.glob(str(root / 'splits' / '*.jsonl'))):
    name = os.path.basename(p)[:-6]
    for line in open(p):
        r = json.loads(line)
        if r['seed'] != 0:
            continue
        if not r['passed'] or r['benchmark'] not in ('humaneval_synthetic', 'humaneval_python', 'gpqa'):
            continue
        text = r['text']
        score = 0
        if r['thinking']:
            score += 2
        for pat in (r'\*\*1\.', r'\*\*Step', r'^\s*\d+\.\s+\*\*', r'Approach', r'Plan:', r'Let me', r'First,', r'Check:'):
            if re.search(pat, text, re.M | re.I):
                score += 1
        L = len(text)
        if L > 1500:
            score += 1
        if L > 4000:
            score += 1
        cands.append(dict(rec=r, file=name, cond=r['condition'], n=r['n'], bench=r['benchmark'],
                          task=r['task_id'], score=score, len=L))

# best per (condition, n, benchmark) cell
best = {}
for c in cands:
    k = (c['cond'], c['n'], c['bench'])
    if k not in best or (c['score'], c['len']) > (best[k]['score'], best[k]['len']):
        best[k] = c

index = ['# Good-looking passed reasoning traces (seed 0 only)',
         '',
         'One representative passed example per condition × N × benchmark cell, ranked by a',
         'heuristic trace-quality score (thinking mode, structured reasoning markers, length).',
         'Restricted to seed 0 rows. All rows passed their benchmark scoring.',
         '`first` = passed on the initial attempt before the final-answer retry.']
for k in sorted(best, key=str):
    c = best[k]
    r = c['rec']
    cond, n, bench = k
    slug = f"{cond}-n{n}-{bench}-{c['task'].replace('/', '-')}".replace(' ', '')
    first = (r.get('initial_score') or {}).get('passed', False)
    lines = [f"# {cond} N={n} · {bench} · {c['task']}",
             '',
             f"Source: `splits/{c['file']}.jsonl` · trace score {c['score']} · {c['len']} chars · "
             f"thinking={r['thinking']} · passed on first attempt: {first}",
             '',
             '## Prompt (user message, truncated)',
             '```',
             r['messages'][-1]['content'][:1200],
             '```',
             '',
             '## Model output (full)',
             '```',
             r['text'],
             '```']
    if r.get('decoded_code'):
        lines += ['', '## Decoded code (executed)', '```python', r['decoded_code'], '```']
    if r.get('followup') and r['followup'].get('text'):
        lines += ['', '## Final-answer retry output', '```', r['followup']['text'][:3000], '```']
    (outdir / f'{slug}.md').write_text('\n'.join(lines) + '\n')
    index.append(f"- [{cond} N={n} · {bench} · {c['task']}](good-traces/{slug}.md) "
                 f"(score {c['score']}, {c['len']} chars, thinking={r['thinking']}, first-attempt pass: {first})")

(root / 'analysis' / 'good-traces.md').write_text('\n'.join(index) + '\n')
print(f'wrote {len(best)} trace files and index to {outdir}')
