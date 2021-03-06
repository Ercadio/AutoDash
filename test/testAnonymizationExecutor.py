#!/usr/bin/env python3
import unittest
import os
import shutil

from src.data.VideoItem import VideoItem
from src.data.MetaDataItem import MetaDataItem
from src.executor.FaceBlurrer import FaceBlurrer
from numpy.testing import assert_array_equal, assert_raises

class TestAnonymizationExecutor(unittest.TestCase):
    TEST_DIR = os.path.join(os.getcwd(), "anontest")
    TEST_FILE = "test.mp4"
    DATASET_PATH = "src/lib/anonymization/dataset/input"
    ACCEPTED_FILE_EXTENSION = ".mp4"
    TEST_FILE_PATH = os.path.join(TEST_DIR, TEST_FILE)

    def setUp(self):
        # Create test directory and copy one of the test videos from the anonymization repo into it
        if not os.path.exists(self.TEST_DIR):
            os.mkdir(self.TEST_DIR)

    def tearDown(self):
        # Delete test directory
        if os.path.exists(self.TEST_DIR):
            shutil.rmtree(self.TEST_DIR)

    def test_compiles(self):
        self.assertEqual(True, True)

    """
    # Test that the executor works with a single video
    def test_face_blurrer_single(self):
        # Copy video to test directory
        shutil.copy2(os.path.join(os.getcwd(), self.DATASET_PATH, "man_face.mp4"), self.TEST_FILE_PATH)
        video = VideoItem(filepath = self.TEST_FILE_PATH, metadata=None)

        original_data = video.npy

        # Running the face blurrer should overwrite the input file
        face_blurrer = FaceBlurrer()
        new_data = face_blurrer.run(video)

        # Now we check that the video data has changed
        assert_raises(AssertionError, assert_array_equal, original_data, new_data)
    """

if __name__ == '__main__':
    unittest.main()
