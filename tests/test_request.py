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
            "html_url": "https://github.com/Momin-Khannn/image-scraper/issues/42",
            "body": """### Website URL

example.com

### Maximum images

30

### Shopify image mode

All images per product

### Image selection

1-5, 10-

### Webhook URL

https://my-database.com/api/ingest

### Public permission

- [x] I confirm I am allowed to scrape and publicly publish images from this URL.""",
            "user": {"login": "visitor"},
        }
    }

    request = parse_event(event)

    assert request["issue_number"] == 42
    assert request["target_url"] == "https://example.com"
    assert request["max_images"] == 30
    assert request["all_shopify_images"] is True
    assert request["image_selection"] == "1-5, 10-"
    assert request["webhook_url"] == "https://my-database.com/api/ingest"
    assert request["gallery_subdir"] == "requests/issue-42"
