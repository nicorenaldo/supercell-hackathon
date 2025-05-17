import uuid
import logging
from typing import Dict, Any, Optional

from pydantic import BaseModel

from .video_recorder import VideoRecorder


logger = logging.getLogger(__name__)


class RecordingResult(BaseModel):
    """Model for recording results"""

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
        self.video_recorder = VideoRecorder()

        self.current_recording_id: Optional[str] = None
        self.is_recording: bool = False
        self.recording_counter: Dict[str, int] = {}

        logger.info("Recording manager initialized")

    def start_recording(self, game_id: str) -> Dict[str, Any]:
        """
        Start a new recording session for video

        Returns:
            Dictionary with recording session information
        """
        if self.is_recording:
            logger.warning("Already recording, stopping current session first")
            self.stop_recording()

        if game_id not in self.recording_counter:
            self.recording_counter[game_id] = 0

        self.recording_counter[game_id] += 1

        self.current_recording_id = f"recording_{self.recording_counter[game_id]}"
        self.video_recorder.start_recording(game_id, self.current_recording_id)
        self.is_recording = True

        return RecordingStatus(
            status="recording",
            recording_id=self.current_recording_id,
        )

    def stop_recording(self) -> RecordingResult:
        """
        Stop the current recording session

        Returns:
            RecordingResult object with video file
        """
        if not self.is_recording:
            logger.warning("Not currently recording")
            return RecordingResult(recording_id="none", file_path=None)

        recording_id = self.current_recording_id
        video_result = self.video_recorder.stop_recording()
        self.is_recording = False

        result = RecordingResult(
            recording_id=recording_id,
            file_path=video_result.get("filename"),
        )

        return result

    def cleanup(self):
        """
        Clean up resources
        """
        if self.is_recording:
            self.stop_recording()
        self.video_recorder.cleanup()
        logger.info("Recording manager cleaned up")
