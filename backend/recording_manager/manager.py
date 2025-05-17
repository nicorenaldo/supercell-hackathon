import time
import uuid
import logging
from typing import Dict, Any, Optional

from pydantic import BaseModel

from .video_recorder import VideoRecorder


logger = logging.getLogger(__name__)


class RecordingResult(BaseModel):
    """Model for recording results"""

    recording_id: str
    video_file: Optional[str] = None


class RecordingStatus(BaseModel):
    """Response model for recording status"""

    status: str
    recording_id: Optional[str] = None


class RecordingManager:
    """
    Manages audio and video recording sessions.
    Coordinates the recording, processing, and cleanup of audio and video data.
    Processes audio to extract speech text and video to extract emotion data.
    """

    def __init__(self):
        """Initialize the recording manager with audio and video recorders"""
        self.video_recorder = VideoRecorder()

        self.current_recording_id: Optional[str] = None
        self.is_recording: bool = False

        logger.info("Recording manager initialized")

    def start_recording(self) -> Dict[str, Any]:
        """
        Start a new recording session for both audio and video

        Returns:
            Dictionary with recording session information
        """
        if self.is_recording:
            logger.warning("Already recording, stopping current session first")
            self.stop_recording()

        self.current_recording_id = str(uuid.uuid4())
        self.video_recorder.start_recording(self.current_recording_id)
        self.is_recording = True

        return RecordingStatus(
            status="recording",
            recording_id=self.current_recording_id,
        )

    def stop_recording(self) -> RecordingResult:
        """
        Stop the current recording session and process the results

        Returns:
            RecordingResult object with processed data
        """
        if not self.is_recording:
            logger.warning("Not currently recording")
            return RecordingResult(recording_id="none")

        recording_id = self.current_recording_id
        video_result = self.video_recorder.stop_recording()
        self.is_recording = False

        result = RecordingResult(
            recording_id=recording_id,
            video_file=video_result.get("filename"),
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
