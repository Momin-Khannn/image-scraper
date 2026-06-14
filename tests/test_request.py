from __future__ import annotations

from image_scraper.request import parse_event, parse_issue_sections


def test_parse_issue_sections_reads_markdown_headings():
    body = """### Website URL

example.com/products

### Maximum images

25
"""

    sections = parse_issue_sections(body)

    assert sections["website url"] == "example.com/products"
    assert sections["maximum images"] == "25"


def test_parse_event_normalizes_inputs_and_caps_max_images():
    event = {
        "issue": {
            "number": 42,
            "html_url": "https://github.com/Momin-Khannn/image-scraper-actions/issues/42",
            "body": """### Website URL

example.com

### Maximum images

999

### Shopify image mode

All images per product
""",
            "user": {"login": "visitor"},
        }
    }

    request = parse_event(event)

    assert request["issue_number"] == 42
    assert request["target_url"] == "https://example.com"
    assert request["max_images"] == 200
    assert request["all_shopify_images"] is True
    assert request["gallery_subdir"] == "requests/issue-42"
