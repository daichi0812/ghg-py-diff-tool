# ghg-py-diff-toool

## multi_projects_diff.py

.pyファイルを"同名"で突き合わせ、存在有無をCSVで出力する。指定したいパスをpaths.txtに書く。
出力される列について
**ファイル名**: .pyの名前
**exits_p⚪︎**: True/Falseでそのファイルが指定したディレクトリ内に存在するかどうか判定
**path_p⚪︎**: 存在する場合のパスを表示
**collision_p⚪︎**: 指定したディレクトリ内で重複している場合はそのパスを表示

- "同名" = basenameでの比

実行方法

- 町田さんマシンの環境

```bash
python3 multi_projects_diff.py --list paths.txt --out ../output/multi_projects_diff.csv
```

---

## two_projects_diff.py

### 概要

指定した2つのディレクトリ内に存在する.pyファイルを洗い出し、共通の同名ファイルがあるかどうかを判定する。ある場合にはその同名のファイルのソースコードの差異を出力する。

実行方法

- 町田さんマシンの環境

```bash
python3 two_projects_diff.py \
  /path/to/projectA \
  /path/to/projectB \
  --out ../output/two_projects_diff.csv \
  --diff-dir ../output/diffs \
  --ext .py
```

### テスト

`tests` ディレクトリに同名の.pyフォルダが入っているp1, p2ディレクトリがある。この2つを指定して、出力されたCSVを見ることで、コードが機能しているかどうか判断できる。

```bash
python3 two_projects_diff.py \
  /Users/shotaro/DevHub/CG/ghg-py-diff-tool/tests/p1 \
  /Users/shotaro/DevHub/CG/ghg-py-diff-tool/tests/p2 \
  --out ../output/two_projects_diff.csv \
  --diff-dir ../output/diffs \
  --ext .py
```
