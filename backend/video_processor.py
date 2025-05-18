import os

from moviepy import VideoFileClip
from recording import RecordingManager, RecordingResult
import whisper
import cv2
from deepface import DeepFace
from typing import List, Dict, Any, Tuple
from time import time, sleep
import logging
import subprocess
from models import DialogInput

logger = logging.getLogger(__name__)
# Set logger level to DEBUG for more detailed output
logger.setLevel(logging.DEBUG)

# Add a stream handler if none exists
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


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
            # For WebM files, use FFmpeg directly as it handles WebM better
            if video_path.lower().endswith(".webm"):
                logger.info("WebM file detected, using FFmpeg directly")
                return self._extract_audio_ffmpeg(video_path, output_audio)

            # For other formats, try MoviePy first
            clip = VideoFileClip(video_path)
            if clip.audio is not None:
                clip.audio.write_audiofile(output_audio, logger=None)
                return output_audio

            # If moviepy fails to extract audio (common on M-series Macs), try ffmpeg
            logger.info("MoviePy couldn't extract audio, trying ffmpeg")
            return self._extract_audio_ffmpeg(video_path, output_audio)

        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            # If all extraction methods fail, create a silent audio file
            logger.warning("No audio detected in video - creating silent audio")
            self._create_silent_audio(output_audio, 10)  # Create 10 seconds of silence
            return output_audio

    def _extract_audio_ffmpeg(self, video_path: str, output_audio: str) -> str:
        """
        Extract audio using FFmpeg with optimized settings for WebM files

        Args:
            video_path: Path to the video file
            output_audio: Path where the extracted audio will be saved

        Returns:
            Path to the extracted audio file
        """
        try:
            # Check if ffmpeg is installed
            subprocess.run(["which", "ffmpeg"], check=True, capture_output=True)

            # Use ffmpeg to extract audio with optimized settings
            cmd = [
                "ffmpeg",
                "-i",
                video_path,
                "-vn",  # Skip video
                "-acodec",
                "pcm_s16le",  # Convert to WAV format
                "-ar",
                "44100",  # Sample rate
                "-ac",
                "1",  # Mono
                "-y",  # Overwrite if exists
                output_audio,
            ]

            # Add specific options for WebM files
            if video_path.lower().endswith(".webm"):
                # Insert WebM-specific options after the input file
                cmd.insert(3, "-map")
                cmd.insert(4, "0:a:0")  # Explicitly map the first audio stream

            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else "Unknown error"
                logger.error(f"ffmpeg command failed: {stderr}")

                # Try alternate approach for WebM with opus codec
                if video_path.lower().endswith(".webm"):
                    logger.info("Trying alternate approach for WebM with opus codec")
                    alt_cmd = [
                        "ffmpeg",
                        "-i",
                        video_path,
                        "-vn",
                        "-af",
                        "aformat=s16:44100",  # Convert audio format
                        "-y",
                        output_audio,
                    ]
                    try:
                        subprocess.run(alt_cmd, check=True, capture_output=True)
                    except subprocess.CalledProcessError as alt_e:
                        alt_stderr = (
                            alt_e.stderr.decode("utf-8", errors="replace")
                            if alt_e.stderr
                            else "Unknown error"
                        )
                        logger.error(f"Alternative ffmpeg command failed: {alt_stderr}")
                        raise ValueError(f"ffmpeg error: {alt_stderr}")
                else:
                    raise ValueError(f"ffmpeg error: {stderr}")

            # Verify the output file exists
            if os.path.exists(output_audio) and os.path.getsize(output_audio) > 0:
                logger.info(f"Successfully extracted audio to {output_audio} using ffmpeg")
                return output_audio
            else:
                logger.warning("ffmpeg didn't produce a valid audio file")
                raise ValueError("ffmpeg produced an empty audio file")

        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg audio extraction failed: {e}")
            raise ValueError(f"ffmpeg error: {e}")
        except Exception as e:
            logger.error(f"Error in ffmpeg audio extraction: {e}")
            raise ValueError(f"Error in ffmpeg audio extraction: {e}")

    def _create_silent_audio(self, output_path: str, duration: int = 10):
        """Create a silent audio file for processing when no audio is available"""
        try:
            cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=mono:d={duration}",
                "-c:a",
                "pcm_s16le",  # WAV format
                "-ar",
                "44100",
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
            model = whisper.load_model("base.en")
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
        frame_data = []
        total_frames_extracted = 0

        # Create frame directory
        frame_dir = os.path.join(video_base_dir, "frames")
        os.makedirs(frame_dir, exist_ok=True)

        # If segments are empty (no audio), use default time ranges
        if not segments:
            # Create artificial segments every 3 seconds
            try:
                # Try to get video duration
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 30
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                video_duration = total_frames / fps
                cap.release()
            except Exception as e:
                logger.error(f"Error getting video duration: {e}")
                video_duration = 30  # Default 30 seconds

            video_length = int(video_duration)
            segment_duration = 3
            artificial_segments = []

            # Create segments from 0 to the video length
            for i in range(0, min(30, video_length), segment_duration):
                artificial_segments.append(
                    {"start": i, "end": i + segment_duration, "text": ""}  # Empty text
                )

            segments = artificial_segments
            logger.debug(f"No audio segments found. Created {len(segments)} artificial segments.")

        # Process each segment
        for i, seg in enumerate(segments):
            segment_frames = []
            start_time = seg["start"]
            end_time = seg["end"]
            duration = end_time - start_time

            # Skip very short segments
            if duration < 0.3:  # Skip segments shorter than 300ms
                logger.debug(f"Skipping segment {i} - too short: {duration:.2f}s")
                continue

            # Calculate FROM (33%) and TO (66%) timestamps
            from_timestamp = start_time + (duration * 0.33)
            to_timestamp = start_time + (duration * 0.66)

            # Calculate timestamps at regular intervals between FROM and TO
            timestamps = []
            current_time = from_timestamp
            frame_interval_sec = frame_interval_ms / 1000  # Convert ms to seconds
            while current_time <= to_timestamp:
                timestamps.append(current_time)
                current_time += frame_interval_sec

            # Ensure we have at least one frame
            if not timestamps and duration > 0.3:
                timestamps = [start_time + duration / 2]  # Take the middle

            logger.debug(
                f"Segment {i}: duration={duration:.2f}s, frames to extract={len(timestamps)}"
            )

            # Extract frames for this segment - create a new VideoCapture for each segment
            try:
                # Open a new video capture for each segment to avoid issues with seeking
                video = cv2.VideoCapture(video_path)
                fps = video.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    logger.warning(f"Invalid fps value: {fps}, defaulting to 30")
                    fps = 30

                valid_frames = 0
                frame_count = 0

                for timestamp in timestamps:
                    # Calculate frame number
                    frame_num = int(timestamp * fps)

                    # Method 1: Seek directly to the specific frame number
                    if video.set(cv2.CAP_PROP_POS_FRAMES, frame_num):
                        ret, frame = video.read()
                        if ret and frame is not None:
                            # Success with method 1
                            pass
                        else:
                            # Method 2: Seek using milliseconds
                            video.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                            ret, frame = video.read()

                            if not ret or frame is None:
                                # Try with a fresh video capture instance for this particular frame
                                video.release()
                                video = cv2.VideoCapture(video_path)
                                video.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                                ret, frame = video.read()

                                if not ret or frame is None:
                                    # Method 3: Try to get nearest frame with offsets
                                    found = False
                                    for offset in [-5, -2, 2, 5, 10, 20]:
                                        video.set(
                                            cv2.CAP_PROP_POS_FRAMES, max(0, frame_num + offset)
                                        )
                                        ret, frame = video.read()
                                        if ret and frame is not None:
                                            found = True
                                            break

                                    if not found:
                                        logger.debug(
                                            f"All methods failed for timestamp {timestamp:.2f}s"
                                        )
                                        continue
                    else:
                        # Direct frame seeking failed, try time-based seeking
                        video.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                        ret, frame = video.read()

                        if not ret or frame is None:
                            logger.debug(f"Failed to read frame at time {timestamp:.2f}s")
                            continue

                    # If we got a frame, process it
                    if ret and frame is not None:
                        # Check if frame is not black or nearly black
                        if not self._is_black_frame(frame):
                            path = f"{frame_dir}/frame_{i}_{frame_count}.jpg"
                            cv2.imwrite(path, frame)
                            segment_frames.append(path)
                            valid_frames += 1
                        else:
                            logger.debug(f"Frame at {timestamp:.2f}s is too dark, skipping")
                    else:
                        logger.debug(f"Failed to read frame at timestamp {timestamp:.2f}s")

                    frame_count += 1

                # Close the video capture for this segment
                video.release()

                total_frames_extracted += valid_frames
                logger.debug(
                    f"Segment {i}: extracted {valid_frames} valid frames out of {len(timestamps)} timestamps"
                )

                if segment_frames:
                    frame_data.append((segment_frames, seg["start"], seg["end"], seg["text"]))
                else:
                    logger.warning(f"No valid frames extracted for segment {i}")

            except Exception as e:
                logger.error(f"Error processing segment {i}: {str(e)}")
                # Ensure video is released in case of exception
                try:
                    video.release()
                except:
                    pass

        logger.info(f"Total frames extracted across all segments: {total_frames_extracted}")
        logger.info(f"Total segments with frames: {len(frame_data)} out of {len(segments)}")

        # If no frames were extracted at all, try a more aggressive approach
        if total_frames_extracted < 2:
            logger.warning(
                "No frames extracted with regular method, trying alternative extraction method"
            )
            alt_frames = self._extract_frames_alternative(video_path, segments)
            if alt_frames:
                logger.info(f"Alternative method extracted {len(alt_frames)} segments with frames")
                frame_data = alt_frames

        return frame_data

    def _extract_frames_alternative(
        self, video_path: str, segments: List[Dict[str, Any]]
    ) -> List[Tuple[List[str], float, float, str]]:
        """
        Alternative method to extract frames using FFmpeg for problematic videos.

        Args:
            video_path: Path to the video file
            segments: List of segments with start and end times

        Returns:
            List of tuples containing frame paths, start time, end time, and text
        """
        video_base_dir = os.path.dirname(video_path)
        frame_dir = os.path.join(video_base_dir, "frames")
        os.makedirs(frame_dir, exist_ok=True)

        frame_data = []
        total_frames = 0

        try:
            # Get video duration using FFmpeg
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                duration = float(result.stdout.strip())
                logger.debug(f"Video duration from FFmpeg: {duration}s")
            except (subprocess.SubprocessError, ValueError) as e:
                logger.warning(f"Failed to get duration with FFmpeg: {e}")
                # Estimate duration based on segments
                if segments:
                    duration = max(seg["end"] for seg in segments) + 1
                else:
                    duration = 30  # Default 30 seconds

            # Create sampling points (one frame every 2 seconds if no segments)
            if not segments:
                # Create artificial segments
                sample_interval = 2  # seconds
                artificial_segments = []
                for t in range(0, int(duration), sample_interval):
                    artificial_segments.append({"start": t, "end": t + sample_interval, "text": ""})
                segments = artificial_segments

            # Process each segment
            for i, seg in enumerate(segments):
                segment_frames = []
                start_time = seg["start"]
                end_time = seg["end"]
                midpoint = (start_time + end_time) / 2

                # Sample at 33%, 50%, and 66% of the segment
                timestamps = [
                    start_time + (end_time - start_time) * 0.33,
                    start_time + (end_time - start_time) * 0.5,
                    start_time + (end_time - start_time) * 0.66,
                ]

                # Extract frames using FFmpeg for each timestamp
                for j, ts in enumerate(timestamps):
                    output_path = f"{frame_dir}/alt_frame_{i}_{j}.jpg"

                    try:
                        # Use FFmpeg to extract the frame
                        cmd = [
                            "ffmpeg",
                            "-ss",
                            str(ts),
                            "-i",
                            video_path,
                            "-vframes",
                            "1",
                            "-q:v",
                            "2",
                            "-y",
                            output_path,
                        ]

                        subprocess.run(cmd, capture_output=True, check=True)

                        # Verify the extracted frame
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            # Check if frame is not too dark
                            img = cv2.imread(output_path)
                            if img is not None and not self._is_black_frame(img):
                                segment_frames.append(output_path)
                                total_frames += 1
                            else:
                                logger.debug(f"Extracted frame at {ts:.2f}s is too dark or invalid")
                                if os.path.exists(output_path):
                                    os.remove(output_path)
                        else:
                            logger.debug(f"Failed to extract frame at {ts:.2f}s")
                    except subprocess.SubprocessError as e:
                        logger.warning(f"FFmpeg extraction failed at {ts:.2f}s: {e}")

                if segment_frames:
                    frame_data.append((segment_frames, start_time, end_time, seg.get("text", "")))
                    logger.debug(
                        f"Alternative method: segment {i} extracted {len(segment_frames)} frames"
                    )

        except Exception as e:
            logger.error(f"Error in alternative frame extraction: {e}")

        logger.info(
            f"Alternative extraction method: extracted {total_frames} frames across {len(frame_data)} segments"
        )
        return frame_data

    def _is_black_frame(self, frame, threshold: int = 15) -> bool:
        """
        Check if a frame is black or nearly black

        Args:
            frame: OpenCV frame
            threshold: Brightness threshold (0-255)

        Returns:
            True if frame is considered black, False otherwise
        """
        # Convert to grayscale and calculate mean brightness
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = cv2.mean(gray)[0]

            return mean_brightness < threshold
        except Exception as e:
            logger.warning(f"Error checking frame brightness: {e}")
            return False  # If we can't check, assume it's not black

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
        logger.info(f"Starting emotion detection on {len(frames)} segments")

        # Define detection backends to try in order of preference
        backends = ["opencv", "retinaface", "ssd", "mtcnn", "mediapipe"]
        default_backend = "opencv"
        detected_frames_count = 0
        total_frames_analyzed = 0

        for idx, (frame_paths, start, end, text) in enumerate(frames):
            # Skip segments with no valid frames
            if not frame_paths:
                logger.warning(f"Segment {idx}: No frames to analyze")
                continue

            emotion_probs_all = []
            confidence_weights = []
            frame_timestamps = []  # Track relative position of each frame in segment
            duration = end - start
            total_frames_analyzed += len(frame_paths)

            # Try to analyze all frames in the segment
            for frame_idx, path in enumerate(frame_paths):
                # Estimate frame's position in timeline (for transition analysis)
                rel_position = frame_idx / (len(frame_paths) - 1 if len(frame_paths) > 1 else 1)
                frame_time = start + (rel_position * duration)
                frame_timestamps.append(frame_time)

                # Try the default backend first
                detected = False
                for backend in [default_backend] + [b for b in backends if b != default_backend]:
                    if detected:
                        break

                    try:
                        # Verify the image exists and is valid
                        if not os.path.exists(path) or os.path.getsize(path) == 0:
                            logger.warning(f"Frame file missing or empty: {path}")
                            continue

                        # Try to read the image to verify it's valid
                        img = cv2.imread(path)
                        if img is None:
                            logger.warning(f"Unable to read image: {path}")
                            continue

                        # For very small images, resize them
                        height, width = img.shape[:2]
                        if height < 100 or width < 100:
                            logger.debug(f"Image too small ({width}x{height}), resizing")
                            img = cv2.resize(img, (max(width * 2, 200), max(height * 2, 200)))
                            resized_path = path.replace(".jpg", "_resized.jpg")
                            cv2.imwrite(resized_path, img)
                            path = resized_path

                        # Use DeepFace to analyze emotions with detailed analysis
                        analysis = DeepFace.analyze(
                            img_path=path,
                            actions=["emotion"],
                            enforce_detection=False,
                            detector_backend=backend,
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
                            if confidence > 0.1:
                                emotion_probs_all.append(emotion_probs)
                                confidence_weights.append(confidence)
                                detected = True
                                detected_frames_count += 1
                                break
                            else:
                                logger.debug(f"Frame {frame_idx} confidence too low: {confidence}")
                        else:
                            logger.debug(
                                f"No analysis results for frame {frame_idx} with {backend}"
                            )
                    except Exception as e:
                        logger.debug(
                            f"Emotion detection failed with {backend} for frame {path}: {str(e)}"
                        )
                        # Continue to the next backend
                        continue

                if not detected:
                    logger.debug(f"Failed to detect emotions in frame {path} with all backends")

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
                    # Create a copy of weighted_avg before modifying it
                    weighted_avg_copy = weighted_avg.copy()
                    for emotion, variance in emotion_variance.items():
                        weighted_avg_copy[f"{emotion}_variance"] = variance
                    weighted_avg = weighted_avg_copy

                else:
                    logger.warning(f"Segment {idx}: Total confidence weight is zero")
                    weighted_avg = self._get_default_emotions()
            elif len(emotion_probs_all) == 1:
                # Just use the single emotion set if only one valid frame
                weighted_avg = emotion_probs_all[0].copy()  # Create a copy
                # Normalize to percentage
                total = sum(weighted_avg.values())
                if total > 0:
                    weighted_avg = {k: round((v / total) * 100, 1) for k, v in weighted_avg.items()}
                weighted_avg["stability"] = 100.0  # Only one data point = perfect stability
                weighted_avg["transition_score"] = 0.0  # No transitions with one frame
                weighted_avg["consistent_emotion"] = True
                # Add zero variance for all emotions
                # Create a copy to avoid modifying during iteration
                emotion_keys = [
                    k
                    for k in weighted_avg.keys()
                    if not k.endswith("_variance")
                    and k not in ["stability", "transition_score", "consistent_emotion"]
                ]
                for emotion in emotion_keys:
                    weighted_avg[f"{emotion}_variance"] = 0.0
            else:
                # Default emotions if detection fails
                logger.warning(f"Segment {idx}: No valid emotion data detected, using defaults")
                weighted_avg = self._get_default_emotions()

            results.append({"time": (start, end), "text": text, "emotions": weighted_avg})

        detection_rate = (
            (detected_frames_count / total_frames_analyzed * 100)
            if total_frames_analyzed > 0
            else 0
        )

        return results

    def _is_default_emotion(self, emotions):
        """Check if the emotions dict matches the default neutral emotions"""
        return (
            emotions.get("neutral", 0) > 90
            and emotions.get("happy", 0) < 5
            and emotions.get("angry", 0) < 5
            and emotions.get("sad", 0) < 5
        )

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

        logger.info(f"Processing video: {video_path}")

        segments = self.transcribe_audio(video_path)
        logger.info(f"Transcription complete: {len(segments)} segments")

        frames = self.extract_frames(video_path, segments)
        logger.info(f"Frame extraction complete: {len(frames)} segments with frames")

        emotion_results = self.detect_emotions(frames)
        logger.info(f"Emotion detection complete: {len(emotion_results)} segments with emotions")

        dialog_input = DialogInput(video_path, emotion_results)
        logger.info(f"Created DialogInput with {len(dialog_input.sentences)} sentences")

        # Debug - check if we're getting all neutral emotions
        neutral_count = 0
        for emotion in dialog_input.emotions:
            if emotion.neutral > 90 and emotion.happy < 5 and emotion.angry < 5:
                neutral_count += 1

        if neutral_count == len(dialog_input.emotions) and len(dialog_input.emotions) > 0:
            logger.warning(
                f"ALL {len(dialog_input.emotions)} emotions are neutral - this suggests deepface is not working correctly"
            )

        return dialog_input


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
