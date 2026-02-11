#!/usr/bin/env python3
"""Quick validation script to check pipeline setup."""

import sys
from pathlib import Path

def check_imports():
    """Check if all required modules can be imported."""
    print("Checking imports...")
    try:
        from src import models, config, puzzle_generator, puzzle_renderer
        from src import video_builder, asset_manager, tiktok_poster, main_pipeline
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\nChecking dependencies...")
    missing = []
    
    try:
        import openai
        print("✓ openai installed")
    except ImportError:
        print("✗ openai not installed")
        missing.append("openai")
    
    try:
        from PIL import Image
        print("✓ Pillow (PIL) installed")
    except ImportError:
        print("✗ Pillow not installed")
        missing.append("Pillow")
    
    try:
        import dotenv
        print("✓ python-dotenv installed")
    except ImportError:
        print("✗ python-dotenv not installed")
        missing.append("python-dotenv")
    
    try:
        import pydantic
        print("✓ pydantic installed")
    except ImportError:
        print("✗ pydantic not installed")
        missing.append("pydantic")
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def check_ffmpeg():
    """Check if ffmpeg is available."""
    print("\nChecking ffmpeg...")
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # Get first line (version info)
            version_line = result.stdout.split('\n')[0]
            print(f"✓ ffmpeg found: {version_line}")
            return True
        else:
            print("✗ ffmpeg found but returned error")
            return False
    except FileNotFoundError:
        print("✗ ffmpeg not found in PATH")
        print("  Install: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")
        return False

def check_env_file():
    """Check if .env file exists and OPENAI_API_KEY is set to a real value."""
    print("\nChecking environment configuration...")
    env_path = Path(".env")
    
    if not env_path.exists():
        print("✗ .env file not found")
        print("  Copy .env.example to .env and add your API keys")
        return False
    
    print("✓ .env file exists")
    
    # Parse .env for OPENAI_API_KEY value
    openai_key_value = None
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                openai_key_value = line.split("=", 1)[1].strip().strip('"\'')
                break
    
    # Placeholders that mean "not set"
    placeholders = (
        "",
        "your_openai_api_key_here",
        "your_ope",
        "sk-your-key-here",
    )
    is_placeholder = (
        openai_key_value is None
        or not openai_key_value
        or any(p in openai_key_value.lower() for p in ("your_ope", "your_openai", "key_here", "replace_me"))
    )
    
    if not is_placeholder and openai_key_value and len(openai_key_value) > 20:
        print("✓ OPENAI_API_KEY is set (required for puzzle generation)")
        return True
    else:
        print("✗ OPENAI_API_KEY is missing or still the placeholder")
        print("  1. Open .env in your editor")
        print("  2. Replace your_openai_api_key_here with your real key from https://platform.openai.com/api-keys")
        print("  3. Save the file and run this check again")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("Puzzle Video Pipeline - Setup Validation")
    print("=" * 60)
    
    results = []
    
    results.append(("Dependencies", check_dependencies()))
    results.append(("Imports", check_imports()))
    results.append(("ffmpeg", check_ffmpeg()))
    results.append(("Environment", check_env_file()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All checks passed! You're ready to run the pipeline.")
        print("\nTry: python -m src.main_pipeline --count 1")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
