import os
import time
import threading
import logging
import cv2
import numpy as np
import platform
import subprocess
import tempfile
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
        os.makedirs(os.path.join(self.output_dir, "audio"), exist_ok=True)

        # Video capture and recording variables
        self.cap = None
        self.writer = None
        self.is_recording = False
        self.recording_thread = None
        self.audio_thread = None
        self.current_recording_id = None
        self.last_frame = None
        self.audio_process = None
        self.audio_filename = None

        # Fourcc code for video codec - use avc1 (H.264) for better compatibility
        self.fourcc = cv2.VideoWriter_fourcc(*"avc1")

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

    def _record_audio(self):
        """
        Record audio from microphone in a separate thread using ffmpeg
        """
        is_macos = platform.system() == "Darwin"

        if is_macos:
            try:
                # Create audio file path
                self.audio_filename = os.path.join(
                    self.output_dir, "audio", f"{self.current_recording_id}.wav"
                )

                # For macOS, use ffmpeg to record from default input device
                # Using format avfoundation for macOS
                cmd = [
                    "ffmpeg",
                    "-f",
                    "avfoundation",
                    "-i",
                    ":0",  # Use default audio input device
                    "-c:a",
                    "pcm_s16le",  # Use WAV format
                    "-ar",
                    "44100",  # Sample rate
                    "-y",  # Overwrite if exists
                    self.audio_filename,
                ]

                logger.info(f"Starting audio recording with command: {' '.join(cmd)}")

                # Start recording process
                self.audio_process = subprocess.Popen(
                    cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

                logger.info(f"Audio recording started: {self.audio_filename}")

                # Wait while recording is active
                while self.is_recording and self.audio_process.poll() is None:
                    time.sleep(0.1)

                # If we're stopping recording and process is still running
                if self.audio_process.poll() is None:
                    # Send 'q' to ffmpeg to stop recording gracefully
                    try:
                        self.audio_process.communicate(input=b"q", timeout=2.0)
                    except subprocess.TimeoutExpired:
                        # If it doesn't stop gracefully, terminate
                        self.audio_process.terminate()
                        time.sleep(0.5)
                        if self.audio_process.poll() is None:
                            self.audio_process.kill()

                logger.info("Audio recording stopped")

            except Exception as e:
                logger.error(f"Error in audio recording: {str(e)}")
                if self.audio_process and self.audio_process.poll() is None:
                    self.audio_process.terminate()
                self.audio_process = None

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
            # For macOS, try multiple camera indices with preference for FaceTime camera
            camera_index = 0
            is_macos = platform.system() == "Darwin"

            # For Apple Silicon Macs, try these specific camera indices first
            preferred_indices = [0, 1]  # Try built-in camera first

            if is_macos:
                # First try the preferred indices for M-series Macs
                for i in preferred_indices:
                    test_cap = cv2.VideoCapture(i)
                    if test_cap.isOpened():
                        ret, test_frame = test_cap.read()
                        if ret:
                            camera_index = i
                            test_cap.release()
                            logger.info(f"Found working camera at index {camera_index}")
                            break
                    test_cap.release()

                # If we didn't find a camera in the preferred indices, try more indices
                if camera_index not in preferred_indices:
                    for i in range(2, 10):  # Try additional camera indices
                        test_cap = cv2.VideoCapture(i)
                        if test_cap.isOpened():
                            ret, test_frame = test_cap.read()
                            if ret:
                                camera_index = i
                                test_cap.release()
                                logger.info(f"Found working camera at index {camera_index}")
                                break
                        test_cap.release()

            self.cap = cv2.VideoCapture(camera_index)

            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            # Try to enable auto exposure and auto white balance for better image quality
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Auto exposure
            self.cap.set(cv2.CAP_PROP_AUTO_WB, 1)  # Auto white balance

            # Verify that video capture is working
            ret, test_frame = self.cap.read()
            if not ret:
                raise ValueError("Could not open webcam")

            # Initialize video writer with H.264 codec for better compatibility
            filename = os.path.join(self.output_dir, f"{recording_id}.mp4")
            self.writer = cv2.VideoWriter(
                filename, self.fourcc, self.fps, (self.width, self.height)
            )

            # Set recording variables
            self.is_recording = True
            self.current_recording_id = recording_id

            # Start recording thread for video
            self.recording_thread = threading.Thread(target=self._record_video)
            self.recording_thread.daemon = True
            self.recording_thread.start()

            # Start recording thread for audio (if on macOS)
            if is_macos:
                self.audio_thread = threading.Thread(target=self._record_audio)
                self.audio_thread.daemon = True
                self.audio_thread.start()

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

        # Wait for audio thread to finish
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2.0)

        recording_id = self.current_recording_id
        filename = os.path.join(self.output_dir, f"{recording_id}.mp4")

        # Clean up resources
        if self.writer:
            self.writer.release()
            self.writer = None

        if self.cap:
            self.cap.release()
            self.cap = None

        # Merge audio with video if audio was recorded
        if self.audio_filename and os.path.exists(self.audio_filename):
            self._merge_audio_with_video(filename, self.audio_filename)
        else:
            # Add silent audio track if no audio was recorded
            self._add_audio_to_video_mac(filename)

        return {
            "status": "completed",
            "recording_id": recording_id,
            "filename": filename,
            "timestamp": time.time(),
        }

    def _merge_audio_with_video(self, video_path: str, audio_path: str):
        """
        Merge recorded audio with video using ffmpeg
        """
        try:
            # Check if ffmpeg is installed
            subprocess.run(["which", "ffmpeg"], check=True, capture_output=True)

            # Create a temporary file for the output
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                temp_output = temp_file.name

            # Run ffmpeg to merge audio and video
            cmd = [
                "ffmpeg",
                "-i",
                video_path,  # Input video
                "-i",
                audio_path,  # Input audio
                "-c:v",
                "copy",  # Copy video stream
                "-c:a",
                "aac",  # Convert audio to AAC
                "-map",
                "0:v:0",  # Use video from first input
                "-map",
                "1:a:0",  # Use audio from second input
                "-shortest",  # End when shortest input ends
                "-y",  # Overwrite if exists
                temp_output,
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            # Replace original file with the new one
            os.replace(temp_output, video_path)
            logger.info(f"Merged audio with video: {video_path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to merge audio with video: {e}")
            # If merging fails, try adding a silent audio track
            self._add_audio_to_video_mac(video_path)
        except Exception as e:
            logger.error(f"Error merging audio with video: {e}")
            # If merging fails, try adding a silent audio track
            self._add_audio_to_video_mac(video_path)

    def _add_audio_to_video_mac(self, video_path: str):
        """
        Add audio to video on macOS using ffmpeg
        This is needed because OpenCV doesn't support audio recording
        """
        try:
            # Check if ffmpeg is installed
            subprocess.run(["which", "ffmpeg"], check=True, capture_output=True)

            # Create a temporary file for the output
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                temp_output = temp_file.name

            # Run ffmpeg to add audio from microphone to the video
            # This creates a new video file with both video and audio
            cmd = [
                "ffmpeg",
                "-i",
                video_path,  # Input video (no audio)
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=stereo",  # Generate silent audio track
                "-c:v",
                "copy",  # Copy video stream
                "-c:a",
                "aac",  # Use AAC for audio
                "-shortest",  # End when shortest input ends
                "-y",  # Overwrite if exists
                temp_output,
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            # Replace original file with the new one
            os.replace(temp_output, video_path)
            logger.info(f"Added silent audio track to video: {video_path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to add audio to video: {e}")
        except Exception as e:
            logger.error(f"Error adding audio to video: {e}")

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

        # Clean up audio process if it's still running
        if self.audio_process and self.audio_process.poll() is None:
            self.audio_process.terminate()
            self.audio_process = None

        logger.info("Video recorder cleaned up")
