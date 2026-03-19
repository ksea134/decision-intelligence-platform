# DIP Model層 仕様

> 作成日: 2026-03-19
> ステータス: Gemini Flash/Pro実装済み。Model Garden連携はPhase 5後

---

## 1. 現在のモデル構成

| エージェント | モデル | 理由 |
|------------|--------|------|
| ルーター | Gemini 2.5 Flash | 分類だけなので高速・低コスト |
| 汎用回答 | Gemini 2.5 Flash | シンプルな質問は高速で十分 |
| 要因分析 | Gemini 2.5 Pro | 5 Whys等の深い推論が必要 |
| 比較分析 | Gemini 2.5 Pro | 多角的な分析が必要 |
| 予測分析 | Gemini 2.5 Pro | シナリオ分析で精度が重要 |

設定ファイル: `orchestration/adk/agent_definition.py`

## 2. モデル設定

```python
MODEL_ROUTER = "gemini-2.5-flash"   # ルーター: 高速・低コスト
MODEL_FAST   = "gemini-2.5-flash"   # 汎用回答: 高速・低コスト
MODEL_DEEP   = "gemini-2.5-pro"     # 分析・比較・予測: 高精度
```

共通パラメータ:
- `temperature=0.0` — 回答の安定性を最大化

## 3. Gemini vs Claude 性能比較

| | Gemini 2.5 Flash（現行） | Claude Sonnet 4.6 | Claude Opus 4.6 |
|---|---|---|---|
| 速度 | やや遅い（考える時間が長い） | 速い | やや遅い |
| 日本語の自然さ | 自然 | とても自然 | とても自然 |
| 分析の深さ | 深い | 深い | とても深い |
| 指示への忠実さ | たまに従わない | 忠実 | とても忠実 |
| Tool Call安定性 | 発火しないことがある | 安定 | 安定 |
| コスト | 安い | 中程度 | 高い |
| Google連携 | ネイティブ対応 | API経由 | API経由 |

### 開発で感じたこと
- Geminiの弱点: Tool Callを使えと指示しても従わないことがあった
- Claudeの強み: 指示に忠実。「これをやれ」と言えばやる
- Geminiの強み: Googleサービス（BigQuery、GCS）との相性が良い。コストが安い

## 4. 将来のモデル戦略（Model Garden連携）

Model Garden = Google Cloudで複数のAIモデルを切り替えられる仕組み。Phase 5（Cloud Run移行）後に実施。

### 将来の構成

| 用途 | モデル | 選定理由 |
|------|--------|---------|
| 速度重視の簡単な質問 | Gemini 2.5 Flash | 高速・低コスト |
| 標準的な分析 | Gemini 2.5 Pro | 高精度 |
| 高度な推論 | Claude Opus（Model Garden経由） | 最高精度の推論 |
| コード生成 | Claude Sonnet（Model Garden経由） | コード品質が高い |

### Model Garden統合の実装イメージ

```python
class ModelGardenService:
    async def call_claude(self, messages, model="claude-sonnet-4-6") -> str:
        client = anthropic.AnthropicVertex(
            project_id=self.project_id, region=self.location
        )
        response = client.messages.create(
            model=model, max_tokens=4096, messages=messages
        )
        return response.content[0].text

    def select_model(self, task_type: str) -> str:
        model_routing = {
            "complex_reasoning": "claude-opus-4-6",
            "code_generation": "claude-sonnet-4-6",
            "fast_response": "gemini-2.5-flash",
            "data_analysis": "gemini-2.5-pro",
        }
        return model_routing.get(task_type, "gemini-2.5-flash")
```

## 5. 補足・予備知識: AIの回答が毎回変わる理由

AIは「次に来る言葉を確率で選ぶ」仕組み。同じ質問でもサイコロを振るように言葉を選ぶため、毎回少し違う言い回しになる。

- 普通のシステム → 1+1 は必ず 2
- AI → 答えの中身は合っているが、言い方が毎回少し違う

DIPでは`temperature=0.0`で安定化しているが、Gemini 2.5 Flashは内部の「考える」ステップにもランダム性があるため完全に同じにはならない。
