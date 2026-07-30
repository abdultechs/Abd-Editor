import unittest
from app.processing.operations.base import OperationContext
from app.processing.operations.fade import apply_fade
from app.processing.plan_builder import build_ffmpeg_plan
from app.processing.probe import MediaInfo


class TestFadeOperation(unittest.TestCase):
    def setUp(self):
        self.ctx = OperationContext(
            duration_seconds=10.0,
            video_width=1920,
            video_height=1080,
        )

    def test_fade_both_video_and_audio(self):
        op = {
            "type": "fade",
            "fade_type": "both",
            "target": "both",
            "fade_in_duration": 1.5,
            "fade_out_duration": 2.0,
            "color": "black",
        }
        res = apply_fade(op, self.ctx)

        self.assertEqual(len(res.video_filters), 2)
        self.assertEqual(len(res.audio_filters), 2)

        # Video filters
        self.assertIn("fade=t=in:st=0.0:d=1.5:color=black", res.video_filters)
        self.assertIn("fade=t=out:st=8.0:d=2.0:color=black", res.video_filters)

        # Audio filters
        self.assertIn("afade=t=in:st=0.0:d=1.5", res.audio_filters)
        self.assertIn("afade=t=out:st=8.0:d=2.0", res.audio_filters)

    def test_fade_video_only(self):
        op = {
            "type": "fade",
            "fade_type": "in",
            "target": "video",
            "fade_in_duration": 1.0,
        }
        res = apply_fade(op, self.ctx)

        self.assertEqual(len(res.video_filters), 1)
        self.assertEqual(len(res.audio_filters), 0)
        self.assertEqual(res.video_filters[0], "fade=t=in:st=0.0:d=1.0:color=black")

    def test_fade_audio_only(self):
        op = {
            "type": "fade",
            "fade_type": "out",
            "target": "audio",
            "fade_out_duration": 2.5,
        }
        res = apply_fade(op, self.ctx)

        self.assertEqual(len(res.video_filters), 0)
        self.assertEqual(len(res.audio_filters), 1)
        # 10.0 - 2.5 = 7.5
        self.assertEqual(res.audio_filters[0], "afade=t=out:st=7.5:d=2.5")

    def test_fade_custom_out_start_timestamp(self):
        op = {
            "type": "fade",
            "fade_type": "out",
            "target": "both",
            "fade_out_start": 5.0,
            "fade_out_duration": 2.0,
        }
        res = apply_fade(op, self.ctx)
        self.assertIn("fade=t=out:st=5.0:d=2.0:color=black", res.video_filters)
        self.assertIn("afade=t=out:st=5.0:d=2.0", res.audio_filters)

    def test_plan_builder_integration(self):
        script = {
            "name": "Fade Test Script",
            "keepOriginal": True,
            "operations": [
                {
                    "type": "fade",
                    "fade_type": "both",
                    "target": "both",
                    "fade_in_duration": 1.0,
                    "fade_out_duration": 1.0,
                }
            ],
        }
        probe = MediaInfo(
            duration_seconds=15.0,
            video_width=1280,
            video_height=720,
            has_video=True,
            has_audio=True,
        )

        plan = build_ffmpeg_plan("input.mp4", "output.mp4", script, probe)
        self.assertIn("fade=t=in", plan.command)
        self.assertIn("fade=t=out:st=14.0", plan.command)
        self.assertIn("afade=t=in", plan.command)
        self.assertIn("afade=t=out:st=14.0", plan.command)


if __name__ == "__main__":
    unittest.main()
