from utils import transcribe_audio, extract_frames, detect_emotions
import os

class Emotions:
    def __init__(self, emotion_probs: dict):
        self.angry: float = emotion_probs['angry']
        self.disgust: float = emotion_probs['disgust']
        self.fear: float = emotion_probs['fear']
        self.happy: float = emotion_probs['happy']
        self.sad: float = emotion_probs['sad']
        self.surprise: float = emotion_probs['surprise']
        self.neutral: float = emotion_probs['neutral']

class DialogInputDCL:
    def __init__(self,
                 video_file: str = "sample_video.mp4",
                 frames_per_sentence: int = 3
                 ):
        self.emotions: list[Emotions] = []
        self.sentences: list[str] = []
        self.mid_timestamps: list[float] = []
        self.start_times: list[float] = []
        self.end_times: list[float] = []
        self.video_file: str = video_file
        self.frames_per_sentence: int = frames_per_sentence
        self.get_dialog_input(video_file)


    def get_dialog_input(self, file_path: str):
        if not os.path.isabs(file_path):
            # If relative path is provided, make it absolute relative to script location
            video_file = os.path.join(os.path.dirname(__file__), file_path)
        else:
            video_file = file_path

        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file not found: {video_file}")
        # Transcribe audio. This also determines the timestamps of the sentences.
        segments = transcribe_audio(video_file)
        # Extract frames from the segments.
        frames = extract_frames(video_file, segments, self.frames_per_sentence)
        # Detect emotions from the frames. These are probabilities, stored in Emotions objects.
        emotions = detect_emotions(frames)

        for entry in emotions:
            self.emotions.append(Emotions(entry['emotions']))
            self.sentences.append(entry['text'])
            self.mid_timestamps.append((entry['time'][0] + entry['time'][1]) / 2)
            self.start_times.append(entry['time'][0])
            self.end_times.append(entry['time'][1])


