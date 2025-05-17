import unittest
from dialog_input_dcl import DialogInputDCL
from time import time

class TestDialogInputDCL(unittest.TestCase):
    def test_get_dialog_input(self):
        start_time = time()
        dialog_input = DialogInputDCL(video_file="sample_video.mp4",
                                      frames_per_sentence=3)
        end_time = time()
        print(f"Time taken: {end_time - start_time} seconds")
        self.assertEqual(dialog_input.video_file, "sample_video.mp4")



if __name__ == "__main__":
    unittest.main()
