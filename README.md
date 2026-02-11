# Puzzle Video Production Pipeline

Automated production system for generating Raven's Progressive Matrix style puzzle videos optimized for TikTok short-form content.

## Features

- **LLM-Powered Puzzle Generation**: Uses OpenAI API to generate structured puzzle data
- **Deterministic Rendering**: PIL/Pillow-based image generation (no AI art)
- **Automated Video Assembly**: ffmpeg-based video creation with countdown overlays
- **Batch Processing**: Generate hundreds of videos with a single command
- **TikTok Integration**: Optional direct posting via TikTok Content Posting API
- **Structured Metadata**: JSON metadata for all assets

## Architecture

```
puzzle_generator → puzzle_renderer → video_builder → asset_manager → [tiktok_poster]
     (LLM)            (PIL)            (ffmpeg)         (storage)        (optional)
```

## Prerequisites

### Required

1. **Python 3.9+**
2. **ffmpeg** - Install via:
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

3. **OpenAI API Key** - Get from https://platform.openai.com/api-keys

### Optional (for TikTok posting)

4. **TikTok Developer Account** - Register at https://developers.tiktok.com/
5. **TikTok App** with Content Posting API enabled
6. **`video.publish` scope** approved for your app
7. **User Access Token** from OAuth flow

**Important**: Unaudited TikTok API clients can only post videos as private. After successful testing, submit your app for audit to enable public posting.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd monkeybusiness
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

4. **Verify ffmpeg installation**:
   ```bash
   ffmpeg -version
   ```

## Usage

### Basic Usage

Generate a single puzzle video:

```bash
python -m src.main_pipeline
```

Generate multiple videos:

```bash
python -m src.main_pipeline --count 10
```

Puzzle IDs auto-increment from existing output files, so new runs append (for example, `puzzle_021`, `puzzle_022`) instead of overwriting earlier assets.

### Advanced Options

```bash
python -m src.main_pipeline \
  --count 50 \
  --difficulty 5 \
  --output-dir ./custom_output \
  --log-level DEBUG
```

### Image-Only Mode

Generate puzzle images without videos:

```bash
python -m src.main_pipeline --count 20 --skip-video
```

### TikTok Posting

Post generated videos directly to TikTok:

```bash
# First, set TIKTOK_ACCESS_TOKEN in .env
python -m src.main_pipeline --count 5 --post-to-tiktok
```

**Note**: Posting respects TikTok's rate limit of 6 video uploads per minute.

### Google Drive upload (shared folder for TikTok account holder)

Upload each generated video to a Google Drive folder. Share that folder with your friend who has the TikTok account so they can download and post when ready:

```bash
# Set GOOGLE_DRIVE_FOLDER_ID in .env (see Google Drive setup below)
python -m src.main_pipeline --count 10 --upload-to-drive
```

First run with `--upload-to-drive` will open a browser to sign in to Google; a `token.json` is saved so later runs need no login.

## Command-Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--count` | int | 1 | Number of puzzles to generate |
| `--output-dir` | path | `./output` | Custom output directory |
| `--skip-video` | flag | false | Generate images only (skip video creation) |
| `--post-to-tiktok` | flag | false | Post videos to TikTok after generation |
| `--upload-to-drive` | flag | false | Upload each video to Google Drive (GOOGLE_DRIVE_FOLDER_ID) |
| `--difficulty` | int (1-10) | random | Starting difficulty level (cycles through all) |
| `--log-level` | str | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Project Structure

```
monkeybusiness/
├── src/
│   ├── __init__.py
│   ├── models.py              # Puzzle data models and validation
│   ├── config.py              # Configuration and environment variables
│   ├── puzzle_generator.py    # LLM-based puzzle generation
│   ├── puzzle_renderer.py     # PIL/Pillow image rendering
│   ├── video_builder.py       # ffmpeg video assembly
│   ├── asset_manager.py       # File storage and metadata
│   ├── tiktok_poster.py       # TikTok Content Posting API integration
│   └── main_pipeline.py       # Orchestration and CLI
├── output/                    # Created at runtime
│   ├── images/               # Rendered puzzle images
│   ├── videos/               # Final MP4 videos
│   └── metadata/             # JSON metadata files
├── templates/                # Optional fonts and assets
├── requirements.txt
├── .env.example
└── README.md
```

## Output

Each puzzle generates:

1. **Image** (`output/images/{puzzle_id}.png`): Rendered puzzle grid with options
2. **Video** (`output/videos/{puzzle_id}.mp4`): 18-second TikTok-ready video:
   - Slide 1 (2s): Intro hook
   - Slide 2 (8s): Puzzle with countdown timer
   - Slide 3 (3s): Answer reveal
   - Slide 4 (5s): Explanation
3. **Metadata** (`output/metadata/{puzzle_id}.json`): Complete puzzle data, asset paths, timestamps, and optional TikTok publish info

## Video Specifications

- **Format**: MP4 (H.264)
- **Resolution**: 1080x1920 (vertical, TikTok-optimized)
- **Frame Rate**: 24 fps
- **Codec**: libx264 with CRF 23
- **Compatibility**: Meets TikTok Content Posting API requirements

## TikTok Integration

### Setup

1. **Register your app** at https://developers.tiktok.com/
2. **Enable Content Posting API** with Direct Post configuration
3. **Request `video.publish` scope** approval
4. **Implement OAuth** to obtain user access tokens (see [TikTok OAuth docs](https://developers.tiktok.com/doc/login-kit-web))
5. **Add token to `.env`**:
   ```env
   TIKTOK_ACCESS_TOKEN=act.your_access_token_here
   ```

### Privacy Levels

The pipeline supports these privacy levels (must match creator's allowed options):

- `PUBLIC_TO_EVERYONE`: Public posts (requires audited API client)
- `MUTUAL_FOLLOW_FRIENDS`: Friends only
- `FOLLOWER_OF_CREATOR`: Followers only
- `SELF_ONLY`: Private (default, works for unaudited clients)

Set default in `.env`:
```env
TIKTOK_PRIVACY_LEVEL=SELF_ONLY
```

### Rate Limiting

TikTok enforces:
- **6 video init requests per minute** per user access token
- The pipeline automatically throttles requests to stay within limits
- Batch jobs adjust posting speed accordingly

### API Documentation

- [Content Posting API - Get Started](https://developers.tiktok.com/doc/content-posting-api-get-started)
- [Direct Post API Reference](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post)

## Google Drive upload

Upload generated videos to a Drive folder and share that folder with your TikTok account holder so they can download and post when ready.

### Setup

1. **Google Cloud project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/), create or select a project.
   - Enable the **Google Drive API** (APIs & Services → Library → search "Drive API" → Enable).
   - Create **OAuth 2.0 credentials**: APIs & Services → Credentials → Create Credentials → OAuth client ID.
   - Application type: **Desktop app**. Name it (e.g. "Puzzle pipeline"). Download the JSON.
   - Rename the downloaded file to `credentials.json` and put it in the **project root** (same folder as `src/`).

2. **Drive folder**
   - In [Google Drive](https://drive.google.com/), create a folder (e.g. "Puzzle videos for TikTok").
   - Open the folder. The URL is `https://drive.google.com/drive/folders/FOLDER_ID`. Copy `FOLDER_ID`.
   - In `.env` set: `GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here`.
   - (Optional) Share the folder with your friend’s Google account (Editor or Viewer) so they can access the videos.

3. **First run**
   - Run: `python -m src.main_pipeline --count 1 --upload-to-drive`
   - A browser will open to sign in to Google; approve access. A `token.json` is saved in the project root.
   - Later runs with `--upload-to-drive` use this token and do not prompt for login.

### Usage

```bash
python -m src.main_pipeline --count 10 --upload-to-drive
```

Videos are uploaded to the folder; metadata JSON is updated with `drive_file_id` for each puzzle.

## Configuration

Customize behavior via environment variables in `.env`:

### Core Settings

```env
# Required
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-nano               # or gpt-5-mini, gpt-4o-mini, gpt-4
OPENAI_TEMPERATURE=0.7                # 0-2; for gpt-5-nano the code forces 1.0 (API limit)

# Optional
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

### Video Settings (in `src/config.py`)

```python
VIDEO_RESOLUTION = (1080, 1920)       # Width x Height
VIDEO_FPS = 24
SLIDE_INTRO_DURATION = 2.0            # seconds
SLIDE_PUZZLE_DURATION = 8.0
SLIDE_ANSWER_DURATION = 3.0
SLIDE_EXPLANATION_DURATION = 5.0
COUNTDOWN_START = 5                   # Start countdown from 5
```

### Image Settings

```python
IMAGE_SIZE = (1080, 1350)             # Width x Height
IMAGE_BACKGROUND = (255, 255, 255)    # White
GRID_LINE_WIDTH = 3
SHAPE_LINE_WIDTH = 4
```

## Puzzle Format

Puzzles follow this JSON schema (5–8 answer options for harder, more natural quizzes):

```json
{
  "id": "puzzle_001",
  "puzzle_type": "matrix_reasoning",
  "difficulty": 5,
  "question_text": "Which one completes the pattern?",
  "grid_logic": "row1: circle, square, triangle; row2: filled-circle, filled-square, filled-triangle; row3: large-circle, large-square, ?; rule: fill and size increase",
  "options": ["A: large-triangle", "B: large-filled-triangle", "C: filled-triangle", "D: small-triangle", "E: small-filled-triangle", "F: large-circle"],
  "correct_answer": "B: large-filled-triangle",
  "explanation": "The pattern shows shapes increasing in fill and size across rows and columns."
}
```

## Extending the Pipeline

### Adding New Puzzle Types

1. Add type to `Literal` in `src/models.py`
2. Update validation in `validate_puzzle()`
3. Add rendering logic in `puzzle_renderer.py`
4. Update LLM prompt in `puzzle_generator.py`

### Adding Caption Generation

Implement in pipeline:

```python
def generate_caption(puzzle: Puzzle) -> str:
    # Use puzzle.question_text or call LLM for creative caption
    return caption[:2200]  # TikTok limit
```

### Adding Other Platforms

Create a new poster module (e.g., `youtube_poster.py`) following the `TikTokPoster` pattern, then add CLI flag `--post-to-youtube`.

## Troubleshooting

### Common Issues

**"ffmpeg not found"**
- Ensure ffmpeg is installed and in PATH
- Test with `ffmpeg -version`

**"OpenAI API key is required"**
- Check `.env` file exists and has `OPENAI_API_KEY=...`
- Verify key is valid at https://platform.openai.com/api-keys

**"TikTok API error: access_token_invalid"**
- Access tokens expire; regenerate via OAuth flow
- Ensure token has `video.publish` scope

**"TikTok API error: unaudited_client_can_only_post_to_private_accounts"**
- Your app hasn't been audited yet
- Posts will be private until audit completes
- Use `TIKTOK_PRIVACY_LEVEL=SELF_ONLY` for testing

**"Rate limit exceeded"**
- TikTok limits to 6 video init calls per minute
- Pipeline auto-throttles; wait for batch to complete
- Reduce `--count` or run multiple smaller batches

**Video encoding errors**
- Check ffmpeg installation supports H.264
- Try reducing video quality in config (increase `VIDEO_CRF`)

## Performance

- **Puzzle generation**: ~2-5 seconds per puzzle (depends on LLM)
- **Image rendering**: ~0.5 seconds per image
- **Video creation**: ~5-10 seconds per video (ffmpeg encoding)
- **TikTok upload**: ~10-30 seconds per video (depends on network)

**Estimated batch times**:
- 10 videos (no posting): ~2-3 minutes
- 10 videos (with TikTok): ~5-7 minutes
- 50 videos (with TikTok): ~25-35 minutes (rate-limited)

## Testing

Run a quick test:

```bash
python -m src.main_pipeline --count 2 --skip-video
```

Check `output/images/` and `output/metadata/` for results.

## License

[Add your license here]

## Contributing

[Add contribution guidelines]

## Support

For issues related to:
- **Pipeline code**: Open an issue in this repository
- **TikTok API**: See [TikTok Developer Support](https://developers.tiktok.com/support)
- **OpenAI API**: See [OpenAI Help Center](https://help.openai.com/)
