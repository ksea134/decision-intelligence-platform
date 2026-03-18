# Decision Intelligence Platform — 進捗状況
> 最終更新: 2026-03-17
> 目的: 新規チャット開始時にClaudeが現状を把握するためのファイル

---

## 現在のフェーズ: Phase 2 — Memory Store統合

### 完了済み ✅

| 項目 | 完了日 | 備考 |
|------|--------|------|
| SPEC_v1.md 作成 | 2026-03-15 | 仕様抽出完了 |
| アーキテクチャ設計 | 2026-03-15 | 7層構造確定 |
| Track 1: UI/Logic分離 | 2026-03-16 | Interface + 実装済み |
| Track 2: Agent Router | 2026-03-16 | LangGraph統合、フロー動作確認済み |

### 進行中 🔄

| 項目 | 開始日 | ゴール |
|------|--------|--------|
| Phase 2: Memory Store | 2026-03-17 | Redis Memorystore接続 |

### 未着手 ⬜

| 項目 | 依存関係 |
|------|----------|
| Phase 3: Vertex AI Search統合 | Phase 2完了後 |
| Phase 4: Agent Builder統合 | Phase 1-3完了後 |
| InlineViz（文中描画） | Agent Router安定後 |

---

## 実装済みコンポーネント

### Orchestration層
- `reasoning_engine.py` — 推論制御（LangGraph統合済み）
- Agent Router — 意図分類 → エージェント呼び出し

### Interface定義済み
- CacheInterface
- MemoryStoreInterface（短期記憶）
- （追加があれば記載）

---

## 今日の作業 (2026-03-17)

### 目標
Redis Memorystore接続の実装

### タスク
1. [ ] GCP Memorystore for Redis インスタンス作成（または既存確認）
2. [ ] RedisMemoryStore クラス実装
3. [ ] 会話履歴の永続化テスト
4. [ ] InMemoryStore → RedisMemoryStore 切り替え確認

---

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| UI | Streamlit（将来: Cloud Run + IAP） |
| Orchestration | LangGraph |
| Model | Gemini 1.5 Pro / Flash |
| Storage | BigQuery, GCS, Redis Memorystore |
| Infrastructure | GCP |

---

## 次回チャット開始時の指示

```
このプロジェクトの進捗は PROJECT_STATUS.md を参照してください。
前回の続きから作業を再開します。
```

---

*このファイルは作業終了時に更新すること*
