#!/usr/bin/env python3
import argparse
from pathlib import Path
import hashlib
import difflib
import pandas as pd

# ---------- Utility ----------

def read_text_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return f.readlines()

def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_project(root_path: Path, patterns):
    """
    root_path 以下の指定拡張子ファイルを
    {basename: {'rel': str, 'abs': str, 'collisions': [str,...]}} で返す
    """
    root = root_path.resolve()
    info = {}
    for pat in patterns:
        for p in root.rglob(f"*{pat}"):
            name = p.name
            rel = str(p.relative_to(root))
            abs_ = str(p)
            if name not in info:
                info[name] = {"rel": rel, "abs": abs_, "collisions": []}
            else:
                # 衝突
                if not info[name]["collisions"]:
                    info[name]["collisions"].append(info[name]["rel"])
                info[name]["collisions"].append(rel)
    return info

def decide_status(p1_exists: bool, p2_exists: bool, same: bool | None):
    """
    p1_exists, p2_exists, same から status 文字列を返す
    same は両方存在するときのみ True/False、それ以外は None
    """
    if not p1_exists and not p2_exists:
        return "missing_both"           # あり得ないはずだが形式上
    if p1_exists and not p2_exists:
        return "only_p1"
    if not p1_exists and p2_exists:
        return "only_p2"
    # 両方ある
    return "same" if same else "diff"

def write_diff_file(diff_text: str, out_dir: Path, key: str):
    """
    diff_text を out_dir/key.diff に書き出し、パスを返す。
    key に / や : が入ると嫌なので _ に潰す。
    """
    safe_key = key.replace("/", "_").replace(":", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    diff_path = out_dir / f"{safe_key}.diff"
    diff_path.write_text(diff_text, encoding="utf-8")
    return str(diff_path)

# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(
        description="2 つのプロジェクト間で *.py（など）の有無と差分を CSV に出力"
    )
    parser.add_argument("p1", help="プロジェクト1のルートパス")
    parser.add_argument("p2", help="プロジェクト2のルートパス")
    parser.add_argument("--out", default=str(Path.cwd() / "two_projects_diff.csv"),
                        help="出力CSVパス")
    parser.add_argument("--diff-dir", default=None,
                        help="diff を個別ファイルに保存するディレクトリ（指定しないとCSV内のみ）")
    parser.add_argument("--ext", default=".py",
                        help="対象拡張子（カンマ区切り、デフォルト: .py）")
    parser.add_argument("--max-diff-lines", type=int, default=300,
                        help="CSVに埋め込むdiffの最大行数（超えたら省略）")
    parser.add_argument("--debug", action="store_true", help="デバッグ出力")
    args = parser.parse_args()

    p1 = Path(args.p1).resolve()
    p2 = Path(args.p2).resolve()
    if not p1.exists() or not p1.is_dir():
        parser.error(f"p1 が存在しないかディレクトリではありません: {p1}")
    if not p2.exists() or not p2.is_dir():
        parser.error(f"p2 が存在しないかディレクトリではありません: {p2}")

    patterns = [e.strip() for e in args.ext.split(",") if e.strip().startswith(".")]
    if args.debug:
        print("[DEBUG] target extensions:", patterns)

    idx1 = scan_project(p1, patterns)
    idx2 = scan_project(p2, patterns)

    all_keys = sorted(set(idx1.keys()) | set(idx2.keys()))
    rows = []

    diff_dir = Path(args.diff_dir) if args.diff_dir else None

    for key in all_keys:
        d1 = idx1.get(key)
        d2 = idx2.get(key)
        p1_exists = d1 is not None
        p2_exists = d2 is not None

        same = None
        diff_text = None
        diff_file_path = None

        if p1_exists and p2_exists:
            # 比較対象となるファイルを1つに決める（衝突時は最初の rel を使う）
            path1 = Path(p1 / d1["rel"])
            path2 = Path(p2 / d2["rel"])

            # まずハッシュで高速一致判定
            same = sha256sum(path1) == sha256sum(path2)
            if not same:
                lines1 = read_text_lines(path1)
                lines2 = read_text_lines(path2)
                diff_iter = difflib.unified_diff(
                    lines1, lines2,
                    fromfile=str(path1),
                    tofile=str(path2),
                    lineterm=""
                )
                # テキスト化
                diff_lines = list(diff_iter)
                if args.max_diff_lines and len(diff_lines) > args.max_diff_lines:
                    trunk = diff_lines[:args.max_diff_lines]
                    trunk.append(f"...(truncated {len(diff_lines)-args.max_diff_lines} lines)...")
                    diff_text = "\n".join(trunk)
                else:
                    diff_text = "\n".join(diff_lines)

                # diff をファイルに保存するなら
                if diff_dir:
                    diff_file_path = write_diff_file(diff_text, diff_dir, key)

        row = {
            "key": key,
            "exists_p1": p1_exists,
            "path_p1": d1["rel"] if p1_exists else None,
            "collision_p1": ",".join(d1["collisions"]) if (p1_exists and d1["collisions"]) else None,
            "exists_p2": p2_exists,
            "path_p2": d2["rel"] if p2_exists else None,
            "collision_p2": ",".join(d2["collisions"]) if (p2_exists and d2["collisions"]) else None,
            "same": same if same is not None else None,
            "status": decide_status(p1_exists, p2_exists, same),
            "diff_file": diff_file_path,
            "diff_text": diff_text
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(df)} rows).")

if __name__ == "__main__":
    main()
