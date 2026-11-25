"""Find passed examples with good-looking reasoning traces across splits."""
import json, glob, os, re
from collections import Counter

cands = []
for p in sorted(glob.glob('runs/full-keywords-v4-reviewed-gpu-v2/splits/*.jsonl')):
    name = os.path.basename(p)[:-6]
    for line in open(p):
        r = json.loads(line)
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
        first = (r.get('initial_score') or {}).get('passed', False)
        cands.append(dict(file=name, cond=r['condition'], n=r['n'], bench=r['benchmark'],
                          task=r['task_id'], score=score, len=L, thinking=r['thinking'],
                          first=first, gtok=r['generation_tokens']))

cands.sort(key=lambda c: (-c['score'], -c['len']))
print('total passed:', len(cands))
print('by condition/bench:', Counter((c['cond'], c['bench']) for c in cands))
print()
print('top 40 by trace score:')
for c in cands[:40]:
    print(f"{c['file']:38s} {c['bench']:20s} {c['task']:14s} score={c['score']} len={c['len']:6d} think={c['thinking']} first={c['first']}")

# also: best per condition/benchmark cell
print()
print('best per cell:')
seen = {}
for c in cands:
    k = (c['cond'], c['n'], c['bench'])
    if k not in seen:
        seen[k] = c
for k in sorted(seen, key=str):
    c = seen[k]
    print(f"{k} -> {c['task']} score={c['score']} len={c['len']} think={c['thinking']} first={c['first']}")
