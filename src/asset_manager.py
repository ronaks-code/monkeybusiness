"""Asset management for puzzle images, videos, and metadata."""

import json
import shutil
import re
from pathlib import Path
from typing import Union, Optional
from datetime import datetime
from PIL import Image

from . import config
from .models import Puzzle


class AssetManager:
    """Manages storage and retrieval of puzzle assets."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize asset manager.
        
        Args:
            output_dir: Optional custom output directory (defaults to config.OUTPUT_DIR)
        """
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.images_dir = self.output_dir / "images"
        self.videos_dir = self.output_dir / "videos"
        self.metadata_dir = self.output_dir / "metadata"
        
        # Create directories
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create output directories if they don't exist."""
        for directory in [self.output_dir, self.images_dir, self.videos_dir, self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _sanitize_id(self, puzzle_id: str) -> str:
        """Sanitize puzzle ID for use in filenames.
        
        Args:
            puzzle_id: Raw puzzle ID
            
        Returns:
            Sanitized ID safe for filenames
        """
        # Replace any non-alphanumeric characters with underscores
        return "".join(c if c.isalnum() or c in ["-", "_"] else "_" for c in puzzle_id)

    def get_next_puzzle_index(self) -> int:
        """Return the next available numeric puzzle index.

        Scans images/videos/metadata for files named puzzle_<N>.<ext> and
        returns max(N)+1. If none exist, returns 1.
        """
        pattern = re.compile(r"^puzzle_(\d+)$")
        max_index = 0

        for directory in [self.images_dir, self.videos_dir, self.metadata_dir]:
            for path in directory.glob("puzzle_*"):
                match = pattern.match(path.stem)
                if match:
                    max_index = max(max_index, int(match.group(1)))

        return max_index + 1
    
    def save_image(self, puzzle_id: str, image: Union[Image.Image, Path, str]) -> Path:
        """Save puzzle image.
        
        Args:
            puzzle_id: Unique puzzle identifier
            image: PIL Image object or path to existing image file
            
        Returns:
            Path to saved image file
        """
        safe_id = self._sanitize_id(puzzle_id)
        output_path = self.images_dir / f"{safe_id}.png"
        
        if isinstance(image, Image.Image):
            # Save PIL Image
            image.save(output_path, "PNG")
        else:
            # Copy existing file
            source_path = Path(image)
            if not source_path.exists():
                raise FileNotFoundError(f"Image file not found: {source_path}")
            shutil.copy2(source_path, output_path)
        
        return output_path
    
    def save_video(self, puzzle_id: str, video_path: Union[Path, str]) -> Path:
        """Save puzzle video.
        
        Args:
            puzzle_id: Unique puzzle identifier
            video_path: Path to video file to save/move
            
        Returns:
            Path to saved video file
        """
        safe_id = self._sanitize_id(puzzle_id)
        source_path = Path(video_path)
        output_path = self.videos_dir / f"{safe_id}.mp4"
        
        if not source_path.exists():
            raise FileNotFoundError(f"Video file not found: {source_path}")
        
        # Copy video to output directory
        shutil.copy2(source_path, output_path)
        
        return output_path
    
    def save_metadata(
        self,
        puzzle_id: str,
        puzzle: Puzzle,
        extra: Optional[dict] = None
    ) -> Path:
        """Save puzzle metadata as JSON.
        
        Args:
            puzzle_id: Unique puzzle identifier
            puzzle: Puzzle object to save
            extra: Optional additional metadata fields (e.g., asset paths, timestamps)
            
        Returns:
            Path to saved metadata file
        """
        safe_id = self._sanitize_id(puzzle_id)
        output_path = self.metadata_dir / f"{safe_id}.json"
        
        # Build metadata dictionary
        metadata = {
            "puzzle": puzzle.to_dict(),
            "created_at": datetime.now().isoformat(),
            "puzzle_id": puzzle_id,
        }
        
        # Add extra fields
        if extra:
            metadata.update(extra)
        
        # Write JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def update_metadata(self, puzzle_id: str, updates: dict) -> Path:
        """Update existing metadata file with new fields.
        
        Args:
            puzzle_id: Unique puzzle identifier
            updates: Dictionary of fields to update
            
        Returns:
            Path to updated metadata file
        """
        safe_id = self._sanitize_id(puzzle_id)
        metadata_path = self.metadata_dir / f"{safe_id}.json"
        
        # Load existing metadata
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {"puzzle_id": puzzle_id}
        
        # Update with new fields
        metadata.update(updates)
        metadata["updated_at"] = datetime.now().isoformat()
        
        # Write back
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return metadata_path
    
    def get_metadata(self, puzzle_id: str) -> Optional[dict]:
        """Load metadata for a puzzle.
        
        Args:
            puzzle_id: Unique puzzle identifier
            
        Returns:
            Metadata dictionary or None if not found
        """
        safe_id = self._sanitize_id(puzzle_id)
        metadata_path = self.metadata_dir / f"{safe_id}.json"
        
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_image_path(self, puzzle_id: str) -> Path:
        """Get path to puzzle image.
        
        Args:
            puzzle_id: Unique puzzle identifier
            
        Returns:
            Path to image file
        """
        safe_id = self._sanitize_id(puzzle_id)
        return self.images_dir / f"{safe_id}.png"
    
    def get_video_path(self, puzzle_id: str) -> Path:
        """Get path to puzzle video.
        
        Args:
            puzzle_id: Unique puzzle identifier
            
        Returns:
            Path to video file
        """
        safe_id = self._sanitize_id(puzzle_id)
        return self.videos_dir / f"{safe_id}.mp4"
    
    def list_all_metadata(self) -> list:
        """List all metadata files.
        
        Returns:
            List of metadata dictionaries
        """
        metadata_files = sorted(self.metadata_dir.glob("*.json"))
        results = []
        
        for meta_file in metadata_files:
            with open(meta_file, "r", encoding="utf-8") as f:
                results.append(json.load(f))
        
        return results
