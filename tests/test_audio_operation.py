import os
import unittest
from app.processing.operations.base import OperationContext
from app.processing.operations.audio import apply_audio, _resolve_audio_assets
from app.processing.plan_builder import build_ffmpeg_plan
from app.processing.probe import MediaInfo


class TestAudioOperation(unittest.TestCase):
    def setUp(self):
        self.ctx = OperationContext(
            duration_seconds=10.0,
            video_width=1920,
            video_height=1080,
        )

    def test_keep_original_false_enforcement(self):
        script = {
            "name": "Mute Audio Test",
            "keepOriginal": False,
            "operations": [],
        }
        probe = MediaInfo(
            duration_seconds=10.0,
            video_width=1280,
            video_height=720,
            has_video=True,
            has_audio=True,
        )
        plan = build_ffmpeg_plan("input.mp4", "output.mp4", script, probe)
        self.assertIn("-an", plan.args)
        self.assertNotIn("0:a?", plan.args)

    def test_audio_mixing_and_video_duration_trimming(self):
        op = {
            "type": "audio",
            "mode": "background-music",
            "source_type": "file",
            "assetPath": "music.mp3",
            "original_volume": 0.8,
            "background_volume": 0.25,
        }
        res = apply_audio(op, self.ctx)

        # Verifies asset volume scaling and video duration trimming (10.0s)
        self.assertIn("volume=0.25", res.audio_filters)
        self.assertIn("atrim=0:10.0", res.audio_filters)

        script = {
            "name": "BG Music Script",
            "keepOriginal": True,
            "operations": [op],
        }
        probe = MediaInfo(
            duration_seconds=10.0,
            video_width=1280,
            video_height=720,
            has_video=True,
            has_audio=True,
        )
        plan = build_ffmpeg_plan("input.mp4", "output.mp4", script, probe)
        self.assertIn("[0:a]volume=0.8[a_orig]", plan.command)
        self.assertIn("amix=inputs=2:duration=first", plan.command)

    def test_audio_segment_trimming(self):
        op = {
            "type": "audio",
            "mode": "replace-audio",
            "source_type": "file",
            "assetPath": "music.mp3",
            "use_segment": True,
            "segment_start": 5.0,
            "segment_end": 15.0,
        }
        res = apply_audio(op, self.ctx)
        self.assertIn("atrim=start=5.0:end=15.0", res.audio_filters)
        self.assertIn("asetpts=PTS-STARTPTS", res.audio_filters)

    def test_folder_mode_resolution(self):
        # Create a temp test directory with 2 dummy files
        test_dir = os.path.abspath("temp_test_audio_folder")
        os.makedirs(test_dir, exist_ok=True)
        f1 = os.path.join(test_dir, "track1.mp3")
        f2 = os.path.join(test_dir, "track2.wav")
        open(f1, "w").close()
        open(f2, "w").close()

        try:
            # Single mode returns 1 file when exact file path is passed
            single_res = _resolve_audio_assets(f1, source_type="file", folder_mode="single")
            self.assertEqual(len(single_res), 1)
            self.assertEqual(single_res[0], f1)

            # Playlist / folder mode returns all audio files in the folder
            merge_res = _resolve_audio_assets(test_dir, source_type="folder", folder_mode="merge")
            self.assertEqual(len(merge_res), 2)
            self.assertTrue(f1 in merge_res and f2 in merge_res)
        finally:
            os.remove(f1)
            os.remove(f2)
            os.rmdir(test_dir)


if __name__ == "__main__":
    unittest.main()
