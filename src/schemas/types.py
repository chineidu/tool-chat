from enum import Enum


class OpenRouterModels(str, Enum):
    """OpenRouter LLMs."""

    GEMINI_2_0_FLASH_001 = "google/gemini-2.0-flash-001"
    GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
    GPT_OSS_120B = "openai/gpt-oss-120b"
    GPT_OSS_20B = "openai/gpt-oss-20b"
    GPT_5_NANO = "openai/gpt-5-nano"
    LLAMA_3_3_70B_INSTRUCT = "meta-llama/llama-3.3-70b-instruct"
    LLAMA_3_8B_INSTRUCT = "meta-llama/llama-3-8b-instruct"
    NEMOTRON_NANO_9B_V2 = "nvidia/nemotron-nano-9b-v2"
    QWEN3_30B_A3B = "qwen/qwen3-30b-a3b"
    QWEN3_NEXT_80B_A3B_INSTRUCT = "qwen/qwen3-next-80b-a3b-instruct"
    QWEN3_32B = "qwen/qwen3-32b"
    SAO10K_L3_LUNARIS_8B = "sao10k/l3-lunaris-8b"
    X_AI_GROK_4_FAST = "x-ai/grok-4-fast"
    X_AI_GROK_CODE_FAST_1 = "x-ai/grok-code-fast-1"
    Z_AI_GLM_4_5 = "z-ai/glm-4.5"


class GroqModels(str, Enum):
    """Groq LLMs."""

    GPT_OSS_20B = "openai/gpt-oss-20b"
    GPT_OSS_120B = "openai/gpt-oss-120b"
    LLAMA_GUARD_4_12B = "meta-llama/llama-guard-4-12b"
    LLAMA_3_1_8B_INSTANT = "llama-3.1-8b-instant"
    QWEN3_32B = "qwen/qwen3-32b"


class ModelProvider(str, Enum):
    OPENROUTER = "openrouter"
    GROQ = "groq"


type RemoteModel = GroqModels | OpenRouterModels


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
