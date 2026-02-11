"""Video assembly using ffmpeg for TikTok-ready short-form content."""

import subprocess
import tempfile
import logging
import shutil
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from . import config

logger = logging.getLogger(__name__)


class VideoBuilder:
    """Builds short-form puzzle videos using ffmpeg."""
    
    def __init__(self, resolution: Optional[Tuple[int, int]] = None, fps: Optional[int] = None):
        """Initialize video builder."""
        self.resolution = resolution or config.VIDEO_RESOLUTION
        self.fps = fps or config.VIDEO_FPS
        self.codec = config.VIDEO_CODEC
        self.preset = config.VIDEO_PRESET
        self.crf = config.VIDEO_CRF
        
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise RuntimeError("ffmpeg not found. Please install ffmpeg and add it to PATH.")
    
    def _draw_gradient_bg(self, image: Image.Image, top_rgb: tuple, bottom_rgb: tuple) -> None:
        """Fill image with a vertical gradient using bands (fast)."""
        w, h = self.resolution[0], self.resolution[1]
        draw = ImageDraw.Draw(image)
        band = max(1, h // 120)
        for y in range(0, h, band):
            t = y / max(h - 1, 1)
            r = int(top_rgb[0] * (1 - t) + bottom_rgb[0] * t)
            g = int(top_rgb[1] * (1 - t) + bottom_rgb[1] * t)
            b = int(top_rgb[2] * (1 - t) + bottom_rgb[2] * t)
            draw.rectangle([0, y, w, min(y + band, h)], fill=(r, g, b))

    def _create_text_slide(
        self, text: str, output_path: Path, font_size: int = 60,
        text_color=(255, 255, 255), bg_color=(30, 30, 30), gradient: bool = False
    ) -> Path:
        """Create a text slide image (optionally with gradient background)."""
        image = Image.new("RGB", self.resolution, bg_color)
        if gradient:
            self._draw_gradient_bg(image, (45, 35, 75), (25, 20, 45))  # Soft purple
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()
        words = text.split()
        lines, current_line = [], []
        max_width = self.resolution[0] - 120
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        line_height = font_size + 12
        total_h = len(lines) * line_height
        y = self.resolution[1] // 2 - total_h // 2
        for line in lines:
            draw.text((self.resolution[0] // 2, y), line, fill=text_color, anchor="mt", font=font)
            y += line_height
        image.save(output_path, "PNG")
        return output_path

    def _create_intro_slide(self, question_text: Optional[str], output_path: Path) -> Path:
        """Create an engaging intro slide with hook copy."""
        hooks = [
            "Think you can get it?",
            "Can you spot the pattern?",
            "Ready?",
            "Which one completes it?",
        ]
        text = (question_text or "").strip()
        if not text or len(text) > 50:
            import random
            text = random.choice(hooks)
        return self._create_text_slide(
            text, output_path, font_size=64, text_color=(255, 255, 255),
            bg_color=(40, 35, 65), gradient=True
        )

    def _create_answer_slide(self, answer: str, output_path: Path) -> Path:
        """Create answer reveal slide: 'The answer is…' then big letter."""
        image = Image.new("RGB", self.resolution, (28, 28, 38))
        self._draw_gradient_bg(image, (50, 45, 80), (30, 28, 50))
        draw = ImageDraw.Draw(image)
        try:
            font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 52)
            font_main = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 160)
        except Exception:
            font_sub = font_main = ImageFont.load_default()
        cx, cy = self.resolution[0] // 2, self.resolution[1] // 2
        draw.text((cx, cy - 120), "The answer is…", fill=(220, 215, 255), anchor="mt", font=font_sub)
        # Answer can be "A" or "A: something" — show just the letter
        letter = answer.strip().upper()
        if ":" in letter:
            letter = letter.split(":")[0].strip()
        if len(letter) > 1:
            letter = letter[0]
        draw.text((cx, cy + 20), letter, fill=(255, 230, 100), anchor="mt", font=font_main)
        image.save(output_path, "PNG")
        return output_path

    def _create_explanation_slide(self, explanation: str, output_path: Path) -> Path:
        """Create explanation slide with 'Here's why' header and wrapped body."""
        image = Image.new("RGB", self.resolution, (32, 30, 42))
        self._draw_gradient_bg(image, (48, 42, 72), (28, 26, 48))
        draw = ImageDraw.Draw(image)
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            font_body = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
        except Exception:
            font_title = font_body = ImageFont.load_default()
        cx = self.resolution[0] // 2
        draw.text((cx, 180), "Here's why", fill=(255, 248, 220), anchor="mt", font=font_title)
        words = explanation.split()
        lines, current_line = [], []
        max_width = self.resolution[0] - 140
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font_body)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        y = 280
        for line in lines:
            draw.text((cx, y), line, fill=(230, 225, 245), anchor="mt", font=font_body)
            y += 50
        image.save(output_path, "PNG")
        return output_path
    
    def _create_countdown_frames(
        self, puzzle_image_path: Path, output_dir: Path
    ) -> list:
        """Create countdown overlay frames using PIL (no ffmpeg drawtext).
        Returns list of paths to countdown_00.png, countdown_01.png, ...
        """
        base = Image.open(puzzle_image_path).convert("RGB")
        w, h = self.resolution
        # Scale and pad to video size
        base = base.resize((w, h), Image.Resampling.LANCZOS)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
        except Exception:
            font = ImageFont.load_default()
        paths = []
        for i, num in enumerate(range(config.COUNTDOWN_START, 0, -1)):
            frame = base.copy()
            draw = ImageDraw.Draw(frame)
            text = str(num)
            # Semi-transparent box and number at top-left
            x, y = 50, 50
            bbox = draw.textbbox((x, y), text, font=font)
            pad = 20
            draw.rectangle(
                [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
                fill=(0, 0, 0), outline=(255, 255, 0), width=4
            )
            draw.text((x, y), text, fill=(255, 255, 0), font=font)
            path = output_dir / f"countdown_{i:02d}.png"
            frame.save(path, "PNG")
            paths.append(path)
        return paths
    
    def build_video(
        self, puzzle_id: str, puzzle_image_path: Path, answer: str,
        explanation: str, question_text: Optional[str] = None,
        output_path: Optional[Path] = None, audio_path: Optional[Path] = None
    ) -> Path:
        """Build a complete puzzle video (no ffmpeg drawtext; uses PIL for countdown)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create slides (engaging intro, answer reveal, explanation)
            slide1_path = temp_path / "slide1.png"
            self._create_intro_slide(question_text, slide1_path)
            countdown_paths = self._create_countdown_frames(puzzle_image_path, temp_path)
            num_countdown_frames = len(countdown_paths)
            countdown_fps = num_countdown_frames / config.SLIDE_PUZZLE_DURATION
            slide3_path = temp_path / "slide3.png"
            self._create_answer_slide(answer, slide3_path)
            slide4_path = temp_path / "slide4.png"
            self._create_explanation_slide(explanation, slide4_path)
            
            logger.info("Created all slides (countdown via PIL)")
            
            w, h, fps = self.resolution[0], self.resolution[1], self.fps
            # No drawtext: scale+pad+concat only. Use -t on loop inputs so duration is finite.
            filter_complex = (
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v0];"
                f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v1];"
                f"[2:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v2];"
                f"[3:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v3];"
                f"[v0][v1][v2][v3]concat=n=4:v=1:a=0[outv]"
            )
            
            if output_path is None:
                output_path = temp_path / f"{puzzle_id}.mp4"
            
            # Limit looped inputs with -t so ffmpeg finishes (no infinite stream).
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-framerate", str(fps), "-t", str(config.SLIDE_INTRO_DURATION), "-i", str(slide1_path),
                "-framerate", str(countdown_fps), "-i", str(temp_path / "countdown_%02d.png"),
                "-loop", "1", "-framerate", str(fps), "-t", str(config.SLIDE_ANSWER_DURATION), "-i", str(slide3_path),
                "-loop", "1", "-framerate", str(fps), "-t", str(config.SLIDE_EXPLANATION_DURATION), "-i", str(slide4_path),
                "-filter_complex", filter_complex, "-map", "[outv]"
            ]
            
            if audio_path and Path(audio_path).exists():
                total = sum([
                    config.SLIDE_INTRO_DURATION, config.SLIDE_PUZZLE_DURATION,
                    config.SLIDE_ANSWER_DURATION, config.SLIDE_EXPLANATION_DURATION
                ])
                cmd.extend(["-i", str(audio_path), "-t", str(total), "-c:a", "aac", "-b:a", "128k"])
            
            cmd.extend([
                "-c:v", self.codec, "-preset", self.preset, "-crf", str(self.crf),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)
            ])
            
            logger.info("Running ffmpeg...")
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                logger.info(f"Video created: {output_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"ffmpeg failed: {e.stderr}")
                raise RuntimeError(f"Failed to create video: {e.stderr}")
            
            if output_path.parent == temp_path:
                final_path = Path(f"{puzzle_id}.mp4")
                shutil.copy2(output_path, final_path)
                return final_path
            
            return output_path
