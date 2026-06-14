# Image Scraper Actions

A production-ready Python image scraper that can run from GitHub Actions instead of your local machine. It downloads images from Shopify product JSON when available, falls back to standard HTML image extraction, and writes every run to an output folder with a `manifest.json` report.

The deployed site lets visitors request picture collection through GitHub Issues. GitHub Actions processes each request, publishes the result gallery to GitHub Pages, comments the public link back on the issue, and closes the request.

GitHub is used in two ways:

- **GitHub Actions** runs the Python scraper in the cloud, uploads the scraped images as an artifact, and deploys public request galleries.
- **GitHub Issues** acts as the public request queue for visitors.
- **GitHub Pages** publishes the public software site, latest gallery, and request history.

GitHub Pages is static hosting, so it does not run Python or accept public scrape requests by itself. The Python job runs on GitHub Actions, then Pages shows the static result.

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

1. Create a public GitHub repository named `image-scraper` under `Momin-Khannn`.
2. From this folder, run:

```powershell
git remote add origin https://github.com/Momin-Khannn/image-scraper.git
git push -u origin main
```

3. Open the repository on GitHub.
4. Go to **Settings > Pages** and select **GitHub Actions** as the Pages source if GitHub asks for it.
5. The public site deploys from `.github/workflows/pages.yml`.
6. The scraper workflow appears under **Actions > Scrape Images**.
7. Your public site will be available at `https://Momin-Khannn.github.io/image-scraper/`.

## Public Visitor Flow

1. Visitor opens `https://Momin-Khannn.github.io/image-scraper/`.
2. Visitor enters a website URL and clicks **Create request**.
3. GitHub opens a prefilled issue. The visitor submits it.
4. `.github/workflows/process-request.yml` runs automatically.
5. GitHub Actions scrapes the target, publishes the gallery, comments the public result URL, and closes the issue.

## Run In GitHub Actions

1. Open **Actions > Scrape Images**.
2. Select **Run workflow**.
3. Enter:
   - `target_url`
   - optional `max_images`
   - optional `all_shopify_images`
4. When the run finishes, open the Pages URL to view the latest public gallery.
5. You can also download the artifact named `scraped-images-<run-number>`.

The artifact contains downloaded images plus `manifest.json`. Artifacts are retained for 14 days. The public gallery is replaced each time the workflow successfully deploys a new scrape.

## Public Gallery

After deployment, the public pages are:

- Project site: `https://Momin-Khannn.github.io/image-scraper/`
- Latest gallery: `https://Momin-Khannn.github.io/image-scraper/latest/`
- Public request history: `https://Momin-Khannn.github.io/image-scraper/requests/`

Only publish scrape results you are allowed to show publicly. If you need private results, keep the repository private and use workflow artifacts instead of Pages.

## Test

```powershell
python -m pip install -e ".[dev]"
pytest
```

## Responsible Use

Only scrape sites you are allowed to scrape. Respect website terms, robots rules, rate limits, copyright, and privacy. This project is intended for lawful collection of assets you have permission to download.
