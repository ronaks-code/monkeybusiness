"""Configuration settings for the puzzle video pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
WORKSPACE_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", WORKSPACE_ROOT / "output"))

# Output subdirectories
IMAGES_DIR = OUTPUT_DIR / "images"
VIDEOS_DIR = OUTPUT_DIR / "videos"
METADATA_DIR = OUTPUT_DIR / "metadata"

# Templates directory (for fonts, intro/outro assets)
TEMPLATES_DIR = WORKSPACE_ROOT / "templates"

# Image rendering settings
IMAGE_SIZE = (1080, 1350)  # Width x Height for puzzle image
IMAGE_BACKGROUND = (255, 255, 255)  # White background (fallback)
IMAGE_BACKGROUND_QUIZ = (252, 252, 254)  # Softer off-white for quiz UI
IMAGE_MARGIN = 50  # Pixels margin around content
GRID_LINE_WIDTH = 3
SHAPE_LINE_WIDTH = 4

# Video settings
VIDEO_RESOLUTION = (1080, 1920)  # Vertical format for TikTok
VIDEO_FPS = 24
VIDEO_CODEC = "libx264"  # H.264 for TikTok compatibility
VIDEO_PRESET = "medium"  # Encoding speed/quality tradeoff
VIDEO_CRF = 23  # Constant Rate Factor (lower = better quality, 18-28 typical)

# Slide durations (seconds)
SLIDE_INTRO_DURATION = 2.0
SLIDE_PUZZLE_DURATION = 8.0  # Includes countdown
SLIDE_ANSWER_DURATION = 3.0
SLIDE_EXPLANATION_DURATION = 5.0

# Countdown settings
COUNTDOWN_START = 5  # Start countdown from this number
COUNTDOWN_POSITION = (50, 50)  # Top-left position in pixels

# Font settings (use system fonts or place custom fonts in templates/)
FONT_LARGE_SIZE = 80
FONT_MEDIUM_SIZE = 60
FONT_SMALL_SIZE = 40

# OpenAI / LLM settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
OPENAI_MAX_RETRIES = 2

# TikTok Content Posting API settings
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")
TIKTOK_PRIVACY_LEVEL = os.getenv("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY")
TIKTOK_API_BASE_URL = "https://open.tiktokapis.com"

# TikTok rate limiting (6 requests per minute for /video/init/)
TIKTOK_RATE_LIMIT_PER_MINUTE = 6
TIKTOK_RATE_LIMIT_WINDOW = 60  # seconds

# Video upload settings for TikTok
TIKTOK_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks for file upload
TIKTOK_UPLOAD_TIMEOUT = 3600  # 1 hour max for upload completion

# Caption settings
MAX_CAPTION_LENGTH = 2200  # UTF-16 runes (TikTok limit)

# Google Drive upload (optional; for --upload-to-drive)
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
GOOGLE_DRIVE_CREDENTIALS_PATH = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH")
GOOGLE_DRIVE_TOKEN_PATH = os.getenv("GOOGLE_DRIVE_TOKEN_PATH")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def ensure_directories():
    """Create output directories if they don't exist."""
    for directory in [OUTPUT_DIR, IMAGES_DIR, VIDEOS_DIR, METADATA_DIR, TEMPLATES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def validate_config():
    """Validate required configuration settings.
    
    Raises:
        ValueError: If required settings are missing or invalid
    """
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required. "
            "Please set it in your .env file or environment."
        )
    
    # TikTok token is optional (only needed for --post-to-tiktok)
    # Will be validated when posting is requested


def get_config_summary() -> dict:
    """Return a dictionary of current configuration (excluding secrets)."""
    return {
        "output_dir": str(OUTPUT_DIR),
        "image_size": IMAGE_SIZE,
        "video_resolution": VIDEO_RESOLUTION,
        "video_fps": VIDEO_FPS,
        "openai_model": OPENAI_MODEL,
        "tiktok_privacy_level": TIKTOK_PRIVACY_LEVEL,
    }
