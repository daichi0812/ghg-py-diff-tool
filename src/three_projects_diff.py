#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path
import pandas as pd

def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def index_project(root: Path):
    """root以下の*.pyを {basename: {'rel': str, 'sha': str}} で返す"""
    root = root.resolve()
    info = {}
    for p in root.rglob("*.py"):
        key = p.name  # basename基準
        rel = str(p.relative_to(root))
        sha = sha256sum(p)
        if key in info:  # 衝突（同名複数）対策 → 最初を優先＋衝突記録
            if "collisions" not in info[key]:
                info[key]["collisions"] = [info[key]["rel"]]
            info[key]["collisions"].append(rel)
            continue
        info[key] = {"rel": rel, "sha": sha}
    return info

def decide_status(exists, shas):
    if not any(exists):
        return "missing_all"
    if exists.count(True) == 1:
        return f"only_p{exists.index(True)+1}"
    if exists.count(True) == 2:
        pair = [i+1 for i, e in enumerate(exists) if e]
        s = [shas[i-1] for i in pair]
        return f"p{pair[0]}_p{pair[1]}_" + ("same" if s[0] == s[1] else "diff")
    # 3つ存在
    uniq = set([s for s in shas if s is not None])
    return "all_exist_same" if len(uniq) == 1 else "all_exist_diff"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p1", required=True)
    ap.add_argument("--p2", required=True)
    ap.add_argument("--p3", required=True)
    ap.add_argument("--out", default="three_projects_diff.csv")
    args = ap.parse_args()

    roots = [Path(args.p1), Path(args.p2), Path(args.p3)]
    names = ["p1", "p2", "p3"]

    indices = [index_project(r) for r in roots]
    all_keys = set().union(*[i.keys() for i in indices])

    rows = []
    for key in sorted(all_keys):
        row = {"key": key}
        exists_flags = []
        shas = []
        for idx, name in enumerate(names):
            d = indices[idx].get(key)
            row[f"exists_{name}"] = bool(d)
            row[f"path_{name}"]   = d["rel"] if d else None
            row[f"sha_{name}"]    = d["sha"] if d else None
            row[f"collision_{name}"] = ",".join(d.get("collisions", [])) if d else None
            exists_flags.append(row[f"exists_{name}"])
            shas.append(row[f"sha_{name}"])
        row["status"] = decide_status(exists_flags, shas)
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"Wrote {args.out} ({len(df)} rows).")

if __name__ == "__main__":
    main()
