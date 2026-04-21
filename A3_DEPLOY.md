# VoyageAI — A3 deployment checklist

The A3 refinement splits VoyageAI into two deployables:

| Component | Platform | What it runs | Persists |
|-----------|----------|--------------|----------|
| Frontend  | Streamlit Cloud | `app.py` (unchanged hosting) | nothing |
| Backend   | Railway         | `backend/` (FastAPI + SQLite + Chroma) | `/data` volume |

The frontend degrades gracefully: if `BACKEND_URL` is not set, every backend-backed
feature silently disables and the app runs exactly like A2.

---

## 1. Railway — backend service

### 1.1 Create the service

1. New project → Deploy from GitHub → pick this repo.
2. Settings → Source → **Config path**: `backend/railway.toml`.
   (That file points Railway at `backend/Dockerfile` and runs
   `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.)
3. Healthcheck path: `/health` (already set in `railway.toml`).

### 1.2 Attach a volume

Dashboard → Volumes → Add → mount path **`/data`**.
The Dockerfile sets `VOYAGEAI_DATA_DIR=/data`, so the SQLite file
(`/data/voyageai.db`) and the Chroma index (`/data/chroma/`) both land on
the volume and survive redeploys.

### 1.3 Environment variables

| Key | Value |
|-----|-------|
| `OPENAI_API_KEY` | your key |
| `CORS_ORIGINS`   | `https://<your-streamlit-url>,http://localhost:8501` |
| `EMBED_MODEL`    | `text-embedding-3-small` (default) |
| `CHAT_MODEL`     | `gpt-4o-mini` (default) |
| `RAG_TOP_K`      | `5` (default) |

Amadeus / Google keys are **not** needed on Railway — only the agent tool
paths call them, and those reuse the frontend keys via the imported
`api_functions.py` (which reads from env / `st.secrets`). If you want the
agent to hit live APIs from the backend, also set
`AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `GOOGLE_API_KEY`.

### 1.4 Populate the RAG index

Once the service is up, open Railway → Deployments → latest → **Run a one-off command**:

```
python -m backend.rag.ingest
```

This scrapes Wikipedia for the 40 default cities, generates the curated
tips layer via OpenAI (cached as JSON on disk so reruns are cheap), embeds
everything, and upserts into Chroma at `/data/chroma/`. Expect ~5–10 min
the first time, ~30 s on subsequent runs thanks to the cache.

To ingest a smaller subset while testing:

```
python -m backend.rag.ingest --cities Rome Paris Tokyo --no-curated
```

### 1.5 Smoke test

```
curl https://<railway-url>/health
# → {"status":"ok"}

curl -X POST https://<railway-url>/trips \
  -H 'X-VoyageAI-User: 00000000-0000-0000-0000-000000000001' \
  -H 'Content-Type: application/json' \
  -d '{"dest_city":"Rome","depart_date":"2026-05-01","return_date":"2026-05-05","travelers":2,"budget_eur":1500}'
```

Expected: a JSON trip with an `id`.

---

## 2. Streamlit Cloud — frontend

In the Streamlit Cloud app settings → Secrets, **add** one line:

```toml
BACKEND_URL = "https://<your-railway-url>"
```

All existing secrets (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `AMADEUS_*`) stay
as-is. Push a rebuild.

Verify:

1. Sidebar → **Plan My Trip** — the URL should now contain `?uid=<uuid>`.
2. Open the app in a new incognito tab — the `uid` differs.
3. Vote on the Itinerary tab with both identities — the running tally updates.
4. Chat tab → toggle **Use RAG** on — answers should show a **Sources** expander.
5. **🤖 AI Agent** tab → run the default goal — you should see a summary,
   a structured day plan, and a trace of tool calls.

---

## 3. Files touched in A3 (high level)

Added:

```
backend/                         # FastAPI service
├── main.py, config.py, database.py, models.py, schemas.py, deps.py
├── routers/                     # users, trips, votes, feedback, itineraries, chat, agent
├── services/                    # openai_client, chat_service, itinerary_service, agent_service
├── rag/                         # store, retriever, ingest (Wikipedia + curated tips)
├── Dockerfile, railway.toml, requirements.txt, .env.example
backend_client.py                # thin HTTP wrapper the frontend uses
ui_widgets.py                    # reusable Streamlit widgets (voting, feedback, sources, agent trace)
A3_DEPLOY.md                     # this file
```

Modified:

```
app.py                           # bootstraps user_id, persists Trip, adds votes +
                                 # thumbs feedback on 4 tabs, RAG toggle on Chat,
                                 # structured-itinerary view, new 🤖 AI Agent tab
.gitignore                       # adds backend/.env, backend/data/, chroma/, rag_cache/
```
