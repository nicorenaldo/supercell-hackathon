import whisper
import cv2
import os
from moviepy import VideoFileClip
from deepface import DeepFace
from time import sleep, time

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

# Step 2: Extract frame at midpoint of each transcript segment
def extract_frames(video_path, segments, output_folder='frames'):
    os.makedirs(output_folder, exist_ok=True)
    video = cv2.VideoCapture(video_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    
    frame_data = []
    
    for i, seg in enumerate(segments):
        timestamp = (seg['start'] + seg['end']) / 2
        frame_num = int(timestamp * fps)
        video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = video.read()
        if ret:
            path = f"{output_folder}/frame_{i}.jpg"
            cv2.imwrite(path, frame)
            frame_data.append((path, seg['start'], seg['end'], seg['text']))
    
    video.release()
    return frame_data

# Step 3: Analyze emotion
def detect_emotions(frames):
    results = []
    for frame_path, start, end, text in frames:
        try:
            analysis = DeepFace.analyze(img_path=frame_path, actions=['emotion'], enforce_detection=False)
            emotion = analysis[0]['dominant_emotion']
        except Exception as e:
            emotion = "error"
        results.append({'time': (start, end), 'text': text, 'emotion': emotion})
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
        print(f"[{entry['time'][0]:.2f}s - {entry['time'][1]:.2f}s] {entry['text']} --> Emotion: {entry['emotion']}")
