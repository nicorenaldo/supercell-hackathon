import os

from moviepy import VideoFileClip
from recording_manager.manager import RecordingManager, RecordingResult
import whisper
import cv2
from deepface import DeepFace
from typing import List, Dict, Any, Tuple
from time import time, sleep
import logging
import subprocess
from models import DialogInput

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Main class for processing video files and extracting dialog and emotions"""

    def __init__(self, output_folder: str = "recordings"):
        """
        Initialize the video processor

        Args:
            output_folder: Directory where extracted frames will be saved
        """
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)

    def validate_video(self, video_path: str) -> bool:
        """
        Validate that the video file exists and can be read

        Args:
            video_path: Path to the video file

        Returns:
            True if video is valid, raises ValueError otherwise
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise ValueError(f"Could not read frames from video file: {video_path}")
        return True

    def extract_audio(self, video_path: str, output_audio: str = "recordings/temp.wav") -> str:
        """
        Extract audio from video file

        Args:
            video_path: Path to the video file
            output_audio: Path where the extracted audio will be saved

        Returns:
            Path to the extracted audio file
        """
        try:
            # First try with moviepy
            clip = VideoFileClip(video_path)
            if clip.audio is not None:
                clip.audio.write_audiofile(output_audio, logger=None)
                return output_audio

            # If moviepy fails to extract audio (common on M-series Macs), try ffmpeg
            logger.info("MoviePy couldn't extract audio, trying ffmpeg")
            try:
                # Check if ffmpeg is installed
                subprocess.run(["which", "ffmpeg"], check=True, capture_output=True)

                # Use ffmpeg to extract audio
                cmd = [
                    "ffmpeg",
                    "-i",
                    video_path,
                    "-q:a",
                    "0",
                    "-map",
                    "a",
                    "-y",  # Overwrite if exists
                    output_audio,
                ]

                subprocess.run(cmd, check=True, capture_output=True)

                # Verify the output file exists
                if os.path.exists(output_audio) and os.path.getsize(output_audio) > 0:
                    logger.info(f"Successfully extracted audio to {output_audio} using ffmpeg")
                    return output_audio
                else:
                    logger.warning("ffmpeg didn't produce a valid audio file")
            except subprocess.CalledProcessError as e:
                logger.error(f"ffmpeg audio extraction failed: {e}")
            except Exception as e:
                logger.error(f"Error in ffmpeg audio extraction: {e}")

            # If all extraction methods fail, create a silent audio file
            logger.warning("No audio detected in video - creating silent audio")
            self._create_silent_audio(output_audio, 10)  # Create 10 seconds of silence
            return output_audio

        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise ValueError(f"Failed to extract audio from video: {str(e)}")

    def _create_silent_audio(self, output_path: str, duration: int = 10):
        """Create a silent audio file for processing when no audio is available"""
        try:
            cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo:d={duration}",
                "-y",  # Overwrite if exists
                output_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Created silent audio file: {output_path}")
        except Exception as e:
            logger.error(f"Failed to create silent audio: {e}")
            with open(output_path, "wb") as f:
                f.write(b"")

    def transcribe_audio(self, video_path: str) -> List[Dict[str, Any]]:
        """
        Transcribe audio from video file with timestamps

        Args:
            video_path: Path to the video file

        Returns:
            List of segments with start time, end time, and transcribed text
        """
        self.validate_video(video_path)
        audio_path = self.extract_audio(video_path)

        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            logger.warning("Empty audio file. Returning empty transcription.")
            return []

        try:
            model = whisper.load_model("base")
            result = model.transcribe(audio_path, word_timestamps=True)
            return result["segments"]
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return []

    def extract_frames(
        self, video_path: str, segments: List[Dict[str, Any]], n: int = 3
    ) -> List[Tuple[List[str], float, float, str]]:
        """
        Extract n frames from each segment with uniform distribution

        Args:
            video_path: Path to the video file
            segments: List of segments with start and end times
            n: Number of frames to extract per segment

        Returns:
            List of tuples containing frame paths, start time, end time, and text
        """
        video_base_dir = os.path.dirname(video_path)
        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)

        frame_data = []

        # If segments are empty (no audio), use default time ranges
        if not segments:
            # Create artificial segments every 3 seconds for a 30-second window
            video_length = int(video.get(cv2.CAP_PROP_FRAME_COUNT) / fps)
            segment_duration = 3
            artificial_segments = []

            for i in range(0, min(30, video_length), segment_duration):
                artificial_segments.append(
                    {"start": i, "end": i + segment_duration, "text": ""}  # Empty text
                )

            segments = artificial_segments

        for i, seg in enumerate(segments):
            segment_frames = []
            start_time = seg["start"]
            end_time = seg["end"]
            duration = end_time - start_time

            # Handle different numbers of frames
            if n <= 0:
                n = 1  # Ensure at least one frame

            if n == 1:
                # For single frame, take the middle
                timestamps = [start_time + duration / 2]
            else:
                # For multiple frames, distribute evenly
                timestamps = [start_time + (duration * j / (n - 1)) for j in range(n)]

            # Extract frames at calculated timestamps
            frame_dir = os.path.join(video_base_dir, "frames")
            os.makedirs(frame_dir, exist_ok=True)

            for j, timestamp in enumerate(timestamps):
                frame_num = int(timestamp * fps)
                video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = video.read()
                if ret:
                    path = f"{frame_dir}/frame_{i}_{j}.jpg"
                    cv2.imwrite(path, frame)
                    segment_frames.append(path)

            if segment_frames:
                frame_data.append((segment_frames, seg["start"], seg["end"], seg["text"]))

        video.release()
        return frame_data

    def detect_emotions(
        self, frames: List[Tuple[List[str], float, float, str]]
    ) -> List[Dict[str, Any]]:
        """
        Detect emotions from frames with probability output

        Args:
            frames: List of tuples containing frame paths, start time, end time, and text

        Returns:
            List of dictionaries with timestamps, text, and emotion data
        """
        results = []
        for frame_paths, start, end, text in frames:
            emotion_probs_all = []

            for path in frame_paths:
                try:
                    # Use DeepFace to analyze emotions
                    analysis = DeepFace.analyze(
                        img_path=path, actions=["emotion"], enforce_detection=False, silent=True
                    )

                    if analysis:
                        # Extract and convert emotion probabilities
                        emotion_probs = analysis[0]["emotion"]
                        emotion_probs = {k: float(v) for k, v in emotion_probs.items()}
                        emotion_probs_all.append(emotion_probs)
                except Exception:
                    # Skip frames where emotion detection fails
                    continue

            # Average emotion probabilities across all frames
            if emotion_probs_all:
                # Get all unique emotion keys
                all_emotions = set().union(*[d.keys() for d in emotion_probs_all])
                # Average each emotion's probability
                averaged = {
                    emotion: sum(d.get(emotion, 0) for d in emotion_probs_all)
                    / len(emotion_probs_all)
                    for emotion in all_emotions
                }
                # Normalize probabilities to ensure they sum to 100
                total = sum(averaged.values())
                if total > 0:
                    averaged = {k: (v / total) * 100 for k, v in averaged.items()}
            else:
                # Default emotion values if detection fails
                averaged = {
                    "angry": 0,
                    "disgust": 0,
                    "fear": 0,
                    "happy": 0,
                    "sad": 0,
                    "surprise": 0,
                    "neutral": 100,  # Default to neutral if no emotions detected
                }

            results.append({"time": (start, end), "text": text, "emotions": averaged})
        return results

    def process_video(self, video_path: str) -> DialogInput:
        """
        Process video file and extract dialog and emotions

        Args:
            video_path: Path to the video file

        Returns:
            DialogInput object with extracted dialog and emotions
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        segments = self.transcribe_audio(video_path)
        frames = self.extract_frames(video_path, segments)
        emotion_results = self.detect_emotions(frames)

        return DialogInput(video_path, emotion_results)


if __name__ == "__main__":
    print("Starting video processor...")
    processor = VideoProcessor()
    print("Video processor initialized")
    recording_manager = RecordingManager()
    print("Recording manager initialized")
    try:
        print("Starting recording...")
        recording_manager.start_recording()
        sleep(5)
        result: RecordingResult = recording_manager.stop_recording()
        print("Recording stopped")
        print(result)
        start_time = time()
        dialog_input = processor.process_video(result.file_path)

        print(f"Processed {len(dialog_input.sentences)} dialog segments")
        for i, (text, emotion) in enumerate(zip(dialog_input.sentences, dialog_input.emotions)):
            print(f"Segment {i+1}: {text}")
            print(
                f"  Start: {dialog_input.start_times[i]:.2f}s, End: {dialog_input.end_times[i]:.2f}s"
            )
            print(
                f"  Emotions: Angry={emotion.angry:.2f}, Happy={emotion.happy:.2f}, Neutral={emotion.neutral:.2f}"
            )

        end_time = time()
        print(f"Total execution time: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"Error processing video: {e}")
