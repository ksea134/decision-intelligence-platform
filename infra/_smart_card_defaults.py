from __future__ import annotations
from typing import Any

DEFAULT_SMART_CARDS: list[dict[str, Any]] = [
    {"id": "recent", "icon": "⚡", "title": "直近のニュース", "desc": "データ変動の検出", "prompt_template": "データを精査し直近の変動を洗い出してください。"},
    {"id": "notable", "icon": "👁", "title": "気になる兆候", "desc": "注目トレンドの検出", "prompt_template": "中長期的に注目すべきトレンドを抽出してください。"},
    {"id": "alert", "icon": "🚨", "title": "要注意トピック", "desc": "対応必要事項の検出", "prompt_template": "早急に対応が必要な事項を検出してください。"},
    {"id": "kpi", "icon": "📊", "title": "要チェックKPI", "desc": "KPI自動検出", "prompt_template": "BigQueryのデータを集計し重要KPIを分析してください。"},
    {"id": "hint", "icon": "💡", "title": "テーマの発掘", "desc": "検討論点の提案", "prompt_template": "経営層がまだ検討していない重要な論点を提案してください。"},
]
