"""
Google Drive Ingestion Module

This module provides comprehensive Google Drive ingestion capabilities for the
VeritasReason framework, enabling data extraction from Google Drive files and folders.

Key Features:
    - Folder ingestion
    - File ingestion
    - Drive export
    - File type detection
    - OAuth authentication

Main Classes:
    - GDriveIngestor: Main Google Drive ingestion class
    - GDriveData: Data representation for Google Drive ingestion

Example Usage:
    >>> from veritasreason.ingest import GDriveIngestor
    >>> ingestor = GDriveIngestor(credentials_path="credentials.json")
    >>> data = ingestor.ingest_folder("folder_id")
    >>> file_data = ingestor.ingest_file("file_id")
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload
    import io
except (ImportError, OSError):
    Credentials = None
    InstalledAppFlow = None
    Request = None
    build = None
    HttpError = None
    MediaIoBaseDownload = None
    io = None


@dataclass
class GDriveData:
    """Google Drive data representation."""

    files: List[Dict[str, Any]]
    file_count: int
    folder_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=datetime.now)


class GDriveIngestor:
    """
    Google Drive ingestion handler.

    This class provides comprehensive Google Drive ingestion capabilities,
    connecting to Google Drive, listing files, and downloading content.

    Features:
        - Folder ingestion
        - File ingestion
        - Drive export
        - File type detection
        - OAuth authentication

    Example Usage:
        >>> ingestor = GDriveIngestor(credentials_path="credentials.json")
        >>> data = ingestor.ingest_folder("folder_id")
    """

    # Google Drive API scopes
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize Google Drive ingestor.

        Args:
            config: Optional Google Drive ingestion configuration dictionary
            **kwargs: Additional configuration parameters (merged into config)
        """
        if build is None:
            raise ImportError(
                "google-api-python-client and google-auth-oauthlib are required for GDriveIngestor. "
                "Install with: pip install google-api-python-client google-auth-oauthlib"
            )

        self.logger = get_logger("gdrive_ingestor")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize Google Drive service
        self.service = None
        self.credentials_path = self.config.get("credentials_path")
        self.token_path = self.config.get("token_path", "token.json")

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()

        self.logger.debug("Google Drive ingestor initialized")

    def _authenticate(self):
        """
        Authenticate with Google Drive API.

        Raises:
            ProcessingError: If authentication fails
        """
        if self.service:
            return

        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(
                    self.token_path, self.SCOPES
                )
            except Exception as e:
                self.logger.warning(f"Failed to load token: {e}")

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path:
                    raise ValidationError(
                        "credentials_path is required for Google Drive authentication. "
                        "Provide path to OAuth2 credentials JSON file."
                    )

                if not os.path.exists(self.credentials_path):
                    raise ValidationError(
                        f"Credentials file not found: {self.credentials_path}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())

        # Build service
        self.service = build("drive", "v3", credentials=creds)
        self.logger.info("Authenticated with Google Drive")

    def ingest_folder(
        self,
        folder_id: str,
        include_subfolders: bool = False,
        file_types: Optional[List[str]] = None,
        **options,
    ) -> GDriveData:
        """
        Ingest data from Google Drive folder.

        This method lists all files in a Google Drive folder and retrieves
        their metadata.

        Args:
            folder_id: Google Drive folder ID
            include_subfolders: Whether to include files from subfolders
            file_types: Optional list of file MIME types to filter
            **options: Additional processing options

        Returns:
            GDriveData: Ingested data object containing:
                - files: List of file metadata dictionaries
                - file_count: Number of files
                - folder_id: Folder ID
                - metadata: Additional metadata

        Raises:
            ProcessingError: If ingestion fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=folder_id,
            module="ingest",
            submodule="GDriveIngestor",
            message=f"Ingesting folder: {folder_id}",
        )

        try:
            # Authenticate
            self._authenticate()

            # Query files in folder
            query = f"'{folder_id}' in parents and trashed=false"
            if file_types:
                mime_types = " or ".join([f"mimeType='{ft}'" for ft in file_types])
                query += f" and ({mime_types})"

            self.progress_tracker.update_tracking(
                tracking_id, message="Listing files in folder..."
            )

            files = []
            page_token = None

            while True:
                results = (
                    self.service.files()
                    .list(
                        q=query,
                        pageSize=1000,
                        fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, createdTime)",
                        pageToken=page_token,
                    )
                    .execute()
                )

                items = results.get("files", [])
                files.extend(items)

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            # Handle subfolders if requested
            if include_subfolders:
                # Get all subfolders
                subfolder_query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                subfolders = []
                page_token = None

                while True:
                    results = (
                        self.service.files()
                        .list(
                            q=subfolder_query,
                            pageSize=1000,
                            fields="nextPageToken, files(id, name)",
                            pageToken=page_token,
                        )
                        .execute()
                    )

                    items = results.get("files", [])
                    subfolders.extend(items)

                    page_token = results.get("nextPageToken")
                    if not page_token:
                        break

                # Recursively ingest subfolders
                for subfolder in subfolders:
                    try:
                        subfolder_data = self.ingest_folder(
                            subfolder["id"],
                            include_subfolders=True,
                            file_types=file_types,
                            **options,
                        )
                        files.extend(subfolder_data.files)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to ingest subfolder {subfolder['name']}: {e}"
                        )

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Ingested {len(files)} files",
            )

            self.logger.info(f"Folder ingestion completed: {len(files)} file(s)")

            return GDriveData(
                files=files,
                file_count=len(files),
                folder_id=folder_id,
                metadata={"include_subfolders": include_subfolders},
            )

        except HttpError as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest folder: {e}")
            raise ProcessingError(f"Failed to ingest folder: {e}") from e
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest folder: {e}")
            raise ProcessingError(f"Failed to ingest folder: {e}") from e

    def ingest_file(
        self,
        file_id: str,
        download: bool = False,
        **options,
    ) -> Dict[str, Any]:
        """
        Ingest data from Google Drive file.

        This method retrieves metadata and optionally downloads content
        from a Google Drive file.

        Args:
            file_id: Google Drive file ID
            download: Whether to download file content
            **options: Additional processing options

        Returns:
            Dictionary containing file metadata and optionally content

        Raises:
            ProcessingError: If ingestion fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=file_id,
            module="ingest",
            submodule="GDriveIngestor",
            message=f"Ingesting file: {file_id}",
        )

        try:
            # Authenticate
            self._authenticate()

            # Get file metadata
            file_metadata = (
                self.service.files().get(fileId=file_id, fields="*").execute()
            )

            result = {"metadata": file_metadata}

            # Download content if requested
            if download:
                self.progress_tracker.update_tracking(
                    tracking_id, message="Downloading file content..."
                )

                # Check if file is Google Workspace file (needs export)
                mime_type = file_metadata.get("mimeType", "")
                if mime_type.startswith("application/vnd.google-apps"):
                    # Export Google Workspace file
                    export_mime_type = options.get(
                        "export_mime_type", "application/pdf"
                    )
                    request = self.service.files().export_media(
                        fileId=file_id, mimeType=export_mime_type
                    )
                else:
                    # Download regular file
                    request = self.service.files().get_media(fileId=file_id)

                # Download to bytes
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

                result["content"] = file_content.getvalue()

            self.progress_tracker.stop_tracking(
                tracking_id, status="completed", message="File ingested"
            )

            self.logger.info(f"File ingestion completed: {file_id}")

            return result

        except HttpError as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest file: {e}")
            raise ProcessingError(f"Failed to ingest file: {e}") from e
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest file: {e}")
            raise ProcessingError(f"Failed to ingest file: {e}") from e

    def export_drive(
        self,
        folder_id: Optional[str] = None,
        **options,
    ) -> GDriveData:
        """
        Export entire Google Drive or a folder.

        This method exports all files from a Google Drive folder or the entire drive.

        Args:
            folder_id: Optional folder ID (exports entire drive if not provided)
            **options: Additional export options

        Returns:
            GDriveData: Exported data object

        Raises:
            ProcessingError: If export fails
        """
        if folder_id:
            return self.ingest_folder(folder_id, include_subfolders=True, **options)
        else:
            # Export entire drive (root folder)
            return self.ingest_folder("root", include_subfolders=True, **options)

