import unittest
from app.processing.operations.base import OperationContext
from app.processing.operations.text_overlay import apply_text, _wrap_text, _position_to_xy, _align_multiline_text


class TestTextOverlayOperation(unittest.TestCase):
    def setUp(self):
        self.ctx = OperationContext(
            duration_seconds=10.0,
            video_width=1920,
            video_height=1080,
        )

    def test_text_overlay_full_settings(self):
        op = {
            "type": "text",
            "text": "When they return home\nafter honeymoon.....",
            "font": "Impact",
            "fontSize": 80,
            "fontWeight": "Bold",
            "color": "Yellow",
            "enableOutline": True,
            "outlineColor": "Black",
            "outlineThickness": 5,
            "enableShadow": True,
            "shadowBlur": 2,
            "shadowColor": "Black",
            "align": "Center",
            "posX": "Center",
            "posY": "Top 10%",
            "autoWrap": True,
            "maxWidth": 90,
        }
        res = apply_text(op, self.ctx)

        self.assertEqual(len(res.video_filters), 1)
        self.assertIn("overlay=0:0", res.video_filters[0])
        self.assertEqual(len(res.extra_inputs), 1)
        self.assertTrue(res.extra_inputs[0].endswith(".png"))

    def test_multiline_center_alignment(self):
        text = "Click the link below to\nwatch full video"
        aligned = _align_multiline_text(text, "Center")
        lines = aligned.splitlines()
        self.assertTrue(lines[1].startswith(" "))

    def test_text_wrap(self):
        long_line = "This is a very long line of text that should be wrapped automatically by the software to fit within the specified maximum percentage of video width."
        wrapped = _wrap_text(long_line, auto_wrap=True, max_width_pct=90, font_size=80, video_width=1920)
        self.assertIn("\n", wrapped)

    def test_position_mapping(self):
        x, y = _position_to_xy("Center", "Top 10%")
        self.assertEqual(x, "(w-text_w)/2")
        self.assertEqual(y, "h*0.10")

        x2, y2 = _position_to_xy("Left (5%)", "Bottom 20%")
        self.assertEqual(x2, "w*0.05")
        self.assertEqual(y2, "h*0.80-text_h")

    def test_legacy_backward_compatibility(self):
        op = {
            "type": "text",
            "text": "Legacy Sample",
            "fontSize": 42,
            "position": "center",
        }
        res = apply_text(op, self.ctx)
        self.assertEqual(len(res.video_filters), 1)
        self.assertIn("overlay=0:0", res.video_filters[0])
        self.assertEqual(len(res.extra_inputs), 1)

    def test_text_timestamps(self):
        op = {
            "type": "text",
            "text": "Timestamp Test",
            "startTime": 2.5,
            "endTime": 6.0,
        }
        res = apply_text(op, self.ctx)
        self.assertIn("enable='between(t\\,2.5\\,6.0)'", res.video_filters[0])

        op2 = {
            "type": "text",
            "text": "Start only",
            "startTime": 3.0,
            "endTime": 0.0,
        }
        res2 = apply_text(op2, self.ctx)
        self.assertIn("enable='gte(t\\,3.0)'", res2.video_filters[0])


    def test_text_display_modes(self):
        # Start mode
        op_start = {"type": "text", "text": "Start mode", "display_mode": "start", "start_duration": 3.0}
        res1 = apply_text(op_start, self.ctx)
        self.assertIn("enable='between(t\\,0\\,3.0)'", res1.video_filters[0])

        # End mode (video duration = 10.0s, end duration = 3.0s => start at 7.0s)
        op_end = {"type": "text", "text": "End mode", "display_mode": "end", "end_duration": 3.0}
        res2 = apply_text(op_end, self.ctx)
        self.assertIn("enable='gte(t\\,7.0)'", res2.video_filters[0])

        # Both mode
        op_both = {"type": "text", "text": "Both mode", "display_mode": "both", "start_duration": 2.0, "end_duration": 3.0}
        res3 = apply_text(op_both, self.ctx)
        self.assertIn("enable='between(t\\,0\\,2.0)+gte(t\\,7.0)'", res3.video_filters[0])


if __name__ == "__main__":
    unittest.main()
