#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd

def index_project(root: Path):
    """root以下の*.pyを {basename: {'rel': str, 'collisions': [str,...]}} で返す"""
    root = root.resolve()
    info = {}
    for p in root.rglob("*.py"):
        key = p.name  # basename基準
        rel = str(p.relative_to(root))
        if key in info:  # 衝突（同名複数）対策 → 最初を優先＋衝突記録
            info[key].setdefault("collisions", [info[key]["rel"]])
            info[key]["collisions"].append(rel)
            continue
        info[key] = {"rel": rel}
    return info

def decide_status(exists):
    """存在有無だけでラベル付け（内容の同一性は見ない簡易版）"""
    if not any(exists):
        return "missing_all"
    count = exists.count(True)
    if count == 1:
        return f"only_p{exists.index(True)+1}"
    if count == 2:
        pair = [i+1 for i, e in enumerate(exists) if e]
        return f"p{pair[0]}_p{pair[1]}"
    # 3つとも
    return "all_exist"

def main():
    # 引数の設定
    ap = argparse.ArgumentParser()
    ap.add_argument("--p1", required=True)
    ap.add_argument("--p2", required=True)
    ap.add_argument("--p3", required=True)

    # リポジトリルート
    repo_root = Path(__file__).resolve().parents[1]
    default_output = repo_root / "output" / "three_projects_diff.csv"

    ap.add_argument(
        "--out",
        default=str(default_output),
        help="Output CSV path (default: <repo_root>/output/three_projects_diff.csv)"
    )
    args = ap.parse_args()

    roots = [Path(args.p1), Path(args.p2), Path(args.p3)]
    names = ["p1", "p2", "p3"]

    indices = [index_project(r) for r in roots]
    all_keys = set().union(*[i.keys() for i in indices])

    rows = []
    for key in sorted(all_keys):
        row = {"key": key}
        exists_flags = []
        for idx, name in enumerate(names):
            d = indices[idx].get(key)
            row[f"exists_{name}"]    = bool(d)
            row[f"path_{name}"]      = d["rel"] if d else None
            row[f"collision_{name}"] = ",".join(d.get("collisions", [])) if d and "collisions" in d else None
            exists_flags.append(row[f"exists_{name}"])
        row["status"] = decide_status(exists_flags)
        rows.append(row)

    df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(df)} rows).")

if __name__ == "__main__":
    main()
