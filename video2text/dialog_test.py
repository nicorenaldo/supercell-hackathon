import unittest
from dialog_input_dcl import DialogInputDCL

class TestDialogInputDCL(unittest.TestCase):
    def test_get_dialog_input(self):
        dialog_input = DialogInputDCL(video_file="sample_video.mp4")
        self.assertEqual(dialog_input.video_file, "sample_video.mp4")

if __name__ == "__main__":
    unittest.main()
