"""Constants and configuration values for the Daily AI Agent."""

from typing import Dict, List

# Application metadata
APP_NAME = "Daily AI Agent"
APP_VERSION = "0.2.0"
APP_DESCRIPTION = "Intelligent morning routine assistant with conversational AI"

# Timeouts (in seconds)
DEFAULT_TIMEOUT = 30
MCP_SERVER_TIMEOUT = 45
HEALTH_CHECK_TIMEOUT = 10
LLM_TIMEOUT = 60

# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 16.0
RETRY_EXPONENTIAL_BASE = 2.0

# Rate limiting
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
CHAT_RATE_LIMIT_PER_MINUTE = 10
BRIEFING_RATE_LIMIT_PER_MINUTE = 20

# Default financial symbols for morning briefing
FINANCIAL_SYMBOLS: List[str] = [
    "MSFT",   # Microsoft
    "NVDA",   # NVIDIA
    "BTC",    # Bitcoin
    "ETH",    # Ethereum
    "VOO",    # Vanguard S&P 500 ETF
    "SMR",    # NuScale Power
    "GOOGL",  # Google/Alphabet
]

# Shuttle stop name mappings for display
SHUTTLE_STOP_NAMES: Dict[str, str] = {
    "mountain_view_caltrain": "Mountain View Caltrain",
    "linkedin_transit_center": "LinkedIn Transit Center",
    "linkedin_950_1000": "LinkedIn 950|1000",
}

# Valid shuttle stop IDs
VALID_SHUTTLE_STOPS: List[str] = [
    "mountain_view_caltrain",
    "linkedin_transit_center",
    "linkedin_950_1000",
]

# Todo bucket options
TODO_BUCKETS: List[str] = [
    "work",
    "home",
    "errands",
    "personal",
]

# Transport modes for commute
TRANSPORT_MODES: List[str] = [
    "driving",
    "transit",
    "bicycling",
    "walking",
]

# Commute directions
COMMUTE_DIRECTIONS: List[str] = [
    "to_work",
    "from_work",
]

# Financial data types
FINANCIAL_DATA_TYPES: List[str] = [
    "stocks",
    "crypto",
    "mixed",
]

# Weather time options
WEATHER_TIMES: List[str] = [
    "today",
    "tomorrow",
]

# LLM configuration
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLM_TEMPERATURE = 0.1

# API response status codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503

# Request headers
REQUEST_ID_HEADER = "X-Request-ID"
RATE_LIMIT_HEADERS = {
    "limit": "X-RateLimit-Limit",
    "remaining": "X-RateLimit-Remaining",
    "reset": "X-RateLimit-Reset",
}

# Environment names
ENV_DEVELOPMENT = "development"
ENV_PRODUCTION = "production"
ENV_TESTING = "testing"

# Calendar event limits
MAX_EVENTS_PER_DAY = 3
MAX_EVENTS_IN_BRIEFING = 5

# Todo display limits
MAX_HIGH_PRIORITY_TODOS = 2
MAX_OTHER_TODOS = 3
MAX_TOTAL_TODOS_DISPLAY = 5
