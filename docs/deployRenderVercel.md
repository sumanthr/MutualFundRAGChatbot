# Deploy backend (Render) and frontend (Vercel)

This is a short runbook. Full context: [deploymentPlan.md](./deploymentPlan.md).

## 1. Render (backend)

### Option A — Blueprint (recommended)

1. In [Render](https://render.com), choose **New +** → **Blueprint**.
2. Connect GitHub and select repo **`MutualFundRAGChatbot`** (or your fork).
3. Render reads **`render.yaml`** at the repo root.
4. When prompted, set secret **`GROQ_API_KEY`** (your Groq API key).
5. Create resources. Note the web service URL, e.g. `https://mutual-fund-rag-api.onrender.com`.

**After deploy**

- Open **Shell** on the service and run once (populates Chroma on the persistent disk):

  ```bash
  mkdir -p /var/data/chroma_data
  python -m mfr_phase1 --chroma-path /var/data/chroma_data
  ```

- Or copy a `chroma_data` tree from a GitHub Actions **chroma-index** artifact into `/var/data/chroma_data`.

- Hit **`GET /health`** on your service URL.

### Option B — Manual Web Service

- **Runtime:** Python 3.11  
- **Build:** `pip install --upgrade pip setuptools wheel && pip install .`  
- **Start:** `uvicorn mfr_phase4.app:app --host 0.0.0.0 --port $PORT`  
- **Env vars:** match `render.yaml` (`CHROMA_PATH`, `THREAD_DB_PATH`, `GROQ_API_KEY`, …).  
- **Disk:** mount e.g. `/var/data` and point `CHROMA_PATH` / `THREAD_DB_PATH` there.

### Plan note

`render.yaml` uses **`plan: starter`** so a **persistent disk** can be attached. If you switch to **Free**, remove the `disk` block and expect **ephemeral** storage (not suitable for production Chroma).

---

## 2. Vercel (frontend)

The UI lives under **`phase4/mfr_phase4/static/`**.

1. In [Vercel](https://vercel.com), **Add New… → Project** → import the same GitHub repo.
2. Under **Root Directory**, set **`phase4/mfr_phase4/static`** (important).
3. **Framework preset:** Other (static). No build command required.
4. Edit **`vercel.json`** in that folder: replace **`YOUR_RENDER_SERVICE`** with your Render hostname **without** `https://` (e.g. `mutual-fund-rag-api.onrender.com`). Commit and push, or edit in GitHub before connecting.
5. Deploy. Open the Vercel URL and test the chat; `/v1/*` is proxied to Render via rewrites.

If you prefer not to commit the real hostname, delete `vercel.json` from the repo and add the same **Rewrites** in Vercel → Project → **Settings → Rewrites**.

---

## 3. Verify

| Check | URL |
|--------|-----|
| API health | `https://<render-host>/health` |
| UI | `https://<vercel-host>/` |
| Chat | Send a question; in browser DevTools → Network, confirm `/v1/chat/respond` returns 200 |

---

## 4. GitHub Actions artifacts

Scheduled ingest produces **Chroma artifacts on GitHub**, not on Render. To refresh production vectors, either run **`python -m mfr_phase1`** in the Render shell (see above) or copy the artifact onto the Render disk. See **deploymentPlan.md** §5–§8.
