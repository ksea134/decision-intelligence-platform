from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RootCauseAgent:
    """
    Root cause analysis agent. Phase 2 implementation.
    Identifies reasons behind metric changes using BQ data and documents.
    """

    def analyze(self, question: str, data_context: Any) -> str:
        """Perform root cause analysis. Returns empty string until Phase 2."""
        logger.info("RootCauseAgent.analyze called (not yet implemented)")
        return ""
