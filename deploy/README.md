# Deploy bundle (no Render Shell required)

`chroma_data/` here is a **pre-built vector index** copied from local ingest. It is shipped in git so **Render Free** can serve chat without Shell access.

Regenerate after re-indexing locally:

```bash
python -m mfr_phase1 --chroma-path ./chroma_data
./scripts/export-deploy-chroma.sh
git add deploy/chroma_data && git commit -m "Refresh deploy chroma index"
```

On Render, set **`CHROMA_PATH=./deploy/chroma_data`**.
