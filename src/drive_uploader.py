"""Upload generated videos to Google Drive (e.g. shared folder for TikTok posting)."""

import logging
from pathlib import Path
from typing import Optional

from . import config

logger = logging.getLogger(__name__)

# Scope: drive (read/write) so we can upload to any folder the user owns or has write access to
SCOPES = ["https://www.googleapis.com/auth/drive"]


def _optional_import():
    """Import Google API libraries; return (service_builder, creds_builder) or (None, None) if not installed."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        return (build, Credentials, InstalledAppFlow, Request, MediaFileUpload)
    except ImportError:
        return None


def get_drive_service(credentials_path: Optional[Path] = None, token_path: Optional[Path] = None):
    """
    Build a Drive API v3 service using OAuth 2.0.
    On first run, opens browser for login and saves token to token_path.
    """
    impl = _optional_import()
    if impl is None:
        raise ImportError(
            "Google Drive upload requires: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )
    build_api, Credentials, InstalledAppFlow, Request, _ = impl

    creds_path = credentials_path or config.WORKSPACE_ROOT / "credentials.json"
    tok_path = token_path or config.WORKSPACE_ROOT / "token.json"

    creds = None
    if tok_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(tok_path), SCOPES)
        except Exception as e:
            logger.warning(f"Could not load token from {tok_path}: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {creds_path}. "
                    "Download OAuth 2.0 credentials (Desktop app) from Google Cloud Console, "
                    "save as credentials.json in the project root."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        tok_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tok_path, "w") as f:
            f.write(creds.to_json())

    return build_api("drive", "v3", credentials=creds)


def upload_file_to_drive(
    local_path: Path,
    folder_id: str,
    credentials_path: Optional[Path] = None,
    token_path: Optional[Path] = None,
) -> Optional[str]:
    """
    Upload a file to a Google Drive folder. Returns the Drive file ID, or None on failure.
    """
    local_path = Path(local_path)
    if not local_path.exists():
        logger.error(f"File not found: {local_path}")
        return None

    try:
        service = get_drive_service(credentials_path=credentials_path, token_path=token_path)
    except Exception as e:
        logger.error(f"Drive auth failed: {e}")
        return None

    name = local_path.name
    mime = "video/mp4" if local_path.suffix.lower() == ".mp4" else "application/octet-stream"

    try:
        media = MediaFileUpload(str(local_path), mimetype=mime, resumable=True)
        file_metadata = {"name": name, "parents": [folder_id]}
        f = service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
        file_id = f.get("id")
        logger.info(f"Uploaded to Drive: {name} (id={file_id})")
        return file_id
    except Exception as e:
        logger.error(f"Drive upload failed for {name}: {e}")
        return None


class DriveUploader:
    """Uploads pipeline outputs to a Google Drive folder (e.g. shared with TikTok account holder)."""

    def __init__(
        self,
        folder_id: Optional[str] = None,
        credentials_path: Optional[Path] = None,
        token_path: Optional[Path] = None,
    ):
        self.folder_id = (folder_id or config.GOOGLE_DRIVE_FOLDER_ID or "").strip()
        creds_env = (config.GOOGLE_DRIVE_CREDENTIALS_PATH or "").strip()
        self.credentials_path = Path(credentials_path) if credentials_path else (
            Path(creds_env) if creds_env else config.WORKSPACE_ROOT / "credentials.json"
        )
        token_env = (config.GOOGLE_DRIVE_TOKEN_PATH or "").strip()
        self.token_path = Path(token_path) if token_path else (
            Path(token_env) if token_env else config.WORKSPACE_ROOT / "token.json"
        )

    def available(self) -> bool:
        """Return True if Drive upload is configured and dependencies are installed."""
        if not self.folder_id or not self.folder_id.strip():
            return False
        return _optional_import() is not None

    def upload_video(self, video_path: Path) -> Optional[str]:
        """Upload a single video file to the configured Drive folder. Returns Drive file ID or None."""
        return upload_file_to_drive(
            video_path,
            self.folder_id,
            credentials_path=self.credentials_path,
            token_path=self.token_path,
        )
