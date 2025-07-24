#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path
import pandas as pd
import re

# ---------- Utility ----------

def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def read_paths_file(list_path: Path):
    paths = []
    for line in list_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line)
    return paths

def scan_project(root_path):
    """
    root_path 以下の *.py を
      {basename: {'rel': str, 'sha': str, 'collisions': [str,...]}}
    で返す
    """
    root = Path(root_path).resolve()
    info = {}
    for p in root.rglob("*.py"):
        name = p.name
        rel  = str(p.relative_to(root))
        sha  = sha256sum(p)
        if name not in info:
            info[name] = {"rel": rel, "sha": sha, "collisions": []}
        else:
            if not info[name]["collisions"]:
                info[name]["collisions"].append(info[name]["rel"])
            info[name]["collisions"].append(rel)
    return info

def decide_status(flags, names):
    """フラグ配列と列名配列から status を決める"""
    if not any(flags):
        return "missing_all"
    if all(flags):
        return "all_exist"
    present = [n for n, f in zip(names, flags) if f]
    return "_".join(present)

def slugify(text: str) -> str:
    """
    CSV列名にしても困らないように、英数字と '_' のみにする簡易版。
    """
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text)
    return text.strip("_") or "proj"

def short_name(p: Path, keep_parts=2) -> str:
    """
    末尾 keep_parts 個のパス要素を '_' でつなぎ、slugify する。
    """
    return slugify("_".join(p.parts[-keep_parts:]))

def make_unique(names):
    """重複を _2, _3 ... としてユニーク化"""
    seen = {}
    result = []
    for n in names:
        if n not in seen:
            seen[n] = 1
            result.append(n)
        else:
            seen[n] += 1
            result.append(f"{n}_{seen[n]}")
    return result

# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(
        description="複数プロジェクト間 *.py の存在 & ソース一致グルーピングを一覧化"
    )
    parser.add_argument("projects", metavar="PROJECT", nargs="*",
                        help="プロジェクトのルートディレクトリ（複数指定可）")
    parser.add_argument("--list", type=Path,
                        help="パス一覧を1行1パスで記述したテキストファイル")
    parser.add_argument("--out", default=str(Path.cwd() / "multi_projects_diff.csv"),
                        help="出力CSVパス（デフォルト: カレントディレクトリ）")
    parser.add_argument("--debug", action="store_true",
                        help="読み込んだパス等を表示してデバッグ用に使う")
    args = parser.parse_args()

    # ---- パスをまとめる ----
    paths = list(args.projects)
    if args.list:
        paths.extend(read_paths_file(args.list))
    if not paths:
        parser.error("PROJECT か --list で最低1つはパスを指定してください。")

    # 重複除去（順序保持）
    seen, unique_paths = set(), []
    for p in paths:
        if p not in seen:
            unique_paths.append(p)
            seen.add(p)

    project_paths = [Path(p) for p in unique_paths]

    # 存在チェック & ディレクトリチェック
    missing = [str(p) for p in project_paths if not p.exists()]
    not_dir = [str(p) for p in project_paths if p.exists() and not p.is_dir()]
    if missing:
        print("[WARN] 以下のディレクトリが存在しません（無視されます）:")
        for m in missing:
            print("       ", m)
    if not_dir:
        print("[WARN] ディレクトリではないため無視します:")
        for m in not_dir:
            print("       ", m)
    project_paths = [p for p in project_paths if p.exists() and p.is_dir()]

    if args.debug:
        print("[DEBUG] project_paths =", [str(p) for p in project_paths])

    # 列名をパス由来に
    raw_names = [short_name(p, keep_parts=2) for p in project_paths]
    names     = make_unique(raw_names)  # 重複があれば _2, _3…

    # 元の順番を覚えておく（group_summary の並び用）
    order = {name: i for i, name in enumerate(names)}

    # ---- 走査 ----
    index_list = [scan_project(p) for p in project_paths]

    # ---- 全ファイル名集合 ----
    all_keys = set().union(*[idx.keys() for idx in index_list])

    # ---- 行データ作成 ----
    rows = []
    for key in sorted(all_keys):
        row = {"ファイル名": key}
        exists_flags = []

        sha_to_gid = {}
        next_gid   = 1
        group_assignments = [None] * len(names)

        for i, name in enumerate(names):
            d = index_list[i].get(key)
            exists = d is not None
            exists_flags.append(exists)

            if exists:
                sha = d["sha"]
                if sha not in sha_to_gid:
                    sha_to_gid[sha] = next_gid
                    next_gid += 1
                gid = sha_to_gid[sha]
                group_assignments[i] = gid

                row[f"path_{name}"]      = d["rel"]
                row[f"sha_{name}"]       = sha[:12]
                row[f"collision_{name}"] = ",".join(d["collisions"]) if d["collisions"] else None
            else:
                row[f"path_{name}"]      = None
                row[f"sha_{name}"]       = None
                row[f"collision_{name}"] = None

            row[f"exists_{name}"] = exists

        # status
        row["status"] = decide_status(exists_flags, names)

        # group columns
        for name, gid in zip(names, group_assignments):
            row[f"group_{name}"] = gid

        # group_summary
        gid_to_projects = {}
        for proj_name, gid in zip(names, group_assignments):
            if gid is None:
                continue
            gid_to_projects.setdefault(gid, []).append(proj_name)

        row["group_summary"] = ";".join(
            f"G{gid}:{','.join(sorted(gid_to_projects[gid], key=lambda x: order[x]))}"
            for gid in sorted(gid_to_projects)
        )
        row["num_groups"] = len(gid_to_projects)

        rows.append(row)

    # ---- CSV 出力 ----
    df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(df)} rows).")

    # ---- デバッグ表示 ----
    if args.debug:
        diff_df = df[df["num_groups"] > 1][["ファイル名", "group_summary"]]
        print("\n[DEBUG] 内容が異なるファイル抜粋:")
        print(diff_df.to_string(index=False))

if __name__ == "__main__":
    main()
