# Quick Start Guide

## Installation Steps

### 1. Use a virtual environment (recommended)

On macOS/Linux, Python from Homebrew cannot install packages globally. Use a venv:

```bash
cd monkeybusiness
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

You should see `(.venv)` in your prompt. Run the commands below **one at a time** (do not paste blocks with `#` comments—the shell will try to run `#` as a command).

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install ffmpeg

**macOS:**

```bash
brew install ffmpeg
```

**Ubuntu/Debian:**

```bash
sudo apt install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### 4. Configure Environment

```bash
cp .env.example .env
```

Then **edit `.env`** in any text editor and replace the placeholder with your real OpenAI API key:

- Change `OPENAI_API_KEY=your_openai_api_key_here` to `OPENAI_API_KEY=sk-proj-...` (your actual key).
- Get a key at: https://platform.openai.com/api-keys

Save the file. Without a valid key, the pipeline will fail with "401 Unauthorized".

### 5. Verify Setup

```bash
python check_setup.py
```

You must see **✓ OPENAI_API_KEY is set** and **All checks passed!** before running the pipeline. If you see **✗ OPENAI_API_KEY is missing or still the placeholder**, edit `.env` again and set a real key.

## First Run

Generate your first puzzle video:

```bash
python -m src.main_pipeline --count 1
```

This will create:

- `output/images/puzzle_001.png` - The puzzle image
- `output/videos/puzzle_001.mp4` - The final video (18 seconds)
- `output/metadata/puzzle_001.json` - Complete metadata

## Common Commands

### Generate 10 videos

```bash
python -m src.main_pipeline --count 10
```

Puzzle IDs auto-increment from existing output files, so repeated runs append new IDs instead of overwriting previous outputs.

### Generate with specific difficulty

```bash
python -m src.main_pipeline --count 5 --difficulty 7
```

### Image-only mode (faster, for testing)

```bash
python -m src.main_pipeline --count 20 --skip-video
```

### Generate and post to TikTok

```bash
# First: Add TIKTOK_ACCESS_TOKEN to .env
python -m src.main_pipeline --count 5 --post-to-tiktok
```

### Upload to Google Drive (share folder with TikTok account holder)

```bash
# First: Set GOOGLE_DRIVE_FOLDER_ID in .env and add credentials.json (see README → Google Drive upload)
python -m src.main_pipeline --count 10 --upload-to-drive
```

First run opens a browser to sign in to Google; then videos upload to your folder. Share that folder with your friend so they can download and post.

## Output Structure

```
output/
├── images/          # PNG puzzle images (1080x1350)
├── videos/          # MP4 videos (1080x1920, H.264)
└── metadata/        # JSON metadata for each puzzle
```

## TikTok Setup (Optional)

To enable `--post-to-tiktok`:

1. Register app at https://developers.tiktok.com/
2. Enable Content Posting API with Direct Post
3. Get `video.publish` scope approved
4. Obtain user access token via OAuth
5. Add to `.env`:
   ```
   TIKTOK_ACCESS_TOKEN=act.your_token_here
   ```

**Note:** Unaudited apps can only post as private. Submit for audit to enable public posting.

## Troubleshooting

### "ffmpeg not found"

- Ensure ffmpeg is installed: `ffmpeg -version`
- On macOS: `brew install ffmpeg`
- On Linux: `sudo apt install ffmpeg`

### "OPENAI_API_KEY is required"

- Check `.env` file exists in project root
- Verify key is set: `OPENAI_API_KEY=sk-...`
- Get key from: https://platform.openai.com/api-keys

### Import errors

- Install dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (need 3.9+)

### Video encoding slow

- Reduce quality in `src/config.py`: increase `VIDEO_CRF` (e.g., 28)
- Use faster preset: change `VIDEO_PRESET` to "fast" or "ultrafast"

## Next Steps

- Read [README.md](README.md) for complete documentation
- Check `src/config.py` for customization options
- Explore metadata in `output/metadata/*.json`
- Try batch generation: `--count 50`

## Performance Tips

- Use `--skip-video` for quick puzzle testing
- Generate images first, then batch-create videos
- Adjust `OPENAI_MODEL` in .env (gpt-5-nano is fastest/cheapest; code forces temperature=1 for it)
- For TikTok posting, respect 6 videos/minute rate limit

## Support

- Issues: GitHub issues
- TikTok API: https://developers.tiktok.com/support
- OpenAI API: https://help.openai.com/

Happy puzzle generating! 🧩🎬
