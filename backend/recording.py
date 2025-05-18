import uuid
import logging
import os
import shutil
from typing import Dict, Any, Optional

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class RecordingResult(BaseModel):
    """Model for recording results"""

    game_id: str
    recording_id: str
    file_path: Optional[str] = None


class RecordingStatus(BaseModel):
    """Response model for recording status"""

    status: str
    recording_id: Optional[str] = None


class RecordingManager:
    """
    Manages video recording sessions.
    Coordinates the recording, processing, and cleanup of video data.
    """

    def __init__(self):
        """Initialize the recording manager with video recorder"""
        self.recording_counters: Dict[str, int] = {}
        self.current_recording_ids: Dict[str, str] = {}
        self.output_dir = "recordings"

        logger.info("Recording manager initialized")

    def _get_recording_dir(self, game_id: str, recording_id: str) -> str:
        """
        Get the directory path for a specific recording

        Args:
            recording_id: Unique identifier for the recording

        Returns:
            Path to the recording directory
        """
        if not game_id:
            raise ValueError("Game ID is not set")
        if not recording_id:
            raise ValueError("Recording ID is not set")

        recording_dir = os.path.join(self.output_dir, game_id, recording_id)
        os.makedirs(recording_dir, exist_ok=True)
        os.makedirs(os.path.join(recording_dir, "frames"), exist_ok=True)
        return recording_dir

    def handle_uploaded_file(self, game_id: str, file_path: str) -> RecordingResult:
        """
        Handle an uploaded video file instead of recording

        Args:
            game_id: ID of the game session
            file_path: Path to the uploaded video file

        Returns:
            RecordingResult object with video file info
        """
        if game_id not in self.recording_counters:
            self.recording_counters[game_id] = 0

        self.recording_counters[game_id] += 1

        recording_id = f"recording_{game_id}_{self.recording_counters[game_id]}"
        self.current_recording_ids[game_id] = recording_id

        recording_dir = self._get_recording_dir(game_id, recording_id)

        target_path = os.path.join(recording_dir, f"video.webm")
        try:
            shutil.copy2(file_path, target_path)
            logger.info(f"Copied uploaded file to {target_path}")

            return RecordingResult(
                game_id=game_id,
                recording_id=recording_id,
                file_path=target_path,
            )
        except Exception as e:
            logger.error(f"Error handling uploaded file: {str(e)}")
            return RecordingResult(
                game_id=game_id,
                recording_id=recording_id,
                file_path=file_path,
            )

    def cleanup(self, game_id: Optional[str] = None):
        """
        Clean up recording resources for a specific game or all games

        Args:
            game_id: Optional ID of game to clean up. If None, cleans up all games.
        """
        try:
            if game_id:
                # Clean up resources for a specific game
                if game_id in self.recording_counters:
                    del self.recording_counters[game_id]

                if game_id in self.current_recording_ids:
                    del self.current_recording_ids[game_id]

                # Remove recording directory if it exists
                game_dir = os.path.join(self.output_dir, game_id)
                if os.path.exists(game_dir):
                    shutil.rmtree(game_dir)

                logger.info(f"Cleaned up recording resources for game {game_id}")
            else:
                # Clean up all resources
                self.recording_counters.clear()
                self.current_recording_ids.clear()

                # Optionally remove all recording directories
                if os.path.exists(self.output_dir):
                    for game_dir in os.listdir(self.output_dir):
                        full_path = os.path.join(self.output_dir, game_dir)
                        if os.path.isdir(full_path):
                            shutil.rmtree(full_path)

                logger.info("Cleaned up all recording resources")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
