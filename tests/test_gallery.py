from __future__ import annotations

import json
from pathlib import Path

from image_scraper.gallery import build_public_gallery


def test_build_public_gallery_copies_images_and_writes_latest_page(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    output_dir = tmp_path / "output"
    site_dir = tmp_path / "site"
    docs_dir.mkdir()
    output_dir.mkdir()
    (docs_dir / "index.html").write_text("<html>Project</html>", encoding="utf-8")
    (output_dir / "one.jpg").write_bytes(b"image")
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "target_url": "https://example.com",
                "strategy": "html",
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:00:01+00:00",
                "downloaded_count": 1,
                "warnings": [],
                "images": [
                    {
                        "source_url": "https://example.com/one.jpg",
                        "filename": "one.jpg",
                        "relative_path": "one.jpg",
                        "bytes": 5,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = build_public_gallery(docs_dir, output_dir, site_dir)

    assert report["published_images"] == 1
    assert (site_dir / "index.html").exists()
    assert (site_dir / "latest" / "index.html").exists()
    assert (site_dir / "latest" / "manifest.json").exists()
    assert (site_dir / "latest" / "images" / "one.jpg").read_bytes() == b"image"
    latest_html = (site_dir / "latest" / "index.html").read_text(encoding="utf-8")
    assert "Latest Scrape Gallery" in latest_html
    assert "https://example.com/one.jpg" in latest_html
