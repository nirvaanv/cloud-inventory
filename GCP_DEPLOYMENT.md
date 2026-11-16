# Private GCP VM Demo

This guide runs the Flask app in a Compute Engine VM with **no external/public IP**. You access it from your own laptop through an authenticated IAP SSH tunnel and open `http://127.0.0.1:5000`. It is not a public website; share your screen if you want to show it to your class.

## Cost and access notes

Compute Engine requires billing to be enabled. The e2-micro Free Tier applies only in `us-central1`, `us-east1`, or `us-west1`, with a monthly time allowance, up to 30 GB-months of standard persistent disk, and up to 1 GB/month of eligible outbound transfer. The allowance is shared across the billing account, so another project can use it first. This setup avoids a VM external-IP charge, but **it cannot guarantee a zero bill**. If a guaranteed $0 cost is required, do not create the VM; run the app locally instead. See [Google Cloud Free Tier limits](https://docs.cloud.google.com/free/docs/free-cloud-features).

The VM has no general internet egress. This demo downloads Linux-compatible Python packages on your laptop and copies them with the app over IAP, so the VM needs no Docker image and does not install packages from the internet. Do not add Cloud NAT for this demo: it is a separate billable service.

## Requirements

- A Google Cloud project with billing linked and Compute Engine API enabled.
- Google Cloud CLI (`gcloud`) and Python 3.12 with `pip` installed on your laptop.
- Permission to create Compute Engine VMs and IAP tunnels in the project.

The commands below use `us-central1-a` to target the e2-micro Free Tier. Change it only if you accept that another region might not qualify.

## 1. Select the project and enable APIs

Replace `YOUR_PROJECT_ID` with the project ID shown in the Google Cloud console.

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable compute.googleapis.com iap.googleapis.com
```

## 2. Download Linux dependencies on your laptop

Run these commands from the repository root. They download wheels for the VM's Linux x86-64 and Python 3.12 environment; the VM itself does not need internet access.

```bash
mkdir -p wheelhouse
python3 -m pip download \
  --only-binary=:all: \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 312 \
  --abi cp312 --abi abi3 --abi none \
  --dest wheelhouse \
  -r requirements.txt
```

## 3. Create an IAP-only SSH firewall rule and private VM

The firewall rule allows SSH only from Google's IAP TCP-forwarding range. The VM receives an internal IP only.

```bash
gcloud compute firewall-rules create cloud-inventory-allow-iap-ssh \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=cloud-inventory-iap
```

```bash
gcloud compute instances create cloud-inventory-vm \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-type=pd-standard \
  --boot-disk-size=10GB \
  --no-address \
  --tags=cloud-inventory-iap
```

If the project does not have a `default` network, stop here and select an existing VPC/subnet instead of creating extra networking resources.

## 4. Copy and run the app directly on the VM

Create a destination folder, then copy the source and dependency wheels through IAP:

```bash
gcloud compute ssh cloud-inventory-vm \
  --zone=us-central1-a \
  --tunnel-through-iap \
  --command='mkdir -p ~/cloud-inventory'
```

```bash
gcloud compute scp --recurse app.py requirements.txt templates wheelhouse \
  cloud-inventory-vm:~/cloud-inventory/ \
  --zone=us-central1-a \
  --tunnel-through-iap
```

SSH to the VM and confirm its Python version:

```bash
gcloud compute ssh cloud-inventory-vm \
  --zone=us-central1-a \
  --tunnel-through-iap
```

In the VM shell, extract the wheels into a local package directory, then start Gunicorn. The app listens only on the VM's loopback interface, and SQLite data is stored on the VM's boot disk.

```bash
cd ~/cloud-inventory
python3 --version
mkdir -p site-packages
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile

for wheel in Path("wheelhouse").glob("*.whl"):
    with ZipFile(wheel) as archive:
        archive.extractall("site-packages")
PY
nohup env \
  PYTHONPATH="$HOME/cloud-inventory/site-packages" \
  DATABASE_PATH="$HOME/cloud-inventory/inventory.db" \
  python3 -m gunicorn --workers 1 --bind 127.0.0.1:5000 app:app \
  > "$HOME/cloud-inventory/app.log" 2>&1 &
```

Exit the SSH shell. On your laptop, open an IAP tunnel:

```bash
gcloud compute ssh cloud-inventory-vm \
  --zone=us-central1-a \
  --tunnel-through-iap \
  -- -N -L 5000:127.0.0.1:5000
```

Keep that terminal open and visit [http://127.0.0.1:5000](http://127.0.0.1:5000) on your laptop. Only a Google account authorized for IAP/VM access can open the tunnel. IAP access to VMs without an external IP is documented by [Google Cloud](https://docs.cloud.google.com/compute/docs/connect/ssh-using-iap).

## 5. Stop and delete resources after the demo

Deleting the VM also deletes its boot disk and demo data. The firewall rule has no VM data, but delete it too if you no longer need it. Remove the temporary local wheelhouse after deployment if you no longer need it.

```bash
gcloud compute instances delete cloud-inventory-vm --zone=us-central1-a
gcloud compute firewall-rules delete cloud-inventory-allow-iap-ssh
rm -rf wheelhouse
```

Deleting the VM prevents further VM and boot-disk charges. Billing reports may take time to update. This cleanup is not a retroactive cap on charges already accrued.
