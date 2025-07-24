以下の3つのプロジェクトにある.pyファイルを"同名"で突き合わせ、存在有無と内容一致/不一致をCSVで出力する。

- "同名" = basenameでの比較

ここでは以下の3つのプロジェクトに対するdiffツールである。
- generalized-hybrid-grains
- GeneralizedHybridGrainsResearch-線形回帰用
- ExtremeSSD

実行方法
- 町田さんマシンの環境
```bash
python3 three_projects_diff.py \
  --p1 /Users/shotaro/DevHub/CG/generalized-hybrid-grains \
  --p2 /Users/shotaro/DevHub/CG/GeneralizedHybridGrainsResearch-線形回帰用 \
  --p3 /Volumes/ExtremeSSD/python/analysis/python/analysis \
  --out ../output/three_projects_diff.csv
```
