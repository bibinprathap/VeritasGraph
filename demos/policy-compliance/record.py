"""
Record an animated GIF of the policy-compliance demo using Playwright + Pillow.

Pipeline:
  1. Spin up a tiny http.server serving demos/policy-compliance/.
  2. Launch headless Chromium via Playwright at a fixed 1280x720 viewport.
  3. While the demo animation runs (~12 s), capture a PNG screenshot every
     ~150 ms.
  4. Stitch the PNGs into demo.gif using Pillow (no ffmpeg required).
  5. Also leave the raw frames in frames/ for inspection.

Run:
    /home/sijo/VeritasGraph/.venv/bin/python demos/policy-compliance/record.py
"""

from __future__ import annotations

import contextlib
import http.server
import io
import os
import socketserver
import sys
import threading
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

VIEWPORT = {"width": 1280, "height": 720}
TOTAL_DURATION_S = 13.0
FRAME_INTERVAL_S = 0.15
GIF_FRAME_MS = 100   # delay between gif frames (≈10 fps)
PORT = 0             # let OS pick a free port


# --------------------------------------------------------------------------- #
# Tiny static file server (background thread)
# --------------------------------------------------------------------------- #
class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **kw):  # silence
        pass


@contextlib.contextmanager
def serve(directory: Path):
    os.chdir(directory)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), _Quiet)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield port
    finally:
        httpd.shutdown()


# --------------------------------------------------------------------------- #
# Capture frames
# --------------------------------------------------------------------------- #
def capture_frames(url: str, frames_dir: Path) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.png"):
        old.unlink()

    paths: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        start = time.time()
        i = 0
        while time.time() - start < TOTAL_DURATION_S:
            p = frames_dir / f"frame_{i:04d}.png"
            page.screenshot(path=str(p), full_page=False)
            paths.append(p)
            i += 1
            time.sleep(FRAME_INTERVAL_S)

            # Early exit once the demo signals done AND we've captured a tail
            try:
                if page.evaluate("() => window.__demoDone === true"):
                    if (time.time() - start) > 8:
                        # capture ~1.2 s tail
                        tail_end = time.time() + 1.2
                        while time.time() < tail_end:
                            p = frames_dir / f"frame_{i:04d}.png"
                            page.screenshot(path=str(p), full_page=False)
                            paths.append(p)
                            i += 1
                            time.sleep(FRAME_INTERVAL_S)
                        break
            except Exception:
                pass

        browser.close()

    return paths


# --------------------------------------------------------------------------- #
# Stitch GIF
# --------------------------------------------------------------------------- #
def build_gif(frames: list[Path], out_path: Path,
              max_width: int = 960) -> None:
    images: list[Image.Image] = []
    for fp in frames:
        img = Image.open(fp).convert("RGB")
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize(
                (max_width, int(img.height * ratio)),
                Image.Resampling.LANCZOS,
            )
        # Quantise to reduce file size (256-colour palette)
        images.append(img.quantize(colors=128, method=Image.Quantize.MEDIANCUT))

    if not images:
        raise RuntimeError("No frames captured.")

    images[0].save(
        out_path,
        save_all=True,
        append_images=images[1:],
        duration=GIF_FRAME_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )


def main() -> int:
    print(f"[demo] root              : {ROOT}")
    print(f"[demo] static directory  : {HERE}")

    frames_dir = HERE / "frames"
    gif_path   = HERE / "demo.gif"

    with serve(HERE) as port:
        url = f"http://127.0.0.1:{port}/index.html"
        print(f"[demo] serving           : {url}")
        print(f"[demo] capturing frames  …")
        frames = capture_frames(url, frames_dir)

    print(f"[demo] frames captured   : {len(frames)}")
    print(f"[demo] stitching GIF     …")
    build_gif(frames, gif_path)

    size_kb = gif_path.stat().st_size / 1024
    print(f"[demo] wrote             : {gif_path.relative_to(ROOT)} "
          f"({size_kb:,.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
