import unittest
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.processing.operations.base import OperationContext
from app.processing.operations.zoom import apply_zoom
from app.processing.operations.border import apply_border
from app.processing.operations.image_overlay import apply_image_overlay
from app.processing.operations.text_overlay import apply_text
from app.processing.plan_builder import build_ffmpeg_plan
from app.processing.probe import MediaInfo


class TestNewOperations(unittest.TestCase):
    def setUp(self):
        self.ctx = OperationContext(
            duration_seconds=10.0,
            video_width=1920,
            video_height=1080,
        )

    def test_zoom_crop_top_bottom_operation(self):
        op = {"type": "zoom", "zoom_factor": 1.20, "mode": "crop_top_bottom"}
        res = apply_zoom(op, self.ctx)
        self.assertEqual(len(res.video_filters), 1)
        self.assertIn("crop=1920:900", res.video_filters[0])
        self.assertIn("scale=1920:1080", res.video_filters[0])

    def test_solid_color_side_border_operation(self):
        op = {
            "type": "border",
            "thickness": 25,
            "color": "Solid Deep Purple",
            "mode": "sides_only",
            "enable_inner_border": True,
            "inner_thickness": 4,
            "inner_color": "Solid White",
        }
        res = apply_border(op, self.ctx)
        self.assertEqual(len(res.video_filters), 1)
        self.assertIn("pad=w=iw+8:h=ih:x=4:y=0:color=white", res.video_filters[0])
        self.assertIn("pad=w=iw+50:h=ih:x=25:y=0:color=0x7C3AED", res.video_filters[0])

    def test_image_overlay_custom_percentage_position(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            op = {
                "type": "image_overlay",
                "image_path": tmp_path,
                "opacity": 0.5,
                "scale_pct": 25,
                "posX": "Custom Position (%)",
                "posY": "Custom Position (%)",
                "posX_pct": 75.0,
                "posY_pct": 85.0,
            }
            res = apply_image_overlay(op, self.ctx)
            self.assertEqual(len(res.extra_inputs), 1)
            self.assertEqual(res.extra_inputs[0], tmp_path)
            self.assertIn("overlay=(main_w-overlay_w)*0.750:(main_h-overlay_h)*0.850", res.video_filters[0])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_text_opacity(self):
        op = {
            "type": "text",
            "text": "Watermark",
            "opacity": 0.4,
            "color": "White",
        }
        res = apply_text(op, self.ctx)
        self.assertEqual(len(res.video_filters), 1)
        self.assertIn("overlay=0:0", res.video_filters[0])
        self.assertEqual(len(res.extra_inputs), 1)

    def test_plan_builder_with_all_new_operations(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            img_path = tmp_img.name

        try:
            probe = MediaInfo(10.0, 1920, 1080, True, True)
            script = {
                "name": "Full Feature Test Script",
                "keepOriginal": True,
                "operations": [
                    {"type": "zoom", "zoom_factor": 1.15, "mode": "crop_top_bottom"},
                    {"type": "border", "thickness": 30, "color": "Solid Electric Blue", "mode": "sides_only"},
                    {"type": "image_overlay", "image_path": img_path, "opacity": 0.6, "scale_pct": 30},
                    {"type": "text", "text": "ECO GADGETS", "opacity": 0.5},
                ],
            }
            plan = build_ffmpeg_plan("input.mp4", "output.mp4", script, probe)
            self.assertIn("crop=1920:938", plan.command)
            self.assertIn("pad=w=iw+60:h=ih:x=30:y=0:color=0x2563EB", plan.command)
            self.assertIn("scale=576:-1:force_original_aspect_ratio=decrease,setsar=1", plan.command)
            self.assertIn("overlay=0:0", plan.command)
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)


if __name__ == "__main__":
    unittest.main()
