from enum import Enum


class Events(str, Enum):
    """Enumeration of possible event types."""

    CHECKPOINT = "checkpoint"
    CONTENT = "content"
    SEARCH_START = "search_start"
    SEARCH_RESULT = "search_result"
    DATE_RESULT = "date_result"
    COMPLETION_END = "end"


class Feedback(str, Enum):
    """Enumeration of possible feedback types."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = None
