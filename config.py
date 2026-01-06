# config.py

APP_NAME = "Content Creator Multi-Agent"

MAX_HISTORY = 10

ALLOWED_DOMAINS = [
    "beauty",
    "skincare",
    "cosmetics",
    "haircare",
    "makeup"
]

# Models (update later)
LLM_MODEL = "arcee-ai/trinity-mini:free"

# Feature flags
ENABLE_WEB_SEARCH = True
ENABLE_IMAGE_GEN = True
ENABLE_LINKEDIN_POST = False
TAVILY_API_KEY = 
OPENROUTER_API_KEY =
HF_API_TOKEN =
HF_IMAGE_MODEL = 
LINKEDIN_UGC_URL = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_USER_ID = 
LINKEDIN_ACCESS_TOKEN = 