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
        self, video_path: str, segments: List[Dict[str, Any]], frame_interval_ms: int = 100
    ) -> List[Tuple[List[str], float, float, str]]:
        """
        Extract frames continuously FROM the 25% mark TO the 75% mark of each segment duration
        to avoid capturing button pressing actions at the start and end.

        Args:
            video_path: Path to the video file
            segments: List of segments with start and end times
            frame_interval_ms: Milliseconds between each frame extraction within the 25%-75% range

        Returns:
            List of tuples containing frame paths, start time, end time, and text
        """
        video_base_dir = os.path.dirname(video_path)
        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_interval_sec = frame_interval_ms / 1000  # Convert ms to seconds

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

            # Skip very short segments
            if duration < 0.3:  # Skip segments shorter than 300ms
                continue

            # Calculate FROM (25%) and TO (75%) timestamps
            from_timestamp = start_time + (duration * 0.33)
            to_timestamp = start_time + (duration * 0.66)

            # Calculate timestamps at regular intervals between FROM and TO
            timestamps = []
            current_time = from_timestamp
            while current_time <= to_timestamp:
                timestamps.append(current_time)
                current_time += frame_interval_sec

            # Ensure we have at least one frame
            if not timestamps and duration > 0.3:
                timestamps = [start_time + duration / 2]  # Take the middle

            # Extract frames at calculated timestamps
            frame_dir = os.path.join(video_base_dir, "frames")
            os.makedirs(frame_dir, exist_ok=True)

            for j, timestamp in enumerate(timestamps):
                frame_num = int(timestamp * fps)
                video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = video.read()
                if ret:
                    # Check if frame is not black or nearly black
                    if not self._is_black_frame(frame):
                        path = f"{frame_dir}/frame_{i}_{j}.jpg"
                        cv2.imwrite(path, frame)
                        segment_frames.append(path)

            if segment_frames:
                frame_data.append((segment_frames, seg["start"], seg["end"], seg["text"]))

        video.release()
        return frame_data

    def _is_black_frame(self, frame, threshold: int = 20) -> bool:
        """
        Check if a frame is black or nearly black

        Args:
            frame: OpenCV frame
            threshold: Brightness threshold (0-255)

        Returns:
            True if frame is considered black, False otherwise
        """
        # Convert to grayscale and calculate mean brightness
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = cv2.mean(gray)[0]

        return mean_brightness < threshold

    def detect_emotions(
        self, frames: List[Tuple[List[str], float, float, str]]
    ) -> List[Dict[str, Any]]:
        """
        Detect emotions from frames with improved aggregation techniques.
        Now handles frames collected at 200ms intervals with more robust emotion analysis.

        Args:
            frames: List of tuples containing frame paths, start time, end time, and text

        Returns:
            List of dictionaries with timestamps, text, and detailed emotion data
        """
        results = []
        for frame_paths, start, end, text in frames:
            # Skip segments with no valid frames
            if not frame_paths:
                continue

            emotion_probs_all = []
            confidence_weights = []
            frame_timestamps = []  # Track relative position of each frame in segment

            duration = end - start

            for idx, path in enumerate(frame_paths):
                # Estimate frame's position in timeline (for transition analysis)
                rel_position = idx / (len(frame_paths) - 1 if len(frame_paths) > 1 else 1)
                frame_time = start + (rel_position * duration)
                frame_timestamps.append(frame_time)

                try:
                    # Use DeepFace to analyze emotions with detailed analysis
                    analysis = DeepFace.analyze(
                        img_path=path,
                        actions=["emotion"],
                        enforce_detection=False,
                        detector_backend="opencv",
                        silent=True,
                    )

                    if analysis and isinstance(analysis, list) and len(analysis) > 0:
                        # Extract emotion probabilities
                        emotion_probs = analysis[0]["emotion"]
                        emotion_probs = {k: float(v) for k, v in emotion_probs.items()}

                        # Extract face detection confidence as weight
                        region = analysis[0].get("region", {})
                        confidence = region.get("confidence", 0.5) if region else 0.5

                        # Only include results with reasonable confidence
                        if confidence > 0.2:
                            emotion_probs_all.append(emotion_probs)
                            confidence_weights.append(confidence)
                except Exception as e:
                    logger.debug(f"Emotion detection failed for frame {path}: {str(e)}")
                    continue

            # Process results only if we have enough valid data
            if len(emotion_probs_all) >= 2:
                # Calculate weighted average emotions
                all_emotions = set().union(*[d.keys() for d in emotion_probs_all])
                total_weight = sum(confidence_weights)

                if total_weight > 0:
                    # Compute weighted average emotions
                    weighted_avg = {
                        emotion: sum(
                            d.get(emotion, 0) * weight
                            for d, weight in zip(emotion_probs_all, confidence_weights)
                        )
                        / total_weight
                        for emotion in all_emotions
                    }

                    # Normalize to ensure they sum to 100
                    total = sum(weighted_avg.values())
                    if total > 0:
                        weighted_avg = {
                            k: round((v / total) * 100, 1) for k, v in weighted_avg.items()
                        }

                    # Emotion stability analysis
                    emotion_stability = self._calculate_emotion_stability(emotion_probs_all)
                    weighted_avg["stability"] = emotion_stability

                    # Emotion transitions and patterns
                    dominant_sequence = self._get_emotion_sequence(emotion_probs_all)
                    transitions = self._analyze_emotion_transitions(dominant_sequence)
                    weighted_avg["transition_score"] = transitions["transition_score"]
                    weighted_avg["consistent_emotion"] = transitions["consistent_emotion"]

                    # Compute variance for each emotion (showing volatility)
                    emotion_variance = self._calculate_emotion_variance(emotion_probs_all)
                    for emotion, variance in emotion_variance.items():
                        weighted_avg[f"{emotion}_variance"] = variance
                else:
                    weighted_avg = self._get_default_emotions()
            elif len(emotion_probs_all) == 1:
                # Just use the single emotion set if only one valid frame
                weighted_avg = emotion_probs_all[0]
                # Normalize to percentage
                total = sum(weighted_avg.values())
                if total > 0:
                    weighted_avg = {k: round((v / total) * 100, 1) for k, v in weighted_avg.items()}
                weighted_avg["stability"] = 100.0  # Only one data point = perfect stability
                weighted_avg["transition_score"] = 0.0  # No transitions with one frame
                weighted_avg["consistent_emotion"] = True
                # Add zero variance for all emotions
                for emotion in weighted_avg.keys():
                    if not emotion.endswith("_variance") and emotion not in [
                        "stability",
                        "transition_score",
                        "consistent_emotion",
                    ]:
                        weighted_avg[f"{emotion}_variance"] = 0.0
            else:
                # Default emotions if detection fails
                weighted_avg = self._get_default_emotions()

            results.append({"time": (start, end), "text": text, "emotions": weighted_avg})
        return results

    def _calculate_emotion_stability(self, emotion_probs_list: List[Dict[str, float]]) -> float:
        """
        Calculate the stability of emotions across multiple frames.
        Higher score means more consistent dominant emotion.

        Args:
            emotion_probs_list: List of emotion probability dictionaries

        Returns:
            Stability score between 0-100 (higher = more stable)
        """
        if not emotion_probs_list or len(emotion_probs_list) < 2:
            return 100.0  # Default high stability if insufficient data

        # Get the dominant emotion for each frame
        dominant_emotions = [
            max(probs.items(), key=lambda x: x[1])[0] for probs in emotion_probs_list
        ]

        # Count occurrences of each emotion
        from collections import Counter

        emotion_counts = Counter(dominant_emotions)

        # Calculate stability as percentage of frames with most common emotion
        most_common_count = emotion_counts.most_common(1)[0][1]
        stability = (most_common_count / len(dominant_emotions)) * 100

        return round(stability, 1)

    def _get_emotion_sequence(self, emotion_probs_list: List[Dict[str, float]]) -> List[str]:
        """
        Get sequence of dominant emotions across frames

        Args:
            emotion_probs_list: List of emotion probability dictionaries

        Returns:
            List of dominant emotion strings in sequence
        """
        return [max(probs.items(), key=lambda x: x[1])[0] for probs in emotion_probs_list]

    def _analyze_emotion_transitions(self, emotion_sequence: List[str]) -> Dict[str, Any]:
        """
        Analyze transitions between emotions in a sequence

        Args:
            emotion_sequence: List of emotions in sequential order

        Returns:
            Dictionary with transition analysis
        """
        if not emotion_sequence or len(emotion_sequence) < 2:
            return {"transition_score": 0.0, "consistent_emotion": True}

        # Count transitions (changes between consecutive emotions)
        transitions = sum(
            1
            for i in range(1, len(emotion_sequence))
            if emotion_sequence[i] != emotion_sequence[i - 1]
        )

        # Normalize to percentage (0% = no transitions, 100% = every frame different)
        max_possible_transitions = len(emotion_sequence) - 1
        transition_score = (
            (transitions / max_possible_transitions) * 100 if max_possible_transitions > 0 else 0
        )

        # Consistent emotion = low transition score
        consistent_emotion = transition_score < 30  # Less than 30% transitions

        return {
            "transition_score": round(transition_score, 1),
            "consistent_emotion": consistent_emotion,
        }

    def _calculate_emotion_variance(
        self, emotion_probs_list: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Calculate variance for each emotion across frames

        Args:
            emotion_probs_list: List of emotion probability dictionaries

        Returns:
            Dictionary with variance for each emotion
        """
        if not emotion_probs_list or len(emotion_probs_list) < 2:
            return (
                {emotion: 0.0 for emotion in emotion_probs_list[0].keys()}
                if emotion_probs_list
                else {}
            )

        # Get all unique emotions
        all_emotions = set().union(*[d.keys() for d in emotion_probs_list])

        # Calculate variance for each emotion
        variances = {}
        for emotion in all_emotions:
            # Extract values for this emotion across all frames
            values = [d.get(emotion, 0) for d in emotion_probs_list]

            # Calculate variance
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)

            # Store normalized variance (0-100 scale)
            variances[emotion] = round(min(variance * 10, 100), 1)  # Scale and cap at 100

        return variances

    def _get_default_emotions(self) -> Dict[str, float]:
        """Return default emotion values when detection fails"""
        base = {
            "angry": 0.0,
            "disgust": 0.0,
            "fear": 0.0,
            "happy": 0.0,
            "sad": 0.0,
            "surprise": 0.0,
            "neutral": 100.0,  # Default to neutral if no emotions detected
            "stability": 100.0,  # Default high stability
            "transition_score": 0.0,
            "consistent_emotion": True,
        }

        # Add default variance values
        for emotion in ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]:
            base[f"{emotion}_variance"] = 0.0

        return base

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
                f"  Emotions: Angry={emotion.angry:.1f}, Happy={emotion.happy:.1f}, Neutral={emotion.neutral:.1f}"
            )

        end_time = time()
        print(f"Total execution time: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"Error processing video: {e}")
