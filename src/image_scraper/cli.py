"""Command line entry point for the image scraper."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .scraper import scrape_site


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="image-scraper",
        description="Scrape downloadable images from a website and write a manifest.",
    )
    parser.add_argument("target_url", help="Website URL to scrape.")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where images and manifest.json will be saved. Default: output",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=200,
        help="Maximum number of image candidates to download. Default: 200",
    )
    parser.add_argument(
        "--all-shopify-images",
        action="store_true",
        help="Download every Shopify product image instead of only each product's first image.",
    )
    parser.add_argument(
        "--image-selection",
        help="Pattern to select images (e.g. '1-5, 9-'). Default: all",
    )
    parser.add_argument(
        "--webhook-url",
        help="URL to POST results and base64 images to.",
    )
    parser.add_argument(
        "--report-json",
        help="Optional extra path where the run metadata JSON should also be written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = scrape_site(
            target_url=args.target_url,
            output_dir=Path(args.output_dir),
            max_images=args.max_images,
            all_shopify_images=args.all_shopify_images,
            image_selection=args.image_selection,
            webhook_url=args.webhook_url,
            report_json=Path(args.report_json) if args.report_json else None,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(report, indent=2))

    if report["downloaded_count"] == 0:
        print(
            "No images were downloaded. Check manifest.json for warnings and failures.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
