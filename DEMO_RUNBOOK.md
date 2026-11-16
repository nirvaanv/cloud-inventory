# Demo Runbook

This runbook describes the live Cloud Inventory demonstration on a private Google Cloud Compute Engine VM. The GitHub Pages preview is a separate static sample and is not evidence that the Flask service is deployed.

## Architecture

```mermaid
flowchart LR
  Browser[Your browser<br/>127.0.0.1:5000] -->|Local SSH port forward| IAP[Identity-Aware Proxy<br/>Google identity + IAM]
  IAP -->|Encrypted TCP tunnel| VM[Compute Engine VM<br/>Internal IP only]
  VM --> App[Flask + Gunicorn]
  App --> DB[(SQLite on VM boot disk)]
```

The VM has no external IP. You open the application on your laptop through an IAP tunnel; the VM does not expose the Flask port to the internet. The tunnel command and VM setup are in [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md).

## Pre-demo checks

1. Confirm the VM is running in the intended project and zone, and that its external IP field is empty.
2. Start the IAP port-forwarding command from the deployment guide and keep that terminal open.
3. Open `http://127.0.0.1:5000` and confirm the inventory page loads.
4. Open `http://127.0.0.1:5000/health` and confirm it returns `{"status":"healthy"}`.

## Demonstration sequence

1. In the Google Cloud console, show the VM name, machine type, zone, and absence of an external IP.
2. Explain that IAP checks Google identity and IAM authorization before forwarding the connection.
3. Show the Flask inventory page through the local tunnel.
4. Add a sample product and quantity, then show it in the list.
5. Open the health endpoint to show the application's basic health check.
6. Explain that the app is container-ready, but this private VM guide runs the Python application directly on the VM.

## Screenshot evidence

Capture screenshots from the actual deployed VM and save them under [`docs/screenshots/`](docs/screenshots/). Do not label the GitHub Pages sample as the GCP-hosted app.

| Filename | Capture |
| --- | --- |
| `01-compute-engine-private-vm.png` | Compute Engine VM list with machine type, zone, and no external IP visible. |
| `02-inventory-dashboard.png` | Inventory page open through the IAP tunnel. |
| `03-inventory-product-added.png` | Inventory page after adding a clearly identified sample product. |
| `04-application-health.png` | `/health` response in the browser. |

Before committing screenshots, remove browser tabs or account details that are not needed for the evidence. Only use sample inventory data. Add the images to Git and reference them in the README if you want them displayed on the repository front page.

## Shutdown

After the demo, delete the VM and its boot disk if you no longer need them. Use the cleanup commands at the end of [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md), then check the Cloud Billing report later; cost data can be delayed.
