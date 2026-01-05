from enum import Enum

class AIProviderId(str, Enum):
    OPENAI = "openai"
    PERPLEXITY = "perplexity"
    CLAUDE = "claude"
    HUGGINGFACE = "huggingface"
    CLOUD_AI = "cloud_ai"
    NOTION_CALENDAR = "notion_calendar"
    PRO_ACTOR = "pro_actor"
    ECHO = "echo"
