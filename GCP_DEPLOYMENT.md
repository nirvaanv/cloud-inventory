# Private GCP VM Demo

This guide runs the Flask app in a Compute Engine VM with **no external/public IP**. You access it from your own laptop through an authenticated IAP SSH tunnel and open `http://127.0.0.1:5000`. The VM is not a public website; share your screen if you want to show it to your class.

## Cost and access notes

Compute Engine requires billing to be enabled. The e2-micro Free Tier applies only in `us-central1`, `us-east1`, or `us-west1`, with a monthly time allowance, up to 30 GB-months of standard persistent disk, and up to 1 GB/month of eligible outbound transfer. The allowance is shared across the billing account, so another project can use it first. This setup avoids a VM external-IP charge, but **it cannot guarantee a zero bill or a ₹50 maximum** if the Free Tier allowance is unavailable. See [Google Cloud Free Tier limits](https://docs.cloud.google.com/free/docs/free-cloud-features).

The VM has no general internet egress. This demo downloads Linux-compatible Python packages on your laptop and copies them with the app over IAP, so the VM needs no Docker image and does not install packages from the internet. Do not add Cloud NAT for this demo: it is a separate billable service.

Free Tier is not a hard spending cap. If the monthly e2-micro allowance has already been used, the listed us-central1 compute rate is about **$0.0084/hour** (about **$0.60 for 72 hours**, before disk and tax). Google Cloud services billed in India are subject to **18% GST**. Stopping the VM stops compute usage, but its boot disk remains and can still be billed if the disk allowance is exhausted. Check [current Compute Engine rates](https://cloud.google.com/products/compute/pricing/general-purpose) and the [India tax details](https://docs.cloud.google.com/billing/docs/resources/vat-overview?skip_cache=false) before leaving it running.

## Requirements

- A Google Cloud project with billing linked and Compute Engine API enabled.
- Google Cloud CLI (`gcloud`) and Python 3.12 with `pip` installed on your laptop.
- Permission to create Compute Engine VMs and IAP tunnels in the project.

The commands below use `us-central1-a` to target the e2-micro Free Tier. Change it only if you accept that another region might not qualify.

## 1. Select the project and enable APIs

```bash
gcloud auth login
gcloud config set project cloud-inventory-demo
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

## 3. Create IAP-only SSH firewall rules and the private VM

The allow rule admits SSH from Google's IAP TCP-forwarding range. The higher-priority deny rule blocks other IPv4 SSH sources, including the default network's broad SSH rule. The VM receives an internal IP only.

```bash
gcloud compute firewall-rules create cloud-inventory-allow-iap-ssh \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --priority=800 \
  --target-tags=cloud-inventory-iap
```

```bash
gcloud compute firewall-rules create cloud-inventory-deny-direct-ssh \
  --network=default \
  --direction=INGRESS \
  --action=DENY \
  --rules=tcp:22 \
  --source-ranges=0.0.0.0/0 \
  --priority=900 \
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
gcloud compute scp --recurse app.py database.py requirements.txt templates static wheelhouse \
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

## Start and stop the VM between demos

To stop compute charges while preserving the VM and its disk:

```bash
gcloud compute instances stop cloud-inventory-vm --zone=us-central1-a
```

The boot disk remains and can still incur storage charges. When you need the demo again, start the VM:

```bash
gcloud compute instances start cloud-inventory-vm --zone=us-central1-a
```

After it starts, SSH through IAP and start the app again (the `nohup` process does not survive a VM stop):

```bash
gcloud compute ssh cloud-inventory-vm \
  --zone=us-central1-a \
  --tunnel-through-iap
```

Then, in the VM shell:

```bash
cd ~/cloud-inventory
nohup env \
  PYTHONPATH="$HOME/cloud-inventory/site-packages" \
  DATABASE_PATH="$HOME/cloud-inventory/inventory.db" \
  python3 -m gunicorn --workers 1 --bind 127.0.0.1:5000 app:app \
  > "$HOME/cloud-inventory/app.log" 2>&1 &
```

Exit the SSH shell and recreate the laptop IAP port-forward from step 4.

## Delete resources when finished

Deleting the VM also deletes its boot disk and demo data. Delete both firewall rules if they are no longer needed. Remove the temporary local wheelhouse after deployment if you no longer need it.

```bash
gcloud compute instances delete cloud-inventory-vm --zone=us-central1-a
gcloud compute firewall-rules delete cloud-inventory-allow-iap-ssh
gcloud compute firewall-rules delete cloud-inventory-deny-direct-ssh
rm -rf wheelhouse
```

Deleting the VM prevents further VM and boot-disk charges. Billing reports may take time to update. This cleanup is not a retroactive cap on charges already accrued.
