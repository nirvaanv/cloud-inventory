# Cloud Inventory: GCP Presentation Guide

Use this guide to present the project against the Tool Explorer marking scheme. Keep the GitHub Pages preview and the GCP-hosted Flask app clearly distinct: Pages is a static sample; the Flask app runs on a VM only after you deploy it using [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md).

## 1. Tool introduction — Google Cloud Platform

Google Cloud Platform (GCP) is Google's cloud computing platform. It provides computing, storage, databases, networking, analytics, and application hosting over the internet. Instead of buying and maintaining physical servers, users create cloud resources when needed and manage them through the Google Cloud console or command-line tools.

## 2. Services to explain

- **IaaS — Compute Engine:** virtual machines where a user chooses an operating system, machine size, disk, and network settings. This project uses a small Linux VM to run Flask.
- **PaaS — Cloud Run:** runs a containerized application without the user managing a VM. It is an alternative hosting service, not part of this VM demo.
- **SaaS — Google Workspace:** ready-to-use online apps such as Gmail and Google Drive.

## 3. Practical demonstration

For a live GCP demonstration, deploy the Flask app using the private VM guide before class. In the console, show the VM's machine type, zone, internal IP, and that it has **no external IP**. Connect through IAP, open the app through the local tunnel, add an example item, then visit `/health` to show the app's health response. Explain that IAP checks your Google identity and IAM permission before allowing the tunnel. If you have not deployed the VM, present the GitHub Pages sample as a static preview only; do not describe it as a running GCP app.

## 4. Features and benefits

- **On-demand resources:** create or delete a VM when needed.
- **Regions and zones:** choose where a resource runs and understand its location and availability scope.
- **IAM and IAP:** control who can manage or privately connect to a VM.
- **Persistent disk:** stores the app's SQLite file beyond the life of a running process.
- **Measured billing:** resource usage is metered; free-tier eligibility has limits and is not a guaranteed spending cap.

## 5. Real-world application

A small retailer or campus lab can use an inventory app to check equipment quantities, spot low stock, and decide what to replenish. In a larger organization, the same idea can connect to a managed database and serve multiple locations.

## 6. Viva practice

**What is cloud computing?** On-demand access to computing resources over a network, usually billed by measured use.

**What is a VM?** A software-defined computer with an operating system, CPU, memory, disk, and network settings.

**How is IaaS different from PaaS?** IaaS gives more control over the virtual machine; PaaS manages more of the runtime and infrastructure for the developer.

**Why does this VM have no external IP?** To avoid direct internet access to the VM. IAP provides authenticated administrative access through a tunnel.

**Where is the inventory data stored?** In SQLite on the VM's persistent boot disk for this demo.

**Is the demo guaranteed free?** No. Compute Engine requires billing, and Free Tier usage limits are shared across the billing account. Stop and delete resources after the demonstration, and check the billing page.

## Before presenting

1. Open the GitHub Pages sample and confirm it loads.
2. If demonstrating GCP, deploy and verify the VM ahead of time; do not create it for the first time during the presentation.
3. Keep the IAP tunnel terminal open while showing the Flask app.
4. Delete the VM after the demo if you no longer need it. The cleanup command is in the deployment guide.
