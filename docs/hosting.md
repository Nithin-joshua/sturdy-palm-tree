# Cloud Hosting & Deployment Guide

This guide details how to host the **Multimodal Industrial Inspection Agent** on modern cloud platforms. Thanks to the unified architecture implemented in Phases 1–3, both the backend API and frontend console run together inside a single lightweight container.

---

## Provider Comparison

| Provider | Free Tier | Setup Ease | Custom Domain | Persistent Disk | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Render** | Yes (Free Web Service) | Easiest (1-Click Blueprint) | Yes (Free SSL) | Available ($1/mo) | Zero-maintenance demos & portfolios |
| **Railway** | $5 monthly credit | Very Easy (GitHub link) | Yes (Free SSL) | Available ($0.25/GB) | Fast developer deployments |
| **Fly.io** | Free allowance | Easy (CLI `fly deploy`) | Yes (Free SSL) | Yes (Volumes) | Global low-latency edge deployment |
| **Hugging Face Spaces** | Free CPU Tier | Easy (Docker Space) | No | Ephemeral | Machine learning community showcase |
| **AWS EC2 / DigitalOcean** | Free tier / $4-10/mo | Moderate (Docker) | Yes (Manual/Certbot) | Yes (Standard EBS) | Enterprise production control |

---

## 1. Deploying to Render (Recommended - Free Tier)

Render automatically detects [`render.yaml`](../render.yaml) from your GitHub repository.

1. Push your repository to GitHub.
2. Sign in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Blueprint**.
4. Connect your GitHub repository.
5. Render reads `render.yaml` and sets up the Docker Web Service automatically.
6. Click **Apply**.
7. Once deployed, access your live app at `https://industrial-inspection-agent.onrender.com`.

---

## 2. Deploying to Railway

Railway detects [`railway.toml`](../railway.toml) and [`Dockerfile`](../Dockerfile).

1. Push your repository to GitHub.
2. Go to [railway.app](https://railway.app) and click **New Project** -> **Deploy from GitHub repo**.
3. Select this repository.
4. Railway will automatically build the `Dockerfile`.
5. Under service **Settings** -> **Networking**, click **Generate Domain**.
6. Access your public HTTPS URL.

---

## 3. Deploying to Fly.io

Fly.io utilizes [`fly.toml`](../fly.toml) for fast container deployment.

1. Install Flyctl CLI:
   - Windows (PowerShell): `iwr https://fly.io/install.ps1 -useb | iex`
   - macOS / Linux: `curl -L https://fly.io/install.sh | sh`
2. Sign in: `fly auth login`
3. Launch from project root:
   ```bash
   fly launch --copy-config
   ```
4. Deploy:
   ```bash
   fly deploy
   ```
5. Open your app: `fly open`

---

## 4. Deploying to Hugging Face Spaces (Free)

1. Create a new Space on [Hugging Face Spaces](https://huggingface.co/new-space).
2. Space SDK: Select **Docker** -> **Blank**.
3. Clone the Space repository or push this repository to your Space remote:
   ```bash
   git remote add hf https://huggingface.co/spaces/<your-username>/<your-space-name>
   git push hf main
   ```
4. Hugging Face builds and hosts the Docker container automatically.

---

## 5. Deploying to a Linux VPS (AWS EC2 / DigitalOcean / Linode)

1. SSH into your VPS:
   ```bash
   ssh user@your-server-ip
   ```
2. Install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
3. Clone and run:
   ```bash
   git clone <your-repo-url>
   cd Multimodal_Industrial_Inspection_Agent
   docker build -t inspection-agent .
   docker run -d \
     --name inspection-agent \
     --restart unless-stopped \
     -p 80:8000 \
     -v $(pwd)/outputs:/app/outputs \
     inspection-agent
   ```
4. Access `http://your-server-ip`.

---

## Production Security Checklist

- [x] **Strict Upload Limits:** Handled by `MAX_UPLOAD_SIZE_MB` (default 25MB) in [`backend/app/api/inspect.py`](../backend/app/api/inspect.py).
- [x] **Security Headers:** Enforced by middleware (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`) in [`backend/app/main.py`](../backend/app/main.py).
- [x] **CORS Origin Lockdown:** Set `CORS_ORIGINS=https://yourdomain.com` in `.env` or provider environment variables.
- [x] **Non-Root Container:** Runs as unprivileged user `appuser` (UID 1000) inside [`Dockerfile`](../Dockerfile).
- [x] **Health Check Endpoint:** Probed at `/health` by container runtimes and load balancers.
