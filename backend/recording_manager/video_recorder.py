import os
import time
import threading
import logging
import cv2
import numpy as np
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class VideoRecorder:
    """
    Records video from webcam when triggered by frontend.
    Uses OpenCV to capture frames and save as MP4 files.
    Also captures individual frames for emotion detection.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        output_dir: str = "recordings/video",
    ):
        """
        Initialize the video recorder with the given parameters.

        Args:
            width: Frame width
            height: Frame height
            fps: Frames per second
            output_dir: Directory to save recordings
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "frames"), exist_ok=True)

        # Video capture and recording variables
        self.cap = None
        self.writer = None
        self.is_recording = False
        self.recording_thread = None
        self.current_recording_id = None
        self.last_frame = None

        # Fourcc code for video codec
        self.fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        logger.info("Video recorder initialized")

    def _record_video(self):
        """
        Internal function to record video in a background thread
        """
        logger.info(f"Started recording video: {self.current_recording_id}")

        frame_count = 0
        start_time = time.time()

        while self.is_recording:
            ret, frame = self.cap.read()

            if not ret:
                logger.warning("Failed to capture frame")
                time.sleep(0.1)
                continue

            # Store the latest frame for emotion detection
            self.last_frame = frame.copy()

            # Write frame to video
            self.writer.write(frame)

            # Save frame for emotion detection at reduced frequency (every 15 frames = 0.5s at 30fps)
            if frame_count % 15 == 0:
                frame_filename = os.path.join(
                    self.output_dir, "frames", f"{self.current_recording_id}_{frame_count}.jpg"
                )
                cv2.imwrite(frame_filename, frame)

            frame_count += 1

            # Calculate time to sleep to maintain desired FPS
            elapsed = time.time() - start_time
            expected_frame_time = frame_count / self.fps
            sleep_time = max(0, expected_frame_time - elapsed)

            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info(f"Stopped recording video after {frame_count} frames")

    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get the latest captured frame for emotion detection

        Returns:
            The latest frame as numpy array or None if not recording
        """
        return self.last_frame

    def start_recording(self, recording_id: str) -> Dict[str, Any]:
        """
        Start recording video

        Args:
            recording_id: Unique identifier for the recording session

        Returns:
            Dictionary with status and recording info
        """
        if self.is_recording:
            logger.warning("Already recording video, stopping current recording first")
            self.stop_recording()

        try:
            # Initialize video capture
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            # Verify that video capture is working
            ret, _ = self.cap.read()
            if not ret:
                raise ValueError("Could not open webcam")

            # Initialize video writer
            filename = os.path.join(self.output_dir, f"{recording_id}.mp4")
            self.writer = cv2.VideoWriter(
                filename, self.fourcc, self.fps, (self.width, self.height)
            )

            # Set recording variables
            self.is_recording = True
            self.current_recording_id = recording_id

            # Start recording thread
            self.recording_thread = threading.Thread(target=self._record_video)
            self.recording_thread.daemon = True
            self.recording_thread.start()

            return {
                "status": "recording",
                "recording_id": recording_id,
                "filename": filename,
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.error(f"Error starting video recording: {str(e)}")
            self.is_recording = False
            return {"status": "error", "error": str(e), "timestamp": time.time()}

    def stop_recording(self) -> Dict[str, Any]:
        """
        Stop the current recording

        Returns:
            Dictionary with status and file info
        """
        if not self.is_recording:
            logger.warning("Not currently recording video")
            return {"status": "not_recording", "timestamp": time.time()}

        # Stop recording
        self.is_recording = False

        # Wait for recording thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2.0)

        recording_id = self.current_recording_id
        filename = os.path.join(self.output_dir, f"{recording_id}.mp4")

        # Clean up resources
        if self.writer:
            self.writer.release()
            self.writer = None

        if self.cap:
            self.cap.release()
            self.cap = None

        return {
            "status": "completed",
            "recording_id": recording_id,
            "filename": filename,
            "timestamp": time.time(),
        }

    def cleanup(self):
        """
        Clean up resources
        """
        if self.is_recording:
            self.stop_recording()

        if self.writer:
            self.writer.release()
            self.writer = None

        if self.cap:
            self.cap.release()
            self.cap = None

        logger.info("Video recorder cleaned up")
