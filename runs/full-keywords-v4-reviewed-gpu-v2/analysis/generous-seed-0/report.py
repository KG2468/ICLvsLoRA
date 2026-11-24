"""Generate the report from scores.jsonl in this directory."""
import json
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
rows=[json.loads(l) for l in (root/'scores.jsonl').open()]
groups=['Base','ICL 16','ICL 64','ICL 256','LoRA 16','LoRA 64','LoRA 256']
benchmarks=['humaneval_synthetic','humaneval_python','aime2024','aime2025','gpqa']
labels=['Synthetic HumanEval','Python HumanEval','AIME 2024','AIME 2025','GPQA']
def group(r):
    return 'Base' if r['condition']=='base' else ('ICL' if r['condition']=='icl' else 'LoRA')+' '+str(r['n'])
def sub(g,b):
    return [r for r in rows if group(r)==g and (b is None or r['benchmark']==b)]
def ids(g,b,field):
    return {(r['benchmark'],r['task_id']) for r in sub(g,b) if r[field]}
expected={(r['benchmark'],r['task_id']) for r in sub('Base',None)}
assert len(expected)==586 and all({(r['benchmark'],r['task_id']) for r in sub(g,None)}==expected and len(sub(g,None))==586 for g in groups)
assert all((not r['strict_valid'] or r['valid']) and (not r['strict_passed'] or r['passed']) and (not r['passed'] or r['valid']) for r in rows)
def tab(cols,body):
    return '\n'.join(['| '+' | '.join(cols)+' |','|'+'---|'*len(cols),*['| '+' | '.join(map(str,line))+' |' for line in body]])
def counttable(field):
    def cell(g,b):
        rs=sub(g,b);v=sum(r[field] for r in rs);s=sum(r['strict_'+field] for r in rs)
        return f'{v}/{len(rs)} · {100*v/len(rs):.1f}% (+{v-s})'
    return tab(['Condition',*labels,'Pooled'],[[g,*[cell(g,b) for b in benchmarks+[None]]] for g in groups])
doc=['# Seed 0 with a more permissive answer parser',
     'All seven conditions cover the same 586 benchmark prompts (4,102 evaluations). This is a sensitivity analysis on saved generations, including saved retries. Raw outputs and official scores are preserved. Each table cell below gives the new count, percentage and additional tasks recovered over the official results.',
     '## Correct answers',counttable('passed'),'## Valid outputs',counttable('valid'),
     'For HumanEval, validity means a parsable top-level definition with the requested name; correctness requires passing the original tests. On synthetic HumanEval the program still has to decode under the seeded dialect. For GPQA and AIME, validity means a recoverable single choice or integer; correctness is exact match. The pooled rates count both HumanEval variants and weight benchmarks by their numbers of prompts.',
     '![Official and generous accuracy for each benchmark](accuracy.png)',
     '## Paired task comparisons','Each cell is gains / losses going from the first condition to the second under the generous parser, on identical benchmark and task IDs.']
pairs=[('Base',g) for g in groups[1:]]+[(f'ICL {n}',f'LoRA {n}') for n in (16,64,256)]+[(f'{m} {a}',f'{m} {b}') for m in ('ICL','LoRA') for a,b in ((16,64),(64,256))]
doc.append(tab(['Comparison',*labels],[[f'{a} → {g}',*[f'{len(ids(g,b,"passed")-ids(a,b,"passed"))} / {len(ids(a,b,"passed")-ids(g,b,"passed"))}' for b in benchmarks]] for a,g in pairs]))
recovered=[r for r in rows if r['valid'] and not r['strict_valid']]
doc+=['## What the parser recovered',tab(['Extraction rule','Additional valid','Additional correct'],[[k,len(v),sum(r['passed'] for r in v)] for k in sorted({r['method'] for r in recovered}) if (v:=[r for r in recovered if r['method']==k])])]
doc+=['## Retry and draft sensitivity','When a retry was present, it received priority. The rightmost column isolates gains from revisiting the initial draft after the retry supplied no identifiable submission. All columns count additional correct answers.',tab(['Condition','Single attempt','From retry','From earlier draft'],[[g,*[sum(r['passed'] for r in recovered if group(r)==g and predicate(r)) for predicate in (lambda r:not r['has_retry'],lambda r:r['source']=='retry',lambda r:r['has_retry'] and r['source']=='initial')]] for g in groups])]
doc+=['## Scoring rules and limits',
'''- This is an additive rescoring. Originally valid responses keep their score, including valid but incorrect answers. Extraction rules only operate on previously invalid responses. The same rules apply to base, ICL and LoRA.
- The parser can use text with missing thinking boundaries, ignores common boundary tokens and searches final segments first. Extra reasoning can surround a submission. If a retry has no identifiable submission, it can use the initial draft. A recognized but malformed code candidate blocks fallback; a failed test never triggers a second candidate.
- GPQA accepts explicit choice phrases, boxed choices, a final standalone letter, a leading choice with commentary, or exactly one matching option text. Guards on the leading-choice rule exclude competing option labels and reconsideration language. AIME also accepts a leading standalone integer. A bare intermediate equation cannot supply an answer. Earlier text segments and superseded drafts can supply a short answer only with a final marked answer line.
- For code, the parser favors the last identified submission with the requested signature, tolerates prose or Markdown around it, and can restore an omitted definition keyword on a signature matching the required name. It does not fix an algorithm, synthesize imports, close arbitrary brackets, or convert plain Python into synthetic code. Extraction uses neither the answer key nor the unit tests to choose a candidate.
- Recovered code is executed locally using the project's isolated HumanEval scorer and 10-second timeout. Original executions retain their original platform. Base ran locally, ICL on the server, and LoRA N=16 combines Colab and local rows. Server and local FP16 model files have different checksums. These seed-0 comparisons do not establish effects across seeds.''',
'## Reproduction','From the repository root, run the project Python on [rescore.py](rescore.py) and then [report.py](report.py). [scores.jsonl](scores.jsonl) records the strict and generous outcomes per original key, the extraction rule and attempt, and the recovered code or answer where applicable. [Official analysis](../seed-0.md).']
fig,axs=plt.subplots(1,5,figsize=(14,4.3),sharey=True)
for ax,b,label in zip(axs,benchmarks,labels):
    for i,g in enumerate(groups):
        rr=sub(g,b); a=sum(r['strict_passed'] for r in rr)*100/len(rr);z=sum(r['passed'] for r in rr)*100/len(rr)
        ax.plot([a,z],[i,i],color='#777');ax.scatter(a,i,marker='|',color='black',s=65,zorder=3);ax.scatter(z,i,color='#207297',s=24)
    ax.set_title(label,fontsize=10);ax.set_xlim(-3,83);ax.grid(axis='x',alpha=.2)
axs[0].set_yticks(range(7),groups);axs[0].invert_yaxis();fig.supxlabel('Correct (%)    |  official     ●  generous');fig.tight_layout();fig.savefig(root/'accuracy.png',dpi=160);plt.close(fig)
doc.insert(2, """## Findings

**LoRA overtakes ICL on synthetic HumanEval at N=64 and N=256 under permissive scoring.** At N=16 ICL still leads 12 to 7. At N=64 LoRA leads 16 to 7, and at N=256 it leads 20 to 11. All 29 additional synthetic solves came from extracting existing code that passed the tests without inserting a definition keyword. At N=256 only two synthetic tasks were solved by both methods: LoRA solved 18 others and ICL solved nine others.

**Ordinary Python retention remains much stronger for ICL.** At N=16 LoRA rises from 2 to 18 solves, with 13 of its 16 gains requiring a missing definition keyword. At N=256, 54 LoRA submissions contain a usable function under the new rules but only one passes, versus 92 passes for ICL and 111 for base. Recovering a callable function and recovering a correct algorithm produce very different estimates.

**GPQA format compliance explained some of the apparent loss.** LoRA N=16 gains 33 readable choices and 12 correct answers; N=64 gains 34 and 14. At N=256 LoRA and ICL each supply 197 readable choices and score 81 and 77 correct, respectively. Base remains ahead at 102. Neither AIME year gains a correct solution under these rules. Each year contains only 30 tasks.

**Across all conditions**, 478 formerly invalid submissions became readable and 80 became correct (79 LoRA and one ICL). Of 385 recovered code submissions, 49 passed. Four of the 80 additional correct answers came from an earlier draft after a retry. Despite the change on synthetic code, the pooled ranking still favors base (216 solves), followed by the ICL configurations (178–182) and the LoRA configurations (74–103). These are paired observations from one seed.""")

(root/'analysis.md').write_text('\n\n'.join(doc)+'\n')
print(counttable('passed'));print(counttable('valid'))
