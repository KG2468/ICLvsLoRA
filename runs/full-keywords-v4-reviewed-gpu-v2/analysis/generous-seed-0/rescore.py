"""Run from the project root using the project's Python and HumanEval sandbox."""
import ast
import hashlib
import json
import re
import textwrap
import tokenize
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from final_project.language import Language
from final_project.scoring import execute

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
warnings.filterwarnings("ignore", category=SyntaxWarning)
BOUNDARY = re.compile(r"</?think>|<\|(?:endoftext|im_end|im_start)\|>")
RETHINK = re.compile(r"\b(?:wait|reconsider|re-evaluate|on second thought|actually)\b", re.I)


def segments(raw):
    # Prefer the final segment. Earlier segments can supply an otherwise missing answer.
    return [s.strip() for s in reversed(BOUNDARY.split(raw)) if s.strip()]


def choice(text, benchmark, prompt):
    gpqa = benchmark == "gpqa"
    token = r"[A-D]" if gpqa else r"\d{1,3}"
    def normalize(value):
        return value if gpqa else str(int(value))
    text = re.sub(r"\\(?:text|mathrm|mathbf)\{("+token+r")\}", r"\1", text)
    text = text.replace("**", "").replace("`", "").strip()
    # Match bounded answer expressions; reject a prefix of a number, fraction, range or list.
    value = r"[\s$({]*("+token+r")(?!\w)[)}$]*"
    if re.search(r"(?im)^\s*(?:final\s+)?answer\s*:\s*[A-D]\s*(?:,\s*|\s+(?:or|and)\s+)[A-D]\b", text):
        return None, "ambiguous"
    marks = list(re.finditer(r"(?i:\b(?:final\s+answer|answer|correct\s+(?:answer|option|choice))\s*(?:is\b|:|=)\s*(?:option\s+|choice\s+)?)"+value,text))
    marks += list(re.finditer(r"\\boxed\s*\{\s*("+token+r")\s*\}", text))
    if marks:
        m = max(marks, key=lambda x:x.end())
        tail = text[m.end():].split('\n',1)[0].strip()
        if not re.match(r"(?:[?]|[/+*=×÷−–-]\s*\d|\.\d|,\s*\d|(?:or|and)\s+[A-D]\b)", tail) and not RETHINK.search(text[m.end():]):
            return normalize(m[1]), "marked answer"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None, ""
    standalone = r"[($\[]*("+token+r")[)$\]]*[.!]?"
    m = re.fullmatch(standalone,lines[-1])
    if m:
        return normalize(m[1]), "final standalone"
    if gpqa:
        options = re.findall(r"(?m)^([A-D])[.)]\s+(.+)$",prompt)
        exact = [v for v,opt in options if text.casefold().strip(' .')==opt.casefold().strip(' .')]
        if len(exact)==1:
            return exact[0], "exact option text"
        m = re.match(r"^\(?([A-D])(?:[.)](?:\s|$)|\s*\n|$)",text)
        if m and not RETHINK.search(text[m.end():]):
            alternatives = re.findall(r"(?m)^\s*\(?([A-D])[.)]\s",text)
            if all(x==m[1] for x in alternatives):
                return m[1], "leading option"
    elif not RETHINK.search(text):
        m = re.fullmatch(standalone,lines[0])
        if m:
            return normalize(m[1]), "leading integer"
    return None, ""


def code_candidate(segment, entry, synthetic):
    prefix = "zot" if synthetic else "def"
    header = re.compile(r"(?m)^([ \t]*)(?:(?:async\s+def|def|zot)\s+)?"+re.escape(entry)+r"\s*\(")
    # A signature must look like a definition, not a call in an explanation.
    bare = re.compile(r"(?m)^([ \t]*)("+re.escape(entry)+r"\([^\n]*\)(?:\s*->[^\n:]+)?\s*:)(?=[ \t]*(?:#.*)?$)")
    blocks = re.split(r"(?m)^[ \t]*(?:```|~~~)[^\n]*$",segment)
    for blob in reversed(blocks):
        anchors = [m for m in header.finditer(blob)
                   if re.match(r"(?:async\s+def|def|zot)\s+",blob[m.start():].lstrip()) or bare.match(blob,m.start())]
        if not anchors:
            continue
        lines = textwrap.dedent(blob).strip('\n').splitlines()
        # Retain contiguous code, including imports, constants and helper functions.
        # Trim surrounding prose only at unindented boundaries; never drop a broken body line.
        def prose(line):
            return (line==line.lstrip() and
                    (re.match(r"^(?:[A-Z][a-z]+(?:[,']\w*)?\s+[a-zA-Z]+\b|[!]+$|[-*] [A-Za-z])",line)
                     or line.startswith(('</','<|'))))
        anchor_line = max(i for i,line in enumerate(lines) if header.match(line) and
                          (re.match(r'(?:async\s+def|def|zot)\s+',line.lstrip()) or bare.match(line)))
        start = max([i+1 for i,line in enumerate(lines[:anchor_line]) if prose(line)] or [0])
        end = next((i for i in range(anchor_line+1,len(lines)) if prose(lines[i])),len(lines))
        code = textwrap.dedent('\n'.join(lines[start:end])).strip()
        code,n = bare.subn(r'\1'+prefix+r' \2',code)
        try:
            decoded = Language(0).decode(code) if synthetic else code
            tree = ast.parse(decoded)
        except (SyntaxError,ValueError,tokenize.TokenError,RecursionError):
            return None,"invalid candidate"
        if any(isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==entry for node in tree.body):
            return decoded,"insert definition keyword" if n else "extract code"
    return None,""


def main():
    tasks={}
    for b in ('humaneval','aime2024','aime2025','gpqa'):
        for line in Path(f'data/benchmarks/{b}.jsonl').open():
            t=json.loads(line);tasks[b,t['id']]=t
    rows=[]; pending=[]
    for line in (ROOT/'results.jsonl').open():
        r=json.loads(line)
        if r['seed']!=0:continue
        b=r['benchmark'];coding=b.startswith('humaneval');valid=r['parse_valid'] if coding else r['answer'] is not None
        rec={k:r[k] for k in ('key','condition','n','benchmark','task_id','status','passed')}
        rec.update(strict_valid=valid,valid=valid,strict_passed=r['passed'],strict_status=r['status'],method='original',source='original',has_retry='followup' in r)
        rows.append(rec)
        if valid:continue
        t=tasks['humaneval' if coding else b,r['task_id']]
        attempts=[('retry',r['followup']),('initial',r)] if 'followup' in r else [('initial',r)]
        for source,a in attempts:
            found=False
            for pos,seg in enumerate(segments(a.get('text',''))):
                if not coding and (pos or source=='initial' and 'followup' in r):
                    # Only use an earlier explicit commitment, never an intermediate calculation.
                    if not re.search(r'(?im)^\s*(?:\*\*)?(?:final\s+)?answer\s*:',seg.strip().splitlines()[-1]):
                        continue
                if coding:
                    candidate,method=code_candidate(seg,t['entry_point'],b.endswith('synthetic'))
                else:
                    candidate,method=choice(seg,b,t['prompt'])
                if candidate is None:
                    # A malformed concrete code submission or conflicting choices supersede earlier drafts.
                    if method in ('invalid candidate','ambiguous'):
                        found=True
                        break
                    if not coding and RETHINK.search(seg):
                        found=True
                        break
                    continue
                rec.update(valid=True, method=method,source=source)
                if coding:
                    rec['decoded_code']=candidate
                    pending.append((rec,candidate,t))
                else:
                    rec.update(answer=candidate,passed=candidate==t['answer'],status='scored')
                found=True;break
            if found:break
    assert len(rows)==len({r['key'] for r in rows})==4102
    assert execute('def f(): return 1','def check(f): assert f()==1','f',10)['passed']
    def test(item):
        rec,code,t=item
        result=execute(code,t['test'],t['entry_point'],10)
        rec.update(result)
    print('Testing',len(pending),'recovered programs',flush=True)
    with ThreadPoolExecutor(4) as pool:
        for _ in pool.map(test,pending):pass
    tmp=OUT/'scores.tmp'
    tmp.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    tmp.replace(OUT/'scores.jsonl')
    print(Counter(x['method'] for x in rows))
if __name__=='__main__':main()
