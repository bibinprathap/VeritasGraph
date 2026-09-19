"""Generate the negative-path fixtures the E2E suite needs.

Kept as a script rather than checked-in binaries so the inputs are auditable:
you can see exactly what "corrupt" and "image-only" mean here.
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).parent


def main() -> int:
    (HERE / "sample.txt").write_text(
        "This is a plain text file, not a PDF. The uploader must reject it.\n",
        encoding="utf-8",
    )

    # Valid header, truncated body: passes a sniff test, fails to parse.
    (HERE / "corrupt.pdf").write_bytes(
        b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EO"
    )

    (HERE / "empty.pdf").write_bytes(b"")

    # Born-image sheet: one page, a single raster, zero extractable text.
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 300))
    pix.set_rect(pix.irect, (235, 235, 235))
    page.insert_image(pymupdf.Rect(100, 150, 500, 450), pixmap=pix)
    doc.save(HERE / "scanned.pdf")
    doc.close()

    for name in ("sample.txt", "corrupt.pdf", "empty.pdf", "scanned.pdf"):
        print(f"wrote {HERE / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
