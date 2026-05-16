# Deploy backend (Render) and frontend (Vercel)

Step-by-step checklist. Architecture and GitHub Actions context: [deploymentPlan.md](./deploymentPlan.md).

---

## 0. Push the latest code to GitHub

From your machine (replace the path if needed):

```bash
cd /path/to/MutualFundRAG
git status
git add -A
git commit -m "Deploy: Render backend, Vercel static UI, retrieval fix"
git push origin main
```

Use the repo you connected to Render/Vercel (for example `MutualFundRAGChatbot` on GitHub).

---

## 1. Render (backend / API)

### Option A — Blueprint (recommended)

1. Open [Render](https://render.com) → **New +** → **Blueprint**.
2. Connect **GitHub** and select your repository.
3. Render reads **`render.yaml`** at the repo root and proposes a **Web Service** plus a **persistent disk** mounted at `/var/data`.
4. When prompted, set the secret **`GROQ_API_KEY`** (your key from [Groq Console](https://console.groq.com/)).
5. Create resources and wait for the first deploy.

6. **Note your service hostname**, for example `mutual-fund-rag-api.onrender.com` (no `https://`). You will paste this into Vercel’s `vercel.json` (see §2).

### First deploy: index Chroma on the disk

The API needs a populated Chroma directory at **`CHROMA_PATH`** (`/var/data/chroma_data` in `render.yaml`).

1. In Render, open the web service → **Shell**.
2. Run:

   ```bash
   mkdir -p /var/data/chroma_data
   python -m mfr_phase1 --chroma-path /var/data/chroma_data
   ```

   The first run downloads the embedding model; it can take several minutes.

3. Alternatively, unzip a `chroma_data` tree from a GitHub Actions **chroma-index** artifact into `/var/data/chroma_data`.

4. Confirm: open **`https://<your-service>.onrender.com/health`** in a browser — expect `{"status":"ok"}`.

### Option B — Manual Web Service

If you do not use a Blueprint:

| Setting | Value |
|--------|--------|
| Runtime | Python 3.11 |
| Build command | `bash scripts/render-build.sh` |
| Start command | `uvicorn mfr_phase4.app:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

Set the same environment variables as in **`render.yaml`** (especially `CHROMA_PATH`, `THREAD_DB_PATH`, `GROQ_API_KEY`, and the `HF_HOME` / cache paths if you use a disk).

### Plan note

**`render.yaml`** uses **`plan: starter`** so a **persistent disk** can be attached. The **Free** tier does not support this disk; remove the `disk` block and treat storage as **ephemeral** (fine for demos only).

### Cold starts

The first chat after idle may be slow while the embedding model loads. Subsequent requests on the same instance are faster.

---

## 2. Vercel (frontend / static UI)

Static files live in **`phase4/mfr_phase4/static/`** (`index.html`, `styles.css`, `app.js`). The UI calls **`/v1/...`** on the **same origin**; **`vercel.json`** rewrites those paths to your Render API.

### Steps

1. Open [Vercel](https://vercel.com) → **Add New… → Project** → import the **same** GitHub repo.
2. **Root Directory:** `phase4/mfr_phase4/static` (required).
3. **Framework preset:** Other (static site). Leave **Build Command** empty unless you add one later.
4. **Point rewrites at Render**

   - Edit **`phase4/mfr_phase4/static/vercel.json`** in the repo: replace every **`YOUR_RENDER_SERVICE`** with your Render **subdomain only** (example: `mutual-fund-rag-api` if the URL is `https://mutual-fund-rag-api.onrender.com`).
   - Commit and push, then trigger **Redeploy** on Vercel (or let the git integration deploy).

   If you prefer **not** to commit the hostname, delete `vercel.json` from the repo and add equivalent **Rewrites** under Vercel → Project → **Settings → Rewrites** (same `source` / `destination` pattern as in the file).

5. Deploy and open the **Vercel production URL**.

### Why rewrites?

`app.js` uses **relative** URLs (`/v1/chat/...`) when the page is served over `https`, so the browser talks to your Vercel domain. Rewrites forward those requests to Render without changing CORS on the API (the API already allows `*` in Phase 4).

---

## 3. Verify end-to-end

| Check | URL / action |
|--------|----------------|
| API health | `https://<render-host>/health` |
| UI | `https://<vercel-host>/` |
| Chat | Ask a question; in DevTools → **Network**, `POST /v1/chat/respond` should return **200** |

---

## 4. Environment reference (Render)

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Required for factual answers (set in dashboard as secret). |
| `CHROMA_PATH` | Chroma persist directory (on disk: `/var/data/chroma_data`). |
| `THREAD_DB_PATH` | SQLite path for chat threads (on disk: `/var/data/threads.sqlite3`). |
| `RETRIEVAL_MAX_DISTANCE` | Cosine distance cutoff (see `render.yaml`; tuned for the small corpus). |
| `HF_HOME`, `TRANSFORMERS_CACHE`, `SENTENCE_TRANSFORMERS_HOME` | Cache embedding weights on the disk between restarts. |

Local templates: **`.env.example`**.

---

## 5. GitHub Actions artifacts

Scheduled ingest uploads **Chroma** as an artifact; it is **not** pushed to Render automatically. Refresh production vectors by re-running **`python -m mfr_phase1`** in the Render shell or by copying the artifact onto `/var/data/chroma_data`. See **deploymentPlan.md** §5–§8.
