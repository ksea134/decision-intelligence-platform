# DIP UI/UX層 仕様

> 作成日: 2026-03-19
> ステータス: Streamlit（MVP） → Cloud Run + IAP（本番: Phase 5）

---

## 1. 現在の構成

| 項目 | 内容 |
|------|------|
| フレームワーク | Streamlit |
| エントリポイント | `app.py` → `ui/components/chat.py` |
| デプロイ先 | ローカル（localhost:8501）/ Streamlit Cloud |
| 認証 | なし（URLを知っていれば誰でもアクセス可） |

### 主要ファイル

| ファイル | 役割 |
|---------|------|
| `app.py` | エントリポイント。企業選択→chat描画 |
| `ui/components/chat.py` | チャット画面全体（入力、ストリーミング表示、補足フェーズ） |
| `ui/components/sidebar.py` | サイドバー（企業選択、GCP設定） |
| `ui/components/smart_cards.py` | スマートカード定義（スタブ） |
| `ui/components/infographic.py` | インフォグラフィック描画 |

### カラー定義

| 変数名 | カラーコード | 色名 | 用途 |
|---|---|---|---|
| `_ACCENT` | `#D2FF00` | ライムイエロー（蛍光黄緑） | 見出し・強調文字 |
| `_BLUE` | `#38bdf8` | スカイブルー | 情報表示 |
| `_GREEN` | `#22c55e` | グリーン | 接続済み・成功 |
| `_RED` | `#ff4b4b` | レッド | エラー・警告 |

定義場所: `ui/components/chat.py` 134〜137行目

## 2. 主要機能

| # | 機能 | 説明 |
|---|------|------|
| F01 | マルチ企業対応チャット | companies.csvで企業切替、履歴保持 |
| F05 | ストリーミング回答 | リアルタイムで文字が表示される |
| F06 | 思考ロジック生成 | 4ステップの思考プロセス表示 |
| F07 | インフォグラフィック生成 | JSON→HTML Exec Summary |
| F08 | 深掘り質問生成 | フォローアップ3件 |
| F09 | スマートカード | 5種のショートカットプロンプト |
| F10 | 質問履歴 | 直近5件、再実行・削除 |
| F11 | PNG保存 | html2canvas |
| F12 | PDFエクスポート | html2pdf |
| F13 | テキストコピー | クリップボード |
| F14 | テキストDL | .txt出力 |
| F15 | データソースバッジ | BQ/GCS/ローカル表示 |
| F16 | 接続エラーバナー | 警告UI |
| F17 | 稼働状況パネル | リアルタイム表示 |
| F18 | BQ実行ログパネル | SQL/件数表示 |

## 3. スマートカード仕様

### 5つの固定カード

| ID | アイコン | タイトル | 用途 |
|---|---|---|---|
| `recent` | ⚡ | 週間ニュース | データ変動の検出 |
| `notable` | 👁 | 気になる兆候 | 注目すべき変化 |
| `alert` | 🚨 | 要注意トピック | 緊急対応が必要な事項 |
| `kpi` | 📊 | 要チェックKPI | KPIの状態確認 |
| `hint` | 💡 | テーマの発掘 | 分析テーマの提案 |

### カスタマイズ

| 要素 | カスタマイズ | 管理場所 |
|------|-----------|---------|
| カードの種類（5つ固定） | ❌ 変更不可 | `infra/_smart_card_defaults.py` |
| アイコン・タイトル・説明 | ❌ 全企業共通 | `infra/_smart_card_defaults.py` |
| **プロンプト（質問文）** | **✅ 企業ごとにカスタマイズ可** | `data/{企業名}/smart_cards/{id}.md` |

### 表示タイミング
- チャット履歴が空のとき（会話開始時）だけ表示
- スマートカード経由の質問は質問履歴に追加されない

## 4. 将来のUI（Phase 5: Cloud Run + IAP）

| 項目 | 現在（Streamlit） | 将来（Cloud Run） |
|------|-------------------|-------------------|
| フレームワーク | Streamlit | React / Next.js + FastAPI |
| 認証 | なし | IAP（Google Workspace認証） |
| ストリーミング | Streamlit内蔵 | Server-Sent Events |
| デプロイ | Streamlit Cloud | Cloud Run（Docker） |
| スケーリング | なし | オートスケーリング |

### Phase 5で併せて実施する作業
- キャッシュのStreamlit依存解消 → `memos/層別仕様_Orchestration層.md` 参照
- Memory Store統合（Redis Memorystore）
