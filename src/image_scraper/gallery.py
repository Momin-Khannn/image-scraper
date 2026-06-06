"""Build a public static gallery from scraper output."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}


def read_manifest(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return {
            "target_url": "",
            "strategy": "unknown",
            "downloaded_count": 0,
            "images": [],
            "warnings": ["No manifest.json was found for the latest run."],
        }
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def image_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("images", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def copy_docs(docs_dir: Path, site_dir: Path) -> None:
    if site_dir.exists():
        shutil.rmtree(site_dir)
    shutil.copytree(docs_dir, site_dir)


def copy_gallery_images(output_dir: Path, images_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    images_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []

    for entry in image_entries(manifest):
        relative_path = entry.get("relative_path") or entry.get("filename")
        if not isinstance(relative_path, str):
            continue
        source = output_dir / relative_path
        if not source.exists() or source.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        destination = images_dir / source.name
        shutil.copy2(source, destination)
        copied.append({**entry, "gallery_path": f"images/{source.name}"})

    return copied


def render_gallery(manifest: dict[str, Any], copied_images: list[dict[str, Any]]) -> str:
    target_url = html.escape(str(manifest.get("target_url") or "No target URL"))
    strategy = html.escape(str(manifest.get("strategy") or "unknown"))
    started_at = html.escape(str(manifest.get("started_at") or "unknown"))
    finished_at = html.escape(str(manifest.get("finished_at") or "unknown"))
    downloaded_count = len(copied_images)
    warnings = manifest.get("warnings", [])
    warning_items = ""

    if isinstance(warnings, list) and warnings:
        warning_items = "".join(f"<li>{html.escape(str(warning))}</li>" for warning in warnings)

    cards = []
    for image in copied_images:
        gallery_path = html.escape(str(image["gallery_path"]))
        source_url = html.escape(str(image.get("source_url") or ""))
        filename = html.escape(str(image.get("filename") or Path(gallery_path).name))
        size = html.escape(str(image.get("bytes") or ""))
        meta = f"{size} bytes" if size else "Downloaded image"
        cards.append(
            f"""
            <article class="card">
              <a href="{gallery_path}" target="_blank" rel="noopener">
                <img src="{gallery_path}" alt="{filename}" loading="lazy">
              </a>
              <div class="card-body">
                <strong>{filename}</strong>
                <span>{html.escape(meta)}</span>
                <a href="{source_url}" target="_blank" rel="noopener">Source</a>
              </div>
            </article>
            """
        )

    gallery_body = "\n".join(cards)
    if not cards:
        gallery_body = """
        <div class="empty">
          <strong>No public images are available yet.</strong>
          <p>Run the Scrape Images workflow successfully to publish the latest gallery.</p>
        </div>
        """

    warning_block = ""
    if warning_items:
        warning_block = f"""
        <section class="notice">
          <strong>Run warnings</strong>
          <ul>{warning_items}</ul>
        </section>
        """

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Latest Scrape Gallery</title>
    <style>
      :root {{
        --ink: #18202a;
        --muted: #647083;
        --line: #d9e2ec;
        --paper: #f8fafc;
        --panel: #ffffff;
        --accent: #0f766e;
        --rose: #d45b6d;
      }}

      * {{ box-sizing: border-box; }}

      body {{
        margin: 0;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: var(--paper);
        letter-spacing: 0;
      }}

      header {{
        padding: 34px 20px 28px;
        border-bottom: 1px solid var(--line);
        background: #ffffff;
      }}

      .wrap {{
        width: min(1160px, 100%);
        margin: 0 auto;
      }}

      .back {{
        color: var(--accent);
        font-weight: 800;
        text-decoration: none;
      }}

      h1 {{
        margin: 18px 0 12px;
        font-size: clamp(2rem, 5vw, 4.4rem);
        line-height: 1;
        letter-spacing: 0;
      }}

      .summary {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 18px;
      }}

      .pill {{
        padding: 8px 11px;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: #ffffff;
        color: var(--muted);
        font-size: 0.92rem;
      }}

      main {{
        padding: 28px 20px 60px;
      }}

      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 16px;
      }}

      .card {{
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
      }}

      .card img {{
        width: 100%;
        aspect-ratio: 1 / 1;
        display: block;
        object-fit: contain;
        background: #eef3f8;
      }}

      .card-body {{
        display: grid;
        gap: 6px;
        padding: 12px;
      }}

      .card-body strong {{
        overflow-wrap: anywhere;
      }}

      .card-body span {{
        color: var(--muted);
        font-size: 0.9rem;
      }}

      .card-body a {{
        color: var(--accent);
        font-weight: 800;
      }}

      .notice,
      .empty {{
        margin-bottom: 20px;
        padding: 18px;
        border: 1px solid var(--line);
        border-left: 5px solid var(--rose);
        border-radius: 8px;
        background: #ffffff;
      }}

      .notice ul {{
        margin: 10px 0 0;
        padding-left: 20px;
      }}
    </style>
  </head>
  <body>
    <header>
      <div class="wrap">
        <a class="back" href="../">Back to project</a>
        <h1>Latest Scrape Gallery</h1>
        <p>Public static output from the most recent successful GitHub Actions scrape.</p>
        <div class="summary">
          <span class="pill">Target: {target_url}</span>
          <span class="pill">Strategy: {strategy}</span>
          <span class="pill">Images: {downloaded_count}</span>
          <span class="pill">Started: {started_at}</span>
          <span class="pill">Finished: {finished_at}</span>
        </div>
      </div>
    </header>
    <main>
      <div class="wrap">
        {warning_block}
        <section class="grid" aria-label="Scraped images">
          {gallery_body}
        </section>
      </div>
    </main>
  </body>
</html>
"""


def build_public_gallery(docs_dir: str | Path, output_dir: str | Path, site_dir: str | Path) -> dict[str, Any]:
    docs_path = Path(docs_dir)
    output_path = Path(output_dir)
    site_path = Path(site_dir)

    if not docs_path.exists():
        raise ValueError(f"docs_dir does not exist: {docs_path}")
    if not output_path.exists():
        raise ValueError(f"output_dir does not exist: {output_path}")

    copy_docs(docs_path, site_path)
    manifest = read_manifest(output_path)
    latest_dir = site_path / "latest"
    images_dir = latest_dir / "images"
    latest_dir.mkdir(parents=True, exist_ok=True)

    copied_images = copy_gallery_images(output_path, images_dir, manifest)
    (latest_dir / "index.html").write_text(render_gallery(manifest, copied_images), encoding="utf-8")
    (latest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "site_dir": str(site_path),
        "latest_dir": str(latest_dir),
        "published_images": len(copied_images),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="image-scraper-gallery",
        description="Build a GitHub Pages-ready public gallery from scraper output.",
    )
    parser.add_argument("--docs-dir", default="docs", help="Base static site directory. Default: docs")
    parser.add_argument("--output-dir", default="output", help="Scraper output directory. Default: output")
    parser.add_argument("--site-dir", default="site", help="Generated Pages site directory. Default: site")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = build_public_gallery(args.docs_dir, args.output_dir, args.site_dir)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
