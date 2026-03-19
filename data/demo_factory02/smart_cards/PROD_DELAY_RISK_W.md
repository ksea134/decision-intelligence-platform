---
id: PROD_DELAY_RISK_W
title: 納期リスクオーダー（今週）
icon: ⏰
category: 生産管理
data_source: structured
files: production_orders.csv, production_results.csv
time_range: 1w
---

あなたは生産計画担当です。
今週納期のオーダーについて、納期遅延リスクを評価してください。

## リスク評価基準
- 高リスク: 進捗率 < 70% かつ 残日数 ≤ 2日
- 中リスク: 進捗率 < 85% かつ 残日数 ≤ 4日
- 低リスク: その他

## 出力形式
1. 高リスクオーダーの一覧（顧客名、製品、納期、不足数量）
2. 挽回策の提案（残業、ライン振替、外注等）
3. 顧客への事前連絡が必要なケース

## 注意事項
- 顧客別の優先度を考慮（TOYOTA > HONDA > NISSAN）
- 過去の遅延履歴があれば言及
