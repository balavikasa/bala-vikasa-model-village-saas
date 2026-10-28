"""The browser icon must preserve the emblem without an opaque canvas."""
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class TransparentFaviconTests(unittest.TestCase):
    def assert_icon(self, image, size):
        rgba = image.convert('RGBA')
        self.assertEqual(rgba.size, (size, size))
        for point in [(0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)]:
            self.assertEqual(rgba.getpixel(point)[3], 0, 'Favicon still has an opaque background')
        pixels = [rgba.getpixel((x, y)) for y in range(size) for x in range(size)]
        self.assertGreater(sum(a == 0 for _, _, _, a in pixels), size * size // 4)
        self.assertTrue(any(r > 150 and r > g * 1.4 and r > b * 1.4 and a > 150 for r, g, b, a in pixels), 'Original red emblem missing')
        self.assertTrue(any(abs(r-g) < 15 and abs(g-b) < 15 and 70 < r < 210 and a > 150 for r, g, b, a in pixels), 'Original grey emblem missing')

    def test_png_favicons_are_transparent(self):
        for size in (16, 32, 64):
            with self.subTest(size=size), Image.open(ROOT / f'app/static/icons/favicon-{size}.png') as image:
                self.assert_icon(image, size)

    def test_ico_sizes_are_transparent(self):
        with Image.open(ROOT / 'app/static/icons/favicon.ico') as image:
            for size in (16, 32, 64):
                with self.subTest(size=size):
                    self.assert_icon(image.ico.getimage((size, size)), size)


if __name__ == '__main__':
    unittest.main(verbosity=2)
