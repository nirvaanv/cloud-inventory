# Cloud Inventory

A small Flask inventory app for a cloud computing project. It demonstrates an HTTP application, a health endpoint, a container image, and SQLite data stored at a configurable path.

## Online preview

The [interactive sample inventory](https://nirvaanv.github.io/cloud-inventory/) is hosted with GitHub Pages and works while your computer is offline. It uses sample data saved in each visitor's browser; it is not connected to the Flask app or its SQLite database. To publish or republish it, open **Settings → Pages**, choose **Deploy from a branch**, select `main` and `/docs`, then save. GitHub publishes `docs/index.html` at the preview link above.

For the real Flask application, follow the local or Docker instructions below. The static preview is intended as a permanent project showcase, not a live backend deployment.

## Run locally

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. Data is stored in `instance/inventory.db` by default. Set `DATABASE_PATH` to change the location.

## Run with Docker

```bash
docker build -t cloud-inventory .
docker run --rm -p 5000:5000 -v inventory-data:/data cloud-inventory
```

Open http://127.0.0.1:5000. The named volume keeps the SQLite database between container replacements. Check `http://127.0.0.1:5000/health` for the health response.

