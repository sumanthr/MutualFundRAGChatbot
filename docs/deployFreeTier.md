# Deploy on Render Free + Vercel Hobby (free)

Use this guide instead of [deployRenderVercel.md](./deployRenderVercel.md) when you want **no paid plans**.

| Platform | Free product | What you run |
|----------|----------------|--------------|
| **Render** | Free Web Service | FastAPI backend (`mfr_phase4`) |
| **Vercel** | Hobby (default) | Static UI in `phase4/mfr_phase4/static` |

**Trade-offs on Render Free**

- No persistent disk → Chroma and chat SQLite are **wiped on every redeploy** → run ingest again in the Shell after each deploy.
- Service **sleeps** after ~15 minutes with no traffic → first request can take **30–90 seconds**.
- **512 MB RAM** → first `python -m mfr_phase1` may be slow or fail; retry once or run ingest when traffic is low.

Repo: `https://github.com/sumanthr/MutualFundRAGChatbot` (or your fork).

---

## Part A — Prerequisites

1. Code on GitHub (`main` branch pushed).
2. [Groq](https://console.groq.com/) account → create an API key.
3. [Render](https://render.com) account (GitHub login).
4. [Vercel](https://vercel.com) account (GitHub login).

---

## Part B — Backend on Render (Free)

### B1. Create the web service (manual — easiest on Free)

Do **not** use the paid `render.yaml` Blueprint as-is (it requests **Starter** + a disk).

1. Go to [Render Dashboard](https://dashboard.render.com) → **New +** → **Web Service**.
2. Connect **GitHub** → select repository **MutualFundRAGChatbot**.
3. Settings:

   | Field | Value |
   |--------|--------|
   | **Name** | `mutual-fund-rag-api` (or any name) |
   | **Region** | Oregon (or nearest) |
   | **Branch** | `main` |
   | **Root Directory** | *(leave empty)* |
   | **Runtime** | **Python 3** |
   | **Build Command** | `bash scripts/render-build.sh` |
   | **Start Command** | `uvicorn mfr_phase4.app:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | **Free** |

4. Expand **Environment Variables** and add:

   | Key | Value |
   |-----|--------|
   | `PYTHON_VERSION` | `3.11.6` |
   | `GROQ_API_KEY` | *(your Groq secret)* |
   | `CHROMA_PATH` | `./deploy/chroma_data` |
   | `THREAD_DB_PATH` | `./data/threads.sqlite3` |
   | `CHROMA_COLLECTION` | `mutual_fund_faq_groww_v1` |
   | `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
   | `GROQ_MODEL` | `llama-3.1-8b-instant` |
   | `RETRIEVAL_MAX_DISTANCE` | `0.38` |
   | `HF_HOME` | `./.cache/huggingface` |
   | `TRANSFORMERS_CACHE` | `./.cache/huggingface` |
   | `SENTENCE_TRANSFORMERS_HOME` | `./.cache/huggingface` |

5. **Do not** attach a persistent disk (not available on Free).
6. Click **Create Web Service** and wait for the first deploy (build can take several minutes).

### B2. Note your API URL

When deploy finishes, copy the URL, e.g.:

`https://mutual-fund-rag-api.onrender.com`

You need only the **hostname** for Vercel: `mutual-fund-rag-api.onrender.com`.

### B3. Health check

Open in a browser:

`https://<your-render-host>/health`

Expected: `{"status":"ok"}`.

If you get an error, wait for the deploy to finish or check **Logs** in Render.

### B4. Search index (no Shell on Free)

**Render Shell is paid** — use the **committed index** in `deploy/chroma_data/` (included in the repo). The build script also warms the embedding model cache.

1. On Render → **Environment**, set **`CHROMA_PATH`** = `./deploy/chroma_data` (not `./chroma_data`).
2. Redeploy with **Clear build cache** so `bash scripts/render-build.sh` runs (uses `deploy/chroma_data` + model warmup).
3. Open **`https://<render-host>/ready`** — expect `"ready": true` and `"chroma_count" > 0`.

To refresh the index locally later:

```bash
python -m mfr_phase1 --chroma-path ./chroma_data
./scripts/export-deploy-chroma.sh
git add deploy/chroma_data && git commit -m "Refresh deploy chroma" && git push
```

### B5. Test the API

In Shell or from your laptop:

```bash
curl -sS "https://<your-render-host>/health"
```

Optional chat test (may be slow if the service was sleeping):

```bash
curl -sS -X POST "https://<your-render-host>/v1/chat/respond" \
  -H "Content-Type: application/json" \
  -d '{"thread_id":null,"query":"What is the minimum SIP for HDFC ELSS?"}'
```

You should get JSON with `"response_type":"factual"` (or `"refusal"` if ingest did not complete).

---

## Part C — Frontend on Vercel (Hobby / free)

### C1. Point the UI at Render (fixes 502 timeouts)

Vercel rewrites can **time out** (~60s) while Render Free wakes up and loads the embedding model → **502**.

**Recommended:** call Render **directly** from the browser (CORS is already enabled).

1. Edit `phase4/mfr_phase4/static/config.js`:

   ```javascript
   window.MFR_API_BASE = "https://<your-render-host>.onrender.com";
   ```

   (no trailing slash)

2. Still update `vercel.json` rewrites if you want `/health` on the Vercel domain, or rely on `config.js` only for API calls.

### C1b. Point `vercel.json` at Render (optional)

On your machine (or in GitHub’s web editor):

1. Open `phase4/mfr_phase4/static/vercel.json`.
2. Replace **`YOUR_RENDER_SERVICE`** with your Render subdomain **only** (no `https://`).

   Example — if your API is `https://mutual-fund-rag-api.onrender.com`, use:

   `mutual-fund-rag-api.onrender.com`

3. Commit and push:

   ```bash
   git add phase4/mfr_phase4/static/vercel.json
   git commit -m "Point Vercel rewrites at Render free API"
   git push origin main
   ```

### C2. Create the Vercel project

1. [Vercel Dashboard](https://vercel.com/dashboard) → **Add New…** → **Project**.
2. Import the **same** GitHub repo.
3. **Configure Project**:

   | Field | Value |
   |--------|--------|
   | **Framework Preset** | Other |
   | **Root Directory** | `phase4/mfr_phase4/static` ← **Edit** and set this |
   | **Build Command** | *(leave empty)* |
   | **Output Directory** | *(leave default / empty)* |

4. **Environment Variables** — none required for the static UI (rewrites use `vercel.json`).
5. Click **Deploy**.

### C3. Open the UI

Use the production URL Vercel shows, e.g. `https://mutual-fund-rag-xyz.vercel.app`.

1. Open the site.
2. Ask: *What is the minimum SIP for HDFC ELSS?*
3. Open browser **DevTools → Network** → confirm `POST /v1/chat/respond` returns **200**.

If you see **502** or **timeout**, wake the Render API first by opening `/health` on Render, wait ~30s, then try the chat again.

---

## Part D — Checklist

| Step | Done? |
|------|--------|
| Render Web Service on **Free** plan | ☐ |
| `GROQ_API_KEY` set on Render | ☐ |
| `GET /health` returns ok on Render URL | ☐ |
| Ran `python -m mfr_phase1` in Render Shell | ☐ |
| Updated `vercel.json` with Render hostname | ☐ |
| Vercel root = `phase4/mfr_phase4/static` | ☐ |
| Chat works on Vercel URL | ☐ |

---

## Part E — When things break (Free tier)

| Problem | What to do |
|---------|------------|
| Chat always refuses / empty answers | Re-run **B4** ingest in Render Shell. |
| 500 after redeploy | Data was wiped — run ingest again (**B4**). |
| Very slow first message | Normal — Render Free was asleep; hit `/health` then `/ready` first. |
| **502** from Vercel | Set `window.MFR_API_BASE` in `config.js` to your Render URL (see C1). |
| `/ready` shows `ready: false` | Wrong `CHROMA_PATH` or old deploy — use `./deploy/chroma_data` and redeploy. |
| Ingest OOM in Shell | Retry; or build `chroma_data` locally and use GitHub Actions artifact (advanced). |
| Vercel chat 404 on `/v1/...` | Wrong **Root Directory** or `vercel.json` hostname typo. |

---

## Optional: Blueprint on Free

You can use **`render.free.yaml`** at the repo root (no disk, `plan: free`). In Render → **New → Blueprint**, connect the repo; if Render does not let you pick the file, use **Part B (manual)** instead.
