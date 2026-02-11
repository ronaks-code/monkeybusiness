"""TikTok Content Posting API integration."""

import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict
from urllib import request, parse
from urllib.error import HTTPError, URLError

from . import config

logger = logging.getLogger(__name__)


class TikTokPoster:
    """Posts videos to TikTok using the Content Posting API."""
    
    def __init__(self, access_token: Optional[str] = None):
        """Initialize TikTok poster.
        
        Args:
            access_token: TikTok user access token (defaults to config.TIKTOK_ACCESS_TOKEN)
        """
        self.access_token = access_token or config.TIKTOK_ACCESS_TOKEN
        self.base_url = config.TIKTOK_API_BASE_URL
        self.chunk_size = config.TIKTOK_CHUNK_SIZE
        self.rate_limit_window = config.TIKTOK_RATE_LIMIT_WINDOW
        self.rate_limit_per_minute = config.TIKTOK_RATE_LIMIT_PER_MINUTE
        
        # Track API calls for rate limiting
        self.last_init_calls = []
        
        if not self.access_token:
            raise ValueError("TikTok access token is required. Set TIKTOK_ACCESS_TOKEN in .env")
    
    def _make_request(
        self,
        url: str,
        method: str = "POST",
        data: Optional[dict] = None,
        headers: Optional[dict] = None
    ) -> dict:
        """Make HTTP request to TikTok API.
        
        Args:
            url: Full URL to request
            method: HTTP method
            data: Optional JSON data
            headers: Optional additional headers
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            RuntimeError: If request fails
        """
        req_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        if headers:
            req_headers.update(headers)
        
        req_data = None
        if data:
            req_data = json.dumps(data).encode('utf-8')
        
        req = request.Request(url, data=req_data, headers=req_headers, method=method)
        
        try:
            with request.urlopen(req) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                
                # Check for API errors
                error = response_data.get("error", {})
                error_code = error.get("code", "ok")
                
                if error_code != "ok":
                    raise RuntimeError(f"TikTok API error: {error_code} - {error.get('message', 'Unknown error')}")
                
                return response_data
                
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"HTTP {e.code}: {error_body}")
            
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                error_code = error_data.get("error", {}).get("code", "unknown")
                raise RuntimeError(f"TikTok API error ({e.code}): {error_code} - {error_msg}")
            except json.JSONDecodeError:
                raise RuntimeError(f"HTTP {e.code}: {error_body}")
                
        except URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")
    
    def _rate_limit_check(self):
        """Check and enforce rate limiting for video init endpoint.
        
        TikTok allows 6 requests per minute per user access token for /video/init/.
        """
        now = time.time()
        
        # Remove calls older than rate limit window
        self.last_init_calls = [
            t for t in self.last_init_calls
            if now - t < self.rate_limit_window
        ]
        
        # Check if we've hit the limit
        if len(self.last_init_calls) >= self.rate_limit_per_minute:
            # Calculate wait time
            oldest_call = self.last_init_calls[0]
            wait_time = self.rate_limit_window - (now - oldest_call)
            
            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached ({self.rate_limit_per_minute} calls per "
                    f"{self.rate_limit_window}s). Waiting {wait_time:.1f} seconds..."
                )
                time.sleep(wait_time + 1)  # Add 1 second buffer
                
                # Clear old calls after waiting
                now = time.time()
                self.last_init_calls = [
                    t for t in self.last_init_calls
                    if now - t < self.rate_limit_window
                ]
        
        # Record this call
        self.last_init_calls.append(now)
    
    def query_creator_info(self) -> dict:
        """Query creator information before posting.
        
        Returns:
            Dictionary with creator info including privacy_level_options
        """
        url = f"{self.base_url}/v2/post/publish/creator_info/query/"
        
        logger.info("Querying creator info...")
        response = self._make_request(url, method="POST")
        
        data = response.get("data", {})
        logger.info(f"Creator: {data.get('creator_username', 'unknown')}")
        logger.info(f"Privacy options: {data.get('privacy_level_options', [])}")
        
        return data
    
    def post_video(
        self,
        video_path: Path,
        title: Optional[str] = None,
        privacy_level: Optional[str] = None,
        post_info_overrides: Optional[dict] = None
    ) -> dict:
        """Post a video to TikTok.
        
        Args:
            video_path: Path to video file (must be MP4 + H.264)
            title: Video caption (max 2200 UTF-16 runes)
            privacy_level: Privacy level (must be in creator's options)
            post_info_overrides: Optional additional post_info fields
            
        Returns:
            Dictionary with publish_id and status
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Get video size
        video_size = video_path.stat().st_size
        
        # Prepare post_info
        post_info = {
            "privacy_level": privacy_level or config.TIKTOK_PRIVACY_LEVEL,
        }
        
        if title:
            # Truncate title to max length if needed
            if len(title) > config.MAX_CAPTION_LENGTH:
                title = title[:config.MAX_CAPTION_LENGTH]
            post_info["title"] = title
        
        if post_info_overrides:
            post_info.update(post_info_overrides)
        
        # Calculate chunking
        total_chunks = (video_size + self.chunk_size - 1) // self.chunk_size
        
        # Prepare source_info for FILE_UPLOAD
        source_info = {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": self.chunk_size,
            "total_chunk_count": total_chunks
        }
        
        # Step 1: Initialize post (with rate limiting)
        self._rate_limit_check()
        
        init_url = f"{self.base_url}/v2/post/publish/video/init/"
        init_data = {
            "post_info": post_info,
            "source_info": source_info
        }
        
        logger.info(f"Initializing video post (size: {video_size} bytes, chunks: {total_chunks})...")
        init_response = self._make_request(init_url, data=init_data)
        
        publish_id = init_response["data"]["publish_id"]
        upload_url = init_response["data"]["upload_url"]
        
        logger.info(f"Publish ID: {publish_id}")
        logger.info(f"Upload URL obtained")
        
        # Step 2: Upload video file
        logger.info("Uploading video...")
        self._upload_video(video_path, upload_url, video_size)
        
        logger.info("Video uploaded successfully")
        
        # Step 3: Check status (optional, can be polled later)
        status = self.get_post_status(publish_id)
        
        return {
            "publish_id": publish_id,
            "status": status.get("status", "unknown"),
            "upload_url": upload_url
        }
    
    def _upload_video(self, video_path: Path, upload_url: str, video_size: int):
        """Upload video file to TikTok servers.
        
        Args:
            video_path: Path to video file
            upload_url: Upload URL from init response
            video_size: Size of video file in bytes
        """
        with open(video_path, 'rb') as video_file:
            video_data = video_file.read()
        
        # For simplicity, upload as single chunk
        # (multi-chunk upload would split the file and send multiple PUT requests)
        headers = {
            "Content-Type": "video/mp4",
            "Content-Length": str(video_size),
            "Content-Range": f"bytes 0-{video_size-1}/{video_size}"
        }
        
        req = request.Request(upload_url, data=video_data, headers=headers, method="PUT")
        
        try:
            with request.urlopen(req, timeout=config.TIKTOK_UPLOAD_TIMEOUT) as response:
                if response.status not in [200, 201]:
                    raise RuntimeError(f"Upload failed with status {response.status}")
                logger.debug(f"Upload response: {response.status}")
        except Exception as e:
            raise RuntimeError(f"Failed to upload video: {e}")
    
    def get_post_status(self, publish_id: str) -> dict:
        """Check the status of a post.
        
        Args:
            publish_id: Publish ID from post_video
            
        Returns:
            Dictionary with status information
        """
        status_url = f"{self.base_url}/v2/post/publish/status/fetch/"
        status_data = {"publish_id": publish_id}
        
        logger.debug(f"Checking status for {publish_id}...")
        response = self._make_request(status_url, data=status_data)
        
        status_info = response.get("data", {})
        logger.debug(f"Status: {status_info.get('status', 'unknown')}")
        
        return status_info
