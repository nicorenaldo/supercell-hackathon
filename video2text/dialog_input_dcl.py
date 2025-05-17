from prelimm import transcribe_audio, extract_frames, detect_emotions
import os

class DialogInputDCL:
    def __init__(self,
                 video_file: str = "sample_video.mp4",
                 ):
        self.emotions: list[str] = []
        self.sentences: list[str] = []
        self.mid_timestamps: list[float] = []
        self.start_times: list[float] = []
        self.end_times: list[float] = []
        self.video_file: str = video_file
        self.get_dialog_input(video_file)


    def get_dialog_input(self, file_path: str):
        if not os.path.isabs(file_path):
            # If relative path is provided, make it absolute relative to script location
            video_file = os.path.join(os.path.dirname(__file__), file_path)
        else:
            video_file = file_path

        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file not found: {video_file}")

        segments = transcribe_audio(video_file)
        frames = extract_frames(video_file, segments)
        emotions = detect_emotions(frames)

        for entry in emotions:
            self.emotions.append(entry['emotion'])
            self.sentences.append(entry['text'])
            self.mid_timestamps.append((entry['time'][0] + entry['time'][1]) / 2)
            self.start_times.append(entry['time'][0])
            self.end_times.append(entry['time'][1])


