# Cloud Inventory

A small Flask inventory app for a cloud computing project. It demonstrates an HTTP application, a health endpoint, a container image, and SQLite data stored at a configurable path.

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

