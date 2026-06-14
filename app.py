import datetime
import uuid
from pathlib import Path
from flask import Flask, render_template, request, redirect

from image_scraper.scraper import scrape_site
from image_scraper.gallery import build_public_gallery

app = Flask(__name__)

# Ensure the static directory exists
STATIC_DIR = Path("static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scrape", methods=["POST"])
def scrape():
    # Extract form data
    url = request.form.get("url")
    max_images = int(request.form.get("max_images", 50))
    shopify_mode = request.form.get("shopify_mode")
    selection = request.form.get("selection")
    webhook = request.form.get("webhook")

    all_shopify_images = (shopify_mode == "all")

    # We skip empty strings so they are treated as None
    if selection and not selection.strip():
        selection = None
    if webhook and not webhook.strip():
        webhook = None

    # Generate a unique run ID for the output
    run_id = f"scrape_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    output_dir = Path("output") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Execute the scrape synchronously
    manifest = scrape_site(
        target_url=url,
        output_dir=output_dir,
        max_images=max_images,
        all_shopify_images=all_shopify_images,
        image_selection=selection,
        webhook_url=webhook
    )

    # Build the static gallery
    site_dir = STATIC_DIR / "site"
    build_public_gallery(
        docs_dir=Path("templates"),  # Pass templates to satisfy the arg, though we only care about the images
        output_dir=output_dir,
        site_dir=site_dir,
        gallery_subdir="latest",
        update_latest=True,
    )

    # Redirect to the built static HTML gallery
    return redirect("/static/site/latest/index.html")

if __name__ == "__main__":
    # Run the Flask app on localhost:5000 using Waitress for production
    from waitress import serve
    print("Starting production server on http://0.0.0.0:5000")
    serve(app, host="0.0.0.0", port=5000)
