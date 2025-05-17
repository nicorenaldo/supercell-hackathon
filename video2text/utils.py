import whisper
import cv2
import os
from moviepy import VideoFileClip
from deepface import DeepFace
from time import sleep, time
from fer import FER
import numpy as np

def validate_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise ValueError(f"Could not read frames from video file: {video_path}")
    return True

# Step 1: Transcribe audio with timestamps
def transcribe_audio(video_path):
    validate_video(video_path)  # Add validation check
    audio_path = extract_audio_from_video(video_path)
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True)
    return result['segments']

# Step 2: Extract multiple frames per sentence
def extract_frames(video_path, segments, n=3, output_folder='frames'):
    """Extract n frames from each segment with uniform distribution.
    Args:
        video_path: Path to video file
        segments: List of segments with start and end times
        n: Number of frames to extract per segment (minimum 1)
        output_folder: Where to save extracted frames
    """
    os.makedirs(output_folder, exist_ok=True)
    video = cv2.VideoCapture(video_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    
    frame_data = []
    for i, seg in enumerate(segments):
        segment_frames = []
        start_time = seg['start']
        end_time = seg['end']
        duration = end_time - start_time
        
        # Handle different numbers of frames
        if n <= 0:
            n = 1  # Ensure at least one frame
        
        if n == 1:
            # For single frame, take the middle
            timestamps = [start_time + duration/2]
        else:
            # For multiple frames, include start and end, and distribute the rest evenly
            timestamps = [
                start_time + (duration * j / (n - 1))
                for j in range(n)
            ]
        
        # Extract frames at calculated timestamps
        for j, timestamp in enumerate(timestamps):
            frame_num = int(timestamp * fps)
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = video.read()
            if ret:
                path = f"{output_folder}/frame_{i}_{j}.jpg"
                cv2.imwrite(path, frame)
                segment_frames.append(path)
        
        if segment_frames:
            frame_data.append((segment_frames, seg['start'], seg['end'], seg['text']))
    
    video.release()
    return frame_data

def preprocess_image(img):
    # Resize to a reasonable size while maintaining aspect ratio
    height, width = img.shape[:2]
    max_dim = 640
    if height > max_dim or width > max_dim:
        scale = max_dim / max(height, width)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = cv2.resize(img, (new_width, new_height))
    return img

# Step 3: Emotion analysis with probability output
def detect_emotions(frames):
    results = []
    for frame_paths, start, end, text in frames:
        emotion_probs_all = []
        
        for path in frame_paths:
            try:
                # Use DeepFace to analyze emotions
                analysis = DeepFace.analyze(
                    img_path=path,
                    actions=['emotion'],
                    enforce_detection=False,
                    silent=True
                )
                
                if analysis:
                    # DeepFace returns emotion probabilities as percentages
                    emotion_probs = analysis[0]['emotion']
                    # Convert percentage strings to float values
                    emotion_probs = {k: float(v) for k, v in emotion_probs.items()}
                    emotion_probs_all.append(emotion_probs)
            except Exception as e:
                continue
        
        # Average emotion probabilities across all frames
        if emotion_probs_all:
            # Get all unique emotion keys
            all_emotions = set().union(*[d.keys() for d in emotion_probs_all])
            # Average each emotion's probability
            averaged = {
                emotion: sum(d.get(emotion, 0) for d in emotion_probs_all) / len(emotion_probs_all)
                for emotion in all_emotions
            }
            # Normalize probabilities to ensure they sum to 100
            total = sum(averaged.values())
            if total > 0:
                averaged = {k: (v/total) * 100 for k, v in averaged.items()}
        else:
            averaged = {
                'angry': 0, 'disgust': 0, 'fear': 0, 
                'happy': 0, 'sad': 0, 'surprise': 0, 'neutral': 0
            }
        
        results.append({
            'time': (start, end),
            'text': text,
            'emotions': averaged
        })
    return results

def extract_audio_from_video(video_path, output_audio="temp.wav"):
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(output_audio)
    return output_audio




if __name__=="__main__":
    # Main execution
    start_time = time()
    video_file = os.path.join(os.path.dirname(__file__), "sample_video.mp4")  # Use absolute path based on script location
    segments = transcribe_audio(video_file)
    frames = extract_frames(video_file, segments)
    emotions = detect_emotions(frames)
    end_time = time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
    # Output results
    for entry in emotions:
        print(f"[{entry['time'][0]:.2f}s - {entry['time'][1]:.2f}s] {entry['text']} --> Emotions: {entry['emotions']}")
