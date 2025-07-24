#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd

def read_paths_file(list_path: Path):
    """--list で指定されたファイルからパスを読み込む。
       空行と # 始まりの行は無視。"""
    paths = []
    for line in list_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line)
    return paths

def scan_project(root_path):
    """root_path 以下の *.py を {basename: {'rel': str, 'collisions': [str,...]}} 形式で返す"""
    root = Path(root_path).resolve()
    info = {}
    for p in root.rglob("*.py"):
        name = p.name
        rel = str(p.relative_to(root))
        if name not in info:
            info[name] = {"rel": rel, "collisions": []}
        else:
            # 既にある → 衝突として記録
            if not info[name]["collisions"]:
                info[name]["collisions"].append(info[name]["rel"])
            info[name]["collisions"].append(rel)
    return info

def decide_status(flags):
    """
    flags: [True/False, ...]
    全 False -> 'missing_all'
    全 True  -> 'all_exist'
    それ以外 -> 'pX_pY_...'
    """
    if not any(flags):
        return "missing_all"
    if all(flags):
        return "all_exist"
    present = [f"p{i+1}" for i, f in enumerate(flags) if f]
    return "_".join(present)

def main():
    parser = argparse.ArgumentParser(
        description="複数プロジェクト間の *.py ファイル存在差分を一覧化（内容までは見ない簡易版）"
    )
    # 位置引数: 直接パスを並べる（0個でもOK）
    parser.add_argument(
        "projects",
        metavar="PROJECT",
        nargs="*",
        help="プロジェクトのルートディレクトリ（複数指定可）"
    )
    # --list: パス一覧ファイル
    parser.add_argument(
        "--list",
        type=Path,
        help="パス一覧を1行1パスで記述したテキストファイル"
    )
    parser.add_argument(
        "--out",
        default=str(Path.cwd() / "multi_projects_diff.csv"),
        help="出力CSVパス（デフォルト: カレントディレクトリ）"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="読み込んだパス等を表示してデバッグ用に使う"
    )
    args = parser.parse_args()

    # --- パス集合を作る ---
    paths = list(args.projects)  # 位置引数ぶん
    if args.list:
        paths.extend(read_paths_file(args.list))

    if not paths:
        parser.error("PROJECT か --list で最低1つはパスを指定してください。")

    # 重複除去（順序保持）
    seen = set()
    unique_paths = []
    for p in paths:
        if p not in seen:
            unique_paths.append(p)
            seen.add(p)

    project_paths = [Path(p) for p in unique_paths]

    # 存在チェック
    missing = [str(p) for p in project_paths if not p.exists()]
    if missing:
        print("[WARN] 以下のディレクトリが存在しません（無視されます）:")
        for m in missing:
            print("       ", m)
        project_paths = [p for p in project_paths if p.exists()]

    if args.debug:
        print("[DEBUG] project_paths =", [str(p) for p in project_paths])

    names = [f"p{i+1}" for i in range(len(project_paths))]

    # ---- 各プロジェクトを走査 ----
    index_list = [scan_project(p) for p in project_paths]

    # ---- 全てのファイル名キーを集約 ----
    all_keys = set()
    for idx in index_list:
        all_keys.update(idx.keys())

    # ---- 行データを作成 ----
    rows = []
    for key in sorted(all_keys):
        row = {"ファイル名": key}
        exists_flags = []
        for i, name in enumerate(names):
            d = index_list[i].get(key)
            exists = d is not None
            row[f"exists_{name}"] = exists
            row[f"path_{name}"] = d["rel"] if exists else None
            row[f"collision_{name}"] = ",".join(d["collisions"]) if exists and d["collisions"] else None
            exists_flags.append(exists)

        row["status"] = decide_status(exists_flags)
        rows.append(row)

    # ---- CSV 出力 ----
    df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(df)} rows).")

if __name__ == "__main__":
    main()
