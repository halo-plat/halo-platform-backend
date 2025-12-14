from enum import Enum

class AIProviderId(str, Enum):
    OPENAI = "openai"                 # OpenAI Chat Completions
    PERPLEXITY = "perplexity"         # Perplexity Chat Completions (OpenAI-compatible)
    CLOUD_AI = "cloud_ai"             # Gemini generateContent
    NOTION_CALENDAR = "notion_calendar"  # Notion Calendar local deep link (cron://)
    PRO_ACTOR = "pro_actor"           # OpenAI-compatible (generic)
    ECHO = "echo"                     # fallback stub
