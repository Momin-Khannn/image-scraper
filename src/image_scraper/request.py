"""Parse public GitHub issue scrape requests."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from .scraper import normalize_url


MAX_ALLOWED_IMAGES = 200
DEFAULT_MAX_IMAGES = 50


def parse_issue_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in body.splitlines():
        heading = re.match(r"^###\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1).strip().lower()
            sections[current] = []
            continue
        if current:
            sections[current].append(line)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def section_value(sections: dict[str, str], *names: str, default: str = "") -> str:
    normalized_names = {name.lower() for name in names}
    for key, value in sections.items():
        if key in normalized_names:
            return value.strip()
    return default


def parse_max_images(raw_value: str) -> int:
    match = re.search(r"\d+", raw_value or "")
    if not match:
        return DEFAULT_MAX_IMAGES
    value = int(match.group(0))
    return min(max(value, 1), MAX_ALLOWED_IMAGES)


def parse_all_shopify_images(raw_value: str) -> bool:
    normalized = (raw_value or "").strip().lower()
    return any(marker in normalized for marker in ("all images", "all product", "yes", "true", "every"))


def parse_event(event: dict[str, Any]) -> dict[str, Any]:
    issue = event.get("issue") or {}
    body = str(issue.get("body") or "")
    sections = parse_issue_sections(body)
    target_url = normalize_url(section_value(sections, "Website URL", "Target URL", "URL"))
    max_images = parse_max_images(section_value(sections, "Maximum images", "Max images"))
    all_shopify_images = parse_all_shopify_images(
        section_value(sections, "Shopify image mode", "All Shopify images")
    )
    issue_number = int(issue.get("number") or 0)
    user = issue.get("user") or {}

    return {
        "issue_number": issue_number,
        "issue_html_url": issue.get("html_url") or "",
        "requester": user.get("login") or "unknown",
        "target_url": target_url,
        "max_images": max_images,
        "all_shopify_images": all_shopify_images,
        "image_selection": section_value(sections, "Image selection"),
        "webhook_url": section_value(sections, "Webhook URL"),
        "gallery_subdir": f"requests/issue-{issue_number}",
    }


def write_github_outputs(path: str | Path, data: dict[str, Any]) -> None:
    output_path = Path(path)
    with output_path.open("a", encoding="utf-8") as output:
        for key, value in data.items():
            output.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="image-scraper-request",
        description="Parse a GitHub issue event into scraper inputs.",
    )
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH"), help="Path to the GitHub event JSON")
    parser.add_argument("--output-json", help="Optional path for parsed request JSON")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"), help="Optional GitHub output file path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.event_path:
        parser.error("--event-path is required")

    event = json.loads(Path(args.event_path).read_text(encoding="utf-8-sig"))
    request = parse_event(event)

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(request, indent=2), encoding="utf-8")
    if args.github_output:
        write_github_outputs(args.github_output, request)

    print(json.dumps(request, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
