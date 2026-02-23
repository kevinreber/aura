"""Intent classification service using Hugging Face zero-shot classification.

Provides fast, lightweight intent detection to route simple queries directly
to tools without calling the LLM, reducing latency and API costs.
"""

from typing import Dict, List, Optional, Tuple
from loguru import logger

# Lazy-loaded to avoid slow import at startup
_classifier = None

# Tool intent labels mapped to the agent's tool names
TOOL_INTENTS: Dict[str, str] = {
    "weather forecast": "get_weather",
    "calendar schedule meetings": "get_calendar",
    "todo tasks": "get_todos",
    "financial stocks crypto market": "get_financial_data",
    "commute travel directions": "get_commute",
    "morning briefing daily summary": "get_morning_briefing",
}

# Candidate labels for the zero-shot classifier
CANDIDATE_LABELS: List[str] = list(TOOL_INTENTS.keys())

# Default model - small and fast on CPU
DEFAULT_MODEL = "cross-encoder/nli-deberta-v3-small"


def _get_classifier(model_name: str = DEFAULT_MODEL):
    """Lazy-load the zero-shot classification pipeline."""
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline

            logger.info(f"Loading intent classification model: {model_name}")
            _classifier = pipeline(
                "zero-shot-classification",
                model=model_name,
                device=-1,  # CPU
            )
            logger.info("Intent classification model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load intent classification model: {e}")
            raise
    return _classifier


class IntentClassifier:
    """Classifies user messages into tool intents using zero-shot classification."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        confidence_threshold: float = 0.70,
        enabled: bool = True,
    ) -> None:
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.enabled = enabled
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        """Ensure the model is loaded. Returns False if loading fails."""
        if self._loaded:
            return True
        try:
            _get_classifier(self.model_name)
            self._loaded = True
            return True
        except Exception:
            self.enabled = False
            return False

    def classify(self, message: str) -> Tuple[Optional[str], float]:
        """
        Classify a user message into a tool intent.

        Args:
            message: The user's natural language input.

        Returns:
            Tuple of (tool_name, confidence). tool_name is None if confidence
            is below threshold or classification is disabled/unavailable.
        """
        if not self.enabled:
            return None, 0.0

        if not self._ensure_loaded():
            return None, 0.0

        try:
            classifier = _get_classifier(self.model_name)
            result = classifier(message, CANDIDATE_LABELS, multi_label=False)

            top_label = result["labels"][0]
            top_score = result["scores"][0]

            tool_name = TOOL_INTENTS.get(top_label)

            logger.debug(
                f"Intent classification: '{message[:50]}...' -> "
                f"{top_label} ({top_score:.2f}) -> tool={tool_name}"
            )

            if top_score >= self.confidence_threshold and tool_name:
                return tool_name, top_score

            return None, top_score

        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return None, 0.0

    def classify_with_details(self, message: str) -> Dict:
        """
        Classify with full details for debugging/logging.

        Returns dict with all labels, scores, and the selected tool.
        """
        if not self.enabled or not self._ensure_loaded():
            return {"enabled": False, "tool": None, "confidence": 0.0}

        try:
            classifier = _get_classifier(self.model_name)
            result = classifier(message, CANDIDATE_LABELS, multi_label=False)

            top_label = result["labels"][0]
            top_score = result["scores"][0]
            tool_name = TOOL_INTENTS.get(top_label)

            return {
                "enabled": True,
                "tool": tool_name if top_score >= self.confidence_threshold else None,
                "confidence": top_score,
                "threshold": self.confidence_threshold,
                "all_scores": dict(zip(result["labels"], result["scores"])),
            }
        except Exception as e:
            return {"enabled": True, "error": str(e), "tool": None, "confidence": 0.0}
