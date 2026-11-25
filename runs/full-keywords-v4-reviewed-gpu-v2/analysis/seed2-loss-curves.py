"""Plot training and validation loss curves for the seed 2 LoRA adapters.

Data sources:
- seed2-n256: adapters/seed2-n256/loss.jsonl (structured train/validation rows)
- seed2-n16 and seed2-n64: no loss.jsonl was saved; the loss table is parsed
  from logs/train-seed2-n256.log only. If per-size logs appear later, drop
  them in as logs/train-seed2-<n>.log and rerun.
"""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

run = Path(__file__).resolve().parent.parent
adapters = run / 'adapters'
logs = run / 'logs'
out = Path(__file__).resolve().parent

ANSI = re.compile(r'\x1b\[[0-9;]*m')


def from_loss_jsonl(path):
    train, val = [], []
    for line in path.open():
        r = json.loads(line)
        if r['kind'] == 'train':
            train.append((r['iteration'], r['train_loss']))
        elif r['kind'] == 'validation':
            val.append((r['iteration'], r['val_loss']))
    return train, val


def from_log(path):
    train, val = [], []
    for line in path.open():
        line = ANSI.sub('', line)
        m = re.match(r'\s*(\d+)\s+val\s+([\d.]+)\s', line)
        if m:
            val.append((int(m.group(1)), float(m.group(2))))
            continue
        m = re.match(r'\s*(\d+)\s+([\d.]+)\s+[▲▼]', line)
        if m:
            train.append((int(m.group(1)), float(m.group(2))))
    return train, val


series = {}
for n in (16, 64, 256):
    name = f'seed2-n{n}'
    lj = adapters / name / 'loss.jsonl'
    lg = logs / f'train-{name}.log'
    if lj.exists():
        series[n] = from_loss_jsonl(lj)
        src = 'loss.jsonl'
    elif lg.exists():
        series[n] = from_log(lg)
        src = 'log'
    else:
        print(f'{name}: no loss data found, skipping')
        continue
    print(f'{name}: {len(series[n][0])} train points, {len(series[n][1])} val points ({src})')

fig, ax = plt.subplots(figsize=(8, 4.8))
colors = {16: '#207297', 64: '#c1502a', 256: '#4a8c3f'}
for n, (tr, va) in sorted(series.items()):
    c = colors[n]
    if tr:
        xs, ys = zip(*tr)
        ax.plot(xs, ys, color=c, lw=1.2, alpha=.75, label=f'N={n} train')
    if va:
        xs, ys = zip(*va)
        ax.plot(xs, ys, 's', color=c, ms=7, label=f'N={n} validation')
ax.set_xlabel('Iteration')
ax.set_ylabel('Loss')
ax.set_title('Seed 2 LoRA training loss curves')
ax.grid(alpha=.25)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(out / 'seed2-loss-curves.png', dpi=160)
plt.close(fig)
print(f'wrote {out / "seed2-loss-curves.png"}')
