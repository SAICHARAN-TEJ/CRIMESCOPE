"""Centralized backend configuration loading and validation."""

import os
from dotenv import load_dotenv

# Load project-root .env file.
# Path: CRIMESCOPE/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If root .env does not exist, load process environment variables.
    load_dotenv(override=True)


class Config:
    """Flask configuration class."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'crimescope-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # JSON configuration - keep non-ASCII characters readable.
    JSON_AS_ASCII = False

    # Language defaults - enforce English-first backend behavior.
    DEFAULT_LOCALE = os.environ.get('DEFAULT_LOCALE', 'en')
    FALLBACK_LOCALE = os.environ.get('FALLBACK_LOCALE', 'en')

    # CrimeScope defaults from PRD baseline.
    SWARM_AGENT_COUNT = int(os.environ.get('SWARM_AGENT_COUNT', '1000'))
    SIMULATION_ROUNDS = int(os.environ.get('SIMULATION_ROUNDS', '30'))
    
    # LLM configuration (OpenAI-compatible format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Zep configuration
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {
        # Documents
        'pdf', 'md', 'txt', 'markdown', 'docx', 'doc', 'rtf',
        # Images (forensic evidence photos)
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'tif',
        # Video (CCTV, body-cam footage metadata)
        'mp4', 'mov', 'avi', 'mkv', 'webm',
        # Spreadsheets / data
        'csv', 'xlsx', 'xls', 'json',
    }

    
    # Text processing configuration
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default chunk overlap
    
    # OASIS simulation configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS actions available on each platform
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent configuration
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def validate(cls):
        """Validate required configuration keys."""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY is not configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY is not configured")
        return errors

