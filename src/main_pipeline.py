"""Main pipeline orchestration for puzzle video generation."""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from . import config
from .models import Puzzle
from .puzzle_generator import PuzzleGenerator
from .puzzle_renderer import PuzzleRenderer
from .video_builder import VideoBuilder
from .asset_manager import AssetManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineStats:
    """Track pipeline execution statistics."""
    
    def __init__(self):
        self.generated = 0
        self.rendered = 0
        self.videos_created = 0
        self.failed = 0
        self.posted = 0
        self.post_failed = 0
        self.drive_uploaded = 0
        self.drive_failed = 0
    
    def __str__(self):
        lines = [
            f"  Puzzles generated: {self.generated}",
            f"  Images rendered: {self.rendered}",
            f"  Videos created: {self.videos_created}",
            f"  Failed: {self.failed}",
            f"  Posted to TikTok: {self.posted}",
            f"  Post failures: {self.post_failed}",
        ]
        if self.drive_uploaded or self.drive_failed:
            lines.extend([f"  Uploaded to Drive: {self.drive_uploaded}", f"  Drive upload failures: {self.drive_failed}"])
        return "Pipeline Summary:\n" + "\n".join(lines)


def run_pipeline(
    count: int,
    output_dir: Optional[Path] = None,
    skip_video: bool = False,
    post_to_tiktok: bool = False,
    upload_to_drive: bool = False,
    start_difficulty: Optional[int] = None
) -> PipelineStats:
    """Run the complete puzzle video production pipeline.
    
    Args:
        count: Number of puzzles to generate
        output_dir: Optional custom output directory
        skip_video: If True, only generate images
        post_to_tiktok: If True, post videos to TikTok
        upload_to_drive: If True, upload each video to Google Drive (GOOGLE_DRIVE_FOLDER_ID)
        start_difficulty: Starting difficulty level
        
    Returns:
        PipelineStats object with execution statistics
    """
    stats = PipelineStats()
    
    # Initialize components
    logger.info("Initializing pipeline components...")
    
    asset_manager = AssetManager(output_dir)
    generator = PuzzleGenerator()
    renderer = PuzzleRenderer()
    start_index = asset_manager.get_next_puzzle_index()
    logger.info(f"Starting puzzle IDs at puzzle_{start_index:03d}")
    
    if not skip_video:
        video_builder = VideoBuilder()
    
    # TikTok poster will be initialized if needed
    tiktok_poster = None
    if post_to_tiktok:
        from .tiktok_poster import TikTokPoster
        if not config.TIKTOK_ACCESS_TOKEN:
            logger.error("TIKTOK_ACCESS_TOKEN not set. Cannot post to TikTok.")
            logger.error("Please set TIKTOK_ACCESS_TOKEN in your .env file.")
            sys.exit(1)
        tiktok_poster = TikTokPoster()
        logger.info("TikTok poster initialized")
    
    # Google Drive uploader (optional; uploads to shared folder for TikTok account holder)
    drive_uploader = None
    if upload_to_drive:
        from .drive_uploader import DriveUploader
        drive_uploader = DriveUploader()
        if not drive_uploader.available():
            logger.error("Google Drive upload requested but GOOGLE_DRIVE_FOLDER_ID is not set or Drive deps missing.")
            logger.error("Set GOOGLE_DRIVE_FOLDER_ID in .env and add credentials.json (see README).")
            sys.exit(1)
        logger.info("Drive uploader initialized (folder ID set)")
    
    # Generate puzzles
    logger.info(f"Generating {count} puzzles...")
    puzzles = generator.generate_puzzles(
        count,
        start_difficulty=start_difficulty,
        start_index=start_index
    )
    stats.generated = len(puzzles)
    
    if not puzzles:
        logger.error("No puzzles were successfully generated")
        return stats
    
    logger.info(f"Successfully generated {len(puzzles)} puzzles")
    
    # Process each puzzle
    for idx, puzzle in enumerate(puzzles, 1):
        logger.info(f"\n[{idx}/{len(puzzles)}] Processing puzzle: {puzzle.id}")
        
        try:
            # Render image
            logger.info(f"  Rendering image...")
            image = renderer.render(puzzle)
            image_path = asset_manager.save_image(puzzle.id, image)
            stats.rendered += 1
            logger.info(f"  Image saved: {image_path}")
            
            # Save initial metadata
            metadata_extra = {
                "image_path": str(image_path),
                "difficulty": puzzle.difficulty
            }
            
            if skip_video:
                # Save metadata and continue
                asset_manager.save_metadata(puzzle.id, puzzle, metadata_extra)
                logger.info(f"  Metadata saved (video skipped)")
                continue
            
            # Build video
            logger.info(f"  Building video...")
            final_video_path = asset_manager.get_video_path(puzzle.id)
            video_path = video_builder.build_video(
                puzzle_id=puzzle.id,
                puzzle_image_path=image_path,
                answer=puzzle.correct_answer,
                explanation=puzzle.explanation,
                question_text=puzzle.question_text,
                output_path=final_video_path
            )

            # Build wrote directly to output/videos; keep this assignment explicit.
            final_video_path = Path(video_path)
            stats.videos_created += 1
            logger.info(f"  Video saved: {final_video_path}")
            
            # Update metadata
            metadata_extra["video_path"] = str(final_video_path)
            metadata_extra["video_duration"] = (
                config.SLIDE_INTRO_DURATION +
                config.SLIDE_PUZZLE_DURATION +
                config.SLIDE_ANSWER_DURATION +
                config.SLIDE_EXPLANATION_DURATION
            )
            asset_manager.save_metadata(puzzle.id, puzzle, metadata_extra)
            
            # Post to TikTok if requested
            if post_to_tiktok and tiktok_poster:
                logger.info(f"  Posting to TikTok...")
                try:
                    # Generate caption from question text
                    caption = (puzzle.question_text or "")[:config.MAX_CAPTION_LENGTH]
                    
                    result = tiktok_poster.post_video(
                        video_path=final_video_path,
                        title=caption,
                        privacy_level=config.TIKTOK_PRIVACY_LEVEL
                    )
                    
                    # Update metadata with TikTok info
                    asset_manager.update_metadata(puzzle.id, {
                        "tiktok_publish_id": result.get("publish_id"),
                        "tiktok_status": result.get("status", "pending"),
                        "tiktok_title": caption
                    })
                    
                    stats.posted += 1
                    logger.info(f"  Posted to TikTok: {result.get('publish_id')}")
                    
                except Exception as e:
                    logger.error(f"  Failed to post to TikTok: {e}")
                    stats.post_failed += 1
            
            # Upload to Google Drive if requested (e.g. shared folder for TikTok account holder)
            if upload_to_drive and drive_uploader:
                logger.info(f"  Uploading to Google Drive...")
                try:
                    fid = drive_uploader.upload_video(final_video_path)
                    if fid:
                        stats.drive_uploaded += 1
                        asset_manager.update_metadata(puzzle.id, {"drive_file_id": fid})
                    else:
                        stats.drive_failed += 1
                except Exception as e:
                    logger.error(f"  Failed to upload to Drive: {e}")
                    stats.drive_failed += 1
            
        except Exception as e:
            logger.error(f"  Failed to process puzzle {puzzle.id}: {e}")
            stats.failed += 1
            continue
    
    return stats


def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(
        description="Automated puzzle video production pipeline for TikTok"
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of puzzles to generate (default: 1)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Custom output directory (default: ./output)"
    )
    
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Only generate puzzle images, skip video creation"
    )
    
    parser.add_argument(
        "--post-to-tiktok",
        action="store_true",
        help="Post generated videos to TikTok via Content Posting API"
    )
    
    parser.add_argument(
        "--upload-to-drive",
        action="store_true",
        help="Upload each video to Google Drive (set GOOGLE_DRIVE_FOLDER_ID in .env; share folder with TikTok account holder)"
    )
    
    parser.add_argument(
        "--difficulty",
        type=int,
        choices=range(1, 11),
        help="Starting difficulty level (1-10, cycles through all levels)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Validate configuration
    try:
        config.validate_config()
        config.ensure_directories()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Log configuration
    logger.info("Pipeline configuration:")
    for key, value in config.get_config_summary().items():
        logger.info(f"  {key}: {value}")
    
    # Run pipeline
    try:
        stats = run_pipeline(
            count=args.count,
            output_dir=args.output_dir,
            skip_video=args.skip_video,
            post_to_tiktok=args.post_to_tiktok,
            upload_to_drive=args.upload_to_drive,
            start_difficulty=args.difficulty
        )
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info(str(stats))
        logger.info("="*50)
        
        # Exit with appropriate code
        if stats.videos_created > 0 or (args.skip_video and stats.rendered > 0):
            sys.exit(0)
        else:
            logger.error("Pipeline failed to produce any output")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Pipeline failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
