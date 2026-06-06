# Image Scraper Actions

A production-ready Python image scraper that can run from GitHub Actions instead of your local machine. It downloads images from Shopify product JSON when available, falls back to standard HTML image extraction, and writes every run to an output folder with a `manifest.json` report.

GitHub is used in two ways:

- **GitHub Actions** runs the Python scraper in the cloud and uploads the scraped images as an artifact.
- **GitHub Pages** publishes a public project page from `docs/`.

GitHub Pages is static hosting, so it does not run Python or accept public scrape requests by itself.

## Local Run

```powershell
python -m pip install -e ".[dev]"
image-scraper https://example.com --output-dir output --max-images 50
```

You can also use the original filename as a compatibility launcher:

```powershell
python "Data Scapping from websites ( pictures ).py" https://example.com --output-dir output
```

## CLI Options

```text
image-scraper TARGET_URL [--output-dir output] [--max-images 200] [--all-shopify-images] [--report-json path]
```

- `TARGET_URL`: Website URL to scrape. Missing `https://` is added automatically.
- `--output-dir`: Folder for downloaded images and `manifest.json`.
- `--max-images`: Maximum image candidates to download.
- `--all-shopify-images`: For Shopify stores, download all product images instead of only the first product image.
- `--report-json`: Optional second path for the same run metadata JSON.

## Deploy To GitHub

1. Create a public GitHub repository named `image-scraper-actions`.
2. From this folder, run:

```powershell
git init
git add .
git commit -m "Build GitHub Actions image scraper"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/image-scraper-actions.git
git push -u origin main
```

3. Open the repository on GitHub.
4. Go to **Settings > Pages** and select **GitHub Actions** as the Pages source if GitHub asks for it.
5. The public site deploys from `.github/workflows/pages.yml`.
6. The scraper workflow appears under **Actions > Scrape Images**.

## Run In GitHub Actions

1. Open **Actions > Scrape Images**.
2. Select **Run workflow**.
3. Enter:
   - `target_url`
   - optional `max_images`
   - optional `all_shopify_images`
4. When the run finishes, download the artifact named `scraped-images-<run-number>`.

The artifact contains downloaded images plus `manifest.json`. Artifacts are retained for 14 days.

## Test

```powershell
python -m pip install -e ".[dev]"
pytest
```

## Responsible Use

Only scrape sites you are allowed to scrape. Respect website terms, robots rules, rate limits, copyright, and privacy. This project is intended for lawful collection of assets you have permission to download.
