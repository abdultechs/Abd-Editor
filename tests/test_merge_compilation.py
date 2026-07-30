import unittest
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.processing.operations.base import OperationContext
from app.processing.operations.merge import apply_merge
from app.processing.plan_builder import build_ffmpeg_plan
from app.processing.probe import MediaInfo


class TestMergeCompilation(unittest.TestCase):
    def test_apply_merge_folder_compilation_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            v1 = os.path.join(tmpdir, "vid1.mp4")
            v2 = os.path.join(tmpdir, "vid2.mp4")
            open(v1, "w").close()
            open(v2, "w").close()

            ctx = OperationContext(
                duration_seconds=10.0,
                video_width=1280,
                video_height=720,
                input_path=v1,
            )
            op = {"type": "merge", "mode": "folder_compilation"}
            res = apply_merge(op, ctx)
            self.assertTrue(len(res.extra_inputs) >= 1)

    def test_build_ffmpeg_plan_compilation_concat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            v1 = os.path.join(tmpdir, "vid1.mp4")
            open(v1, "w").close()

            dummy_probe = MediaInfo(
                duration_seconds=5.0,
                video_width=1280,
                video_height=720,
                has_audio=True,
                has_video=True,
            )
            script = {
                "name": "Compilation Test",
                "operations": [{"type": "merge", "mode": "folder_compilation"}],
            }
            plan = build_ffmpeg_plan(
                input_path=v1,
                output_path=os.path.join(tmpdir, "out.mp4"),
                script=script,
                probe=dummy_probe,
            )
            self.assertIn("concat=n=", plan.command)


if __name__ == "__main__":
    unittest.main()
