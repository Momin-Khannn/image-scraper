"""Core scraping and download logic."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "image/avif": ".avif",
}

JUNK_IMAGE_PATTERNS = [
    r"payment[_-]?icon",
    r"apple[_-]?pay",
    r"google[_-]?pay",
    r"master[-_]?card",
    r"paypal",
    r"visa",
    r"klarna",
    r"clearpay",
    r"american[_-]?express",
    r"shopify[_-]?pay",
    r"/badge",
    r"favicon",
    r"spinner",
    r"loader",
    r"pixel\.gif",
]
JUNK_IMAGE_RE = re.compile("|".join(JUNK_IMAGE_PATTERNS), re.IGNORECASE)
CSS_URL_RE = re.compile(r"url\([\"']?(.*?)[\"']?\)")
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class ExtractedImages:
    urls: list[str]
    placeholder_count: int
    total_image_tags: int
    dynamic_signals: int
    warnings: list[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def normalize_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("target_url is required")

    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", url) and not url.startswith(("http://", "https://")):
        raise ValueError("target_url must use http or https")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("target_url must use http or https")
    if not parsed.netloc:
        raise ValueError("target_url must include a valid host")

    return url


def content_type_base(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def extension_from_content_type(content_type: str) -> str | None:
    return CONTENT_TYPE_EXTENSIONS.get(content_type_base(content_type))


def extension_from_url(image_url: str) -> str | None:
    suffix = Path(urlparse(image_url).path).suffix.lower()
    if suffix in ALLOWED_EXTENSIONS:
        return ".jpg" if suffix == ".jpeg" else suffix
    return None


def sanitize_filename(name: str, fallback: str) -> str:
    cleaned = SAFE_FILENAME_RE.sub("_", name).strip("._-")
    return cleaned or fallback


def filename_from_url(image_url: str, content_type: str, index: int) -> str:
    parsed_name = Path(urlparse(image_url).path).name
    fallback_ext = extension_from_content_type(content_type) or extension_from_url(image_url) or ".jpg"
    fallback = f"image_{index:04d}{fallback_ext}"

    if not parsed_name:
        return fallback

    safe_name = sanitize_filename(parsed_name, fallback)
    stem = Path(safe_name).stem or f"image_{index:04d}"
    ext = Path(safe_name).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        ext = fallback_ext

    return f"{stem}{ext}"


def unique_filename(filename: str, used_names: set[str]) -> str:
    candidate = filename
    stem = Path(filename).stem
    ext = Path(filename).suffix
    counter = 1
    while candidate.lower() in used_names:
        candidate = f"{stem}_{counter}{ext}"
        counter += 1
    used_names.add(candidate.lower())
    return candidate


def is_downloadable_image(content_type: str, image_url: str) -> bool:
    base = content_type_base(content_type)
    if base.startswith("image/"):
        return True
    if base in {"", "application/octet-stream", "binary/octet-stream"}:
        return extension_from_url(image_url) is not None
    return False


def parse_srcset(value: str) -> str | None:
    best_url: str | None = None
    best_score = -1.0

    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        pieces = part.split()
        candidate_url = pieces[0]
        descriptor = pieces[1] if len(pieces) > 1 else ""
        score = 1.0
        if descriptor.endswith("w") or descriptor.endswith("x"):
            try:
                score = float(descriptor[:-1])
            except ValueError:
                score = 1.0
        if score >= best_score:
            best_url = candidate_url
            best_score = score

    return best_url


def absolute_image_url(candidate: str, base_url: str) -> str:
    if candidate.startswith("//"):
        return f"https:{candidate}"
    return urljoin(base_url, candidate)


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def parse_image_selection(pattern: str) -> set[int]:
    """Parse a selection string like '1-5, 8, 10-' into a set of 1-based indices.
    
    If no upper bound is given (e.g. '10-'), it returns a special large number (1_000_000) 
    in the set to indicate 'and everything after'. This is handled by filter_by_selection.
    """
    if not pattern or not pattern.strip():
        return set()
        
    indices = set()
    parts = pattern.replace(' ', '').split(',')
    
    for part in parts:
        if not part:
            continue
        if '-' in part:
            start_str, end_str = part.split('-', 1)
            try:
                start = int(start_str) if start_str else 1
                end = int(end_str) if end_str else 1_000_000
                if start > 0 and end >= start:
                    indices.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                val = int(part)
                if val > 0:
                    indices.add(val)
            except ValueError:
                continue
    return indices


def filter_by_selection(urls: list[str], selection_pattern: str | None) -> list[str]:
    if not selection_pattern or not selection_pattern.strip():
        return urls
        
    indices = parse_image_selection(selection_pattern)
    if not indices:
        return urls
        
    has_open_end = 1_000_000 in indices
    filtered_urls = []
    
    for i, url in enumerate(urls, start=1):
        if i in indices or (has_open_end and i >= max((idx for idx in indices if idx != 1_000_000), default=0)):
            filtered_urls.append(url)
            
    return filtered_urls


def extract_image_urls_from_html(html: str, base_url: str) -> ExtractedImages:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    placeholder_count = 0

    for img in soup.find_all("img"):
        chosen_url: str | None = None
        for attr in (
            "data-srcset",
            "srcset",
            "data-src",
            "data-original",
            "data-lazy-src",
            "data-image",
            "src",
        ):
            value = img.get(attr)
            if not value:
                continue
            if value.startswith("data:image"):
                placeholder_count += 1
                continue
            if attr.endswith("srcset") or "," in value:
                chosen_url = parse_srcset(value)
            else:
                chosen_url = value
            if chosen_url:
                break

        if chosen_url:
            urls.append(absolute_image_url(chosen_url, base_url))

    for tag in soup.find_all(style=True):
        for css_url in CSS_URL_RE.findall(tag["style"]):
            if css_url.startswith("data:image"):
                placeholder_count += 1
                continue
            urls.append(absolute_image_url(css_url, base_url))

    filtered = [url for url in urls if not JUNK_IMAGE_RE.search(url)]

    dynamic_signals = 0
    total_images = len(soup.find_all("img"))
    if placeholder_count > total_images * 0.5 and total_images > 3:
        dynamic_signals += 1
    if len(filtered) < 3 and total_images > 5:
        dynamic_signals += 1

    for script in soup.find_all("script"):
        script_src = script.get("src", "")
        script_text = script.string or ""
        search_space = f"{script_src} {script_text}".lower()
        if any(marker in search_space for marker in ("react", "vue", "angular", "next", "__nuxt", "svelte")):
            dynamic_signals += 1
            break

    warnings: list[str] = []
    if dynamic_signals >= 2:
        warnings.append(
            "This site appears to load some content with JavaScript; only images visible in static HTML were downloaded."
        )
    if urls and not filtered:
        warnings.append("Only filtered icon/payment/badge images were found.")

    return ExtractedImages(
        urls=unique_in_order(filtered),
        placeholder_count=placeholder_count,
        total_image_tags=total_images,
        dynamic_signals=dynamic_signals,
        warnings=warnings,
    )


def shopify_products_endpoint(target_url: str) -> str:
    parsed = urlparse(target_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    match = re.search(r"/collections/([^/?#]+)", parsed.path)
    if match:
        return f"{base}/collections/{match.group(1)}/products.json"
    return f"{base}/products.json"


def discover_shopify_images(
    session: requests.Session,
    target_url: str,
    *,
    all_shopify_images: bool,
    max_images: int,
) -> list[str] | None:
    endpoint = shopify_products_endpoint(target_url)
    per_page = 30
    page = 1
    all_products: list[dict[str, Any]] = []

    while page <= 100:
        try:
            response = session.get(
                endpoint,
                params={"limit": per_page, "page": page},
                timeout=30,
            )
        except requests.RequestException:
            return None

        if response.status_code != 200:
            if not all_products:
                return None
            break

        try:
            data = response.json()
        except ValueError:
            return None

        products = data.get("products", [])
        if not isinstance(products, list) or not products:
            break

        all_products.extend(products)
        if len(products) < per_page:
            break
        page += 1

    if not all_products:
        return None

    image_urls: list[str] = []
    for product in all_products:
        product_images = product.get("images", [])
        if not isinstance(product_images, list) or not product_images:
            continue
        selected_images = product_images if all_shopify_images else product_images[:1]
        for image in selected_images:
            if not isinstance(image, dict):
                continue
            src = image.get("src")
            if not isinstance(src, str) or not src:
                continue
            image_urls.append(absolute_image_url(src, target_url))
            if len(image_urls) >= max_images:
                return unique_in_order(image_urls)[:max_images]

    return unique_in_order(image_urls)[:max_images]


def download_image(
    session: requests.Session,
    image_url: str,
    output_dir: Path,
    index: int,
    used_names: set[str],
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    try:
        response = session.get(image_url, stream=True, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        return None, {"source_url": image_url, "error": str(exc)}

    content_type = response.headers.get("Content-Type", "")
    if not is_downloadable_image(content_type, image_url):
        return None, {
            "source_url": image_url,
            "error": f"Response is not an image: {content_type or 'unknown content type'}",
        }

    filename = unique_filename(filename_from_url(image_url, content_type, index), used_names)
    destination = output_dir / filename
    bytes_written = 0

    try:
        with destination.open("wb") as file_obj:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_obj.write(chunk)
                    bytes_written += len(chunk)
    except OSError as exc:
        return None, {"source_url": image_url, "error": str(exc)}

    if bytes_written == 0:
        destination.unlink(missing_ok=True)
        return None, {"source_url": image_url, "error": "Image response body was empty"}

    return (
        {
            "source_url": image_url,
            "filename": filename,
            "relative_path": filename,
            "bytes": bytes_written,
            "content_type": content_type_base(content_type) or "unknown",
        },
        None,
    )


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_report(
    *,
    target_url: str,
    strategy: str,
    max_images: int,
    all_shopify_images: bool,
    image_selection: str | None = None,
    started_at: str,
    candidate_urls: list[str],
    warnings: list[str],
    images: list[dict[str, Any]],
    failures: list[dict[str, str]],
    discovered_count: int | None = None,
) -> dict[str, Any]:
    discovered = discovered_count if discovered_count is not None else len(candidate_urls)
    return {
        "target_url": target_url,
        "strategy": strategy,
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "max_images": max_images,
        "all_shopify_images": all_shopify_images,
        "image_selection": image_selection,
        "discovered_count": discovered,
        "attempted_count": len(candidate_urls),
        "downloaded_count": len(images),
        "failed_count": len(failures),
        "skipped_count": max(0, discovered - len(candidate_urls)),
        "warnings": warnings,
        "images": images,
        "failures": failures,
    }


def send_webhook(webhook_url: str, report: dict[str, Any], output_dir: Path) -> None:
    """Send the scrape report and base64 encoded images to a webhook URL."""
    if not webhook_url:
        return

    payload = dict(report)
    images_with_data = []

    for img in payload.get("images", []):
        img_copy = dict(img)
        img_path = output_dir / img["filename"]
        if img_path.exists():
            try:
                with img_path.open("rb") as f:
                    img_copy["base64_data"] = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                img_copy["webhook_error"] = f"Failed to encode image: {e}"
        images_with_data.append(img_copy)
        
    payload["images"] = images_with_data

    try:
        requests.post(webhook_url, json=payload, timeout=30)
    except requests.RequestException as e:
        print(f"Webhook delivery failed: {e}")


def scrape_site(
    target_url: str,
    output_dir: str | Path,
    *,
    max_images: int = 200,
    all_shopify_images: bool = False,
    image_selection: str | None = None,
    webhook_url: str | None = None,
    report_json: str | Path | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    if max_images < 1:
        raise ValueError("max_images must be at least 1")

    normalized_url = normalize_url(target_url)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    scraper_session = session or build_session()
    started_at = utc_now_iso()
    warnings: list[str] = []
    strategy = "html"
    discovered_count: int | None = None

    shopify_urls = discover_shopify_images(
        scraper_session,
        normalized_url,
        all_shopify_images=all_shopify_images,
        max_images=max_images,
    )

    if shopify_urls is not None:
        strategy = "shopify_api"
        candidate_urls = filter_by_selection(shopify_urls, image_selection)[:max_images]
        discovered_count = len(shopify_urls)
    else:
        try:
            response = scraper_session.get(normalized_url, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            candidate_urls = []
            warnings.append(f"Could not fetch target page: {exc}")
        else:
            extracted = extract_image_urls_from_html(response.text, normalized_url)
            warnings.extend(extracted.warnings)
            discovered_count = len(extracted.urls)
            candidate_urls = filter_by_selection(extracted.urls, image_selection)[:max_images]

    images: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    used_names: set[str] = set()

    for index, image_url in enumerate(candidate_urls, start=1):
        image, failure = download_image(scraper_session, image_url, output_path, index, used_names)
        if image:
            images.append(image)
        if failure:
            failures.append(failure)

    if not candidate_urls:
        warnings.append("No downloadable image URLs were discovered.")

    report = build_report(
        target_url=normalized_url,
        strategy=strategy,
        max_images=max_images,
        all_shopify_images=all_shopify_images,
        image_selection=image_selection,
        started_at=started_at,
        candidate_urls=candidate_urls,
        warnings=warnings,
        images=images,
        failures=failures,
        discovered_count=discovered_count,
    )

    write_json(output_path / "manifest.json", report)
    if report_json:
        write_json(Path(report_json), report)

    if webhook_url:
        send_webhook(webhook_url, report, output_path)

    return report
