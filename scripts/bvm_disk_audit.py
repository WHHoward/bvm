#!/usr/bin/env python3
"""Read-only local disk inventory for WHHoward/bvm. NEVER deletes anything."""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import subprocess

CATEGORIES = ('raw CSV', 'HTML', 'ZIP', 'other CSV', 'other')


def describe(path: Path) -> str:
    s=path.name.lower()
    if s=='raw.csv' or s.startswith('data_tran') and s.endswith('.csv'):return 'raw CSV'
    if s.endswith('.html'):return 'HTML'
    if s.endswith('.zip'):return 'ZIP'
    if s.endswith('.csv'):return 'other CSV'
    return 'other'


def report(root: Path, top_n: int):
    counts=Counter(); sizes=Counter(); groups=Counter(); largest=[]; errors=[]
    for here, dirs, names in os.walk(root):
        here_path=Path(here)
        # .git is measured as a separate on-disk tree in one summary number
        if here_path == root:
            dirs[:]=[x for x in dirs if x!='.git']
        for name in names:
            p=here_path/name
            try:
                if p.is_symlink():continue
                n=p.stat().st_size
                rel=p.relative_to(root)
            except (OSError,ValueError) as e:
                errors.append(str(e));continue
            c=describe(p)
            counts[c]+=1; sizes[c]+=n
            parts=rel.parts
            group=parts[2] if len(parts)>2 and parts[:2]==('test','exploration') else parts[0]
            groups[group]+=n
            largest.append((n,str(rel)))
    git_mb=None
    git=root/'.git'
    if git.exists():
        try:
            p=subprocess.run(['du','-sk',str(git)],capture_output=True,text=True,check=True)
            git_mb=int(p.stdout.split()[0])*1024
        except (OSError,ValueError,subprocess.CalledProcessError):pass
    status=None
    try:
        p=subprocess.run(['git','-C',str(root),'status','--short'],capture_output=True,text=True,timeout=15)
        status={'clean':not bool(p.stdout.strip()),'changed_count':len(p.stdout.splitlines()),'exit_code':p.returncode}
    except (OSError,subprocess.TimeoutExpired):pass
    return {'root':str(root),'filesystem_only':True,'contains_no_deletions':True,
        'file_categories':{k:{'files':counts[k],'bytes':sizes[k]} for k in CATEGORIES},
        'experiment_dirs_largest':[{ 'name':name,'bytes':size} for name,size in groups.most_common(top_n)],
        'largest_files':[{ 'path':path,'bytes':size,'category':describe(Path(path))} for size,path in sorted(largest,reverse=True)[:top_n]],
        'git_dir_bytes':git_mb,'git_worktree_status':status,
        'notes':['Do not delete raw/ZIP without matching source+SHA+PACKAGE_QA provenance.',
                 'Deleting git-tracked files in a new commit does not remove past Git object history.',
                 'HTML and plots may be regenerable, but verify raw, renderer version and manifests first.',
                 'Drive is separate: use Drive inventory and matched SHA before removing duplicate-named archives.'],
        'errors':errors[:20]}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,default=Path.cwd())
    ap.add_argument('--top',type=int,default=30)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    root=args.repo.resolve()
    d=report(root,args.top)
    text=json.dumps(d,indent=2,ensure_ascii=False)
    if args.out:
        if args.out.exists(): raise SystemExit('Refusing to overwrite inventory; use another --out path')
        args.out.write_text(text+'\n',encoding='utf8')
    print(text)

if __name__=='__main__': main()
