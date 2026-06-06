from __future__ import annotations

import json
from pathlib import Path

import pytest

from image_scraper.cli import main
from image_scraper.scraper import (
    extract_image_urls_from_html,
    filename_from_url,
    normalize_url,
    parse_srcset,
    scrape_site,
    unique_in_order,
)


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        json_data=None,
        content: bytes = b"",
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data
        self._content = content
        self.headers = headers or {}

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests_error(f"status {self.status_code}")

    def iter_content(self, chunk_size=8192):
        for index in range(0, len(self._content), chunk_size):
            yield self._content[index : index + chunk_size]


class requests_error(Exception):
    pass


class FakeSession:
    def __init__(self, responses: dict[str, list[FakeResponse]]):
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url, **kwargs):
        key = url
        self.calls.append(key)
        if key not in self.responses or not self.responses[key]:
            raise AssertionError(f"Unexpected URL: {url}")
        return self.responses[key].pop(0)


def test_normalize_url_adds_https_and_rejects_bad_scheme():
    assert normalize_url("example.com") == "https://example.com"
    assert normalize_url("http://example.com") == "http://example.com"

    with pytest.raises(ValueError):
        normalize_url("ftp://example.com")


def test_filename_from_url_sanitizes_and_uses_content_type_extension():
    filename = filename_from_url("https://example.com/images/My Product One", "image/webp", 3)
    assert filename == "My_Product_One.webp"


def test_unique_in_order_preserves_first_seen_values():
    assert unique_in_order(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_parse_srcset_picks_largest_width():
    srcset = "/small.jpg 320w, /large.jpg 1200w, /medium.jpg 800w"
    assert parse_srcset(srcset) == "/large.jpg"


def test_extract_image_urls_from_html_filters_duplicates_icons_and_css():
    html = """
    <html>
      <body>
        <img src="/photo.jpg">
        <img src="/photo.jpg">
        <img src="/visa.svg">
        <img srcset="/small.webp 300w, /large.webp 900w">
        <div style="background-image: url('/hero.png')"></div>
      </body>
    </html>
    """

    extracted = extract_image_urls_from_html(html, "https://example.com/products")

    assert extracted.urls == [
        "https://example.com/photo.jpg",
        "https://example.com/large.webp",
        "https://example.com/hero.png",
    ]


def test_scrape_site_uses_shopify_pagination_and_manifest(tmp_path: Path):
    session = FakeSession(
        {
            "https://shop.test/products.json": [
                FakeResponse(
                    json_data={
                        "products": [
                            {"images": [{"src": "//cdn.shop.test/a.jpg"}, {"src": "//cdn.shop.test/a-2.jpg"}]},
                            {"images": [{"src": "https://cdn.shop.test/b.png"}]},
                        ]
                    }
                ),
                FakeResponse(json_data={"products": []}),
            ],
            "https://cdn.shop.test/a.jpg": [
                FakeResponse(content=b"aaa", headers={"Content-Type": "image/jpeg"})
            ],
            "https://cdn.shop.test/b.png": [
                FakeResponse(content=b"bbb", headers={"Content-Type": "image/png"})
            ],
        }
    )

    report = scrape_site("shop.test", tmp_path, max_images=10, session=session)

    assert report["strategy"] == "shopify_api"
    assert report["downloaded_count"] == 2
    assert (tmp_path / "a.jpg").exists()
    assert (tmp_path / "b.png").exists()
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["downloaded_count"] == 2


def test_scrape_site_falls_back_to_html(tmp_path: Path):
    html = '<html><body><img src="/one.jpg"><img data-src="/two.webp"></body></html>'
    session = FakeSession(
        {
            "https://plain.test/products.json": [FakeResponse(status_code=404)],
            "https://plain.test": [FakeResponse(text=html)],
            "https://plain.test/one.jpg": [
                FakeResponse(content=b"one", headers={"Content-Type": "image/jpeg"})
            ],
            "https://plain.test/two.webp": [
                FakeResponse(content=b"two", headers={"Content-Type": "image/webp"})
            ],
        }
    )

    report = scrape_site("plain.test", tmp_path, max_images=2, session=session)

    assert report["strategy"] == "html"
    assert report["downloaded_count"] == 2
    assert (tmp_path / "one.jpg").exists()
    assert (tmp_path / "two.webp").exists()


def test_cli_is_noninteractive(monkeypatch, tmp_path: Path):
    def fake_scrape_site(**kwargs):
        return {
            "downloaded_count": 1,
            "target_url": kwargs["target_url"],
            "images": [{"filename": "one.jpg"}],
        }

    monkeypatch.setattr("image_scraper.cli.scrape_site", fake_scrape_site)
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: pytest.fail("input was called"))

    exit_code = main(["https://example.com", "--output-dir", str(tmp_path), "--max-images", "1"])

    assert exit_code == 0
