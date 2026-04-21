# ✈️ VoyageAI — AI-Powered Travel Planner

Full-stack prototype for an AI-powered travel agency. Streamlit frontend + FastAPI backend, aggregating real-time data from **6 APIs**, using **LLMs in 7+ non-straightforward ways**, with a **RAG knowledge base**, an **AI agent** (OpenAI function calling), **persistence** (SQLite), and **community feedback** (voting + thumbs).

> **PDAI Assignment 3** — Refinement of Assignment 2 · built by Francesco Polimeni · ESADE, April 2026

## 🎯 The Problem

Planning a trip today means jumping between 5+ websites: Google Flights for flights, Booking.com for hotels, TripAdvisor for attractions, Google Maps for restaurants, and a weather app. VoyageAI consolidates everything into a single AI-powered interface — like having a personal travel agent powered by AI — and in A3 adds a persistent backend so users can save trips, vote on plans, give feedback, ask grounded questions over a travel knowledge base, and delegate the whole planning job to an autonomous agent.

## 🆕 What's new in Assignment 3

1. **FastAPI backend** deployed on Railway — separate from the Streamlit frontend, with SQLite persistence on a mounted volume.
2. **Cookie-based user identity** (`?uid=<uuid>` + `X-VoyageAI-User` header) so every user has a persistent profile without a login.
3. **Trip persistence** — saved trips are stored in SQLite and re-loadable across sessions.
4. **RAG chatbot** powered by ChromaDB (~1 800 chunks across 40 cities, sourced from Wikipedia + a curated tips layer). Answers cite the retrieved sources inline.
5. **Voting widget** — "AI-generated vs. manual itinerary" head-to-head with aggregate percentages.
6. **Thumbs-up/down feedback** with optional notes on 4 tabs (itinerary, hotels, restaurants, attractions).
7. **Structured multi-day itinerary** — per-day tabs with morning / afternoon / evening blocks, travel time, cost, notes, and a "Regenerate this day" button.
8. **AI Agent tab** (OpenAI function calling) — give it a high-level goal and it autonomously calls `search_flights`, `search_hotels`, `get_weather`, `retrieve_docs`, `compose_itinerary`, streaming a tool trace back to the UI.
9. **Graceful fallbacks everywhere** — Amadeus rate-limited? The app shows a banner and serves deterministic mock flights so the demo keeps working.
10. **Graceful degradation** — if `BACKEND_URL` isn't configured, the frontend silently disables backend-backed features and runs exactly like the A2 prototype.

## ✨ 13 Tabs + AI Agent

| Tab | Data Source | What it does |
|-----|-----------|--------------|
| ✈️ Flights | **Amadeus API** (+ mock fallback) | Search real flights across 400+ airlines, with a banner when falling back to simulated data |
| 🏨 Hotels | **OpenAI + Google Places** | AI-recommended hotels with real Google photos, ⭐ ratings, price levels & reviews |
| 🌤️ Weather | **Google Weather API** | Current conditions + 10-day forecast + 48h hourly chart |
| 🏛️ Attractions | **OpenAI + Google Places** | Famous landmarks with real photos, star ratings & Google Maps links |
| 🍽️ Restaurants | **OpenAI + Google Places** | Restaurants with Google price levels (€/€€/€€€), photos & ratings |
| 🌙 Nightlife | **OpenAI + Google Places** | Bars, clubs & cafes with real Google data |
| 📋 Itinerary | **OpenAI** | Two flavors: AI markdown day-by-day **plus** a structured multi-day plan with per-day regeneration |
| 💬 Chat | **OpenAI + ChromaDB RAG** | Multi-turn chatbot with optional RAG over a 40-city travel KB; answers cite sources |
| 💰 Budget AI | **OpenAI (structured JSON)** | Budget optimizer with charts, tips, and savings suggestions |
| 🎵 TikTok | **OpenAI** | TikTok travel content discovery with direct search links |
| 💱 Currency | **Frankfurter API** | Real-time exchange rates + converter |
| 🚇 Directions | **Google Directions + Maps Embed** | Route planning with embedded Google Maps |
| 🎒 Packing | **OpenAI** | Smart packing list based on weather + activities |
| 🤖 AI Agent | **OpenAI function calling** | Autonomous planner — orchestrates flight, weather, RAG and compose tools from a natural-language goal |

## 🤖 7 Non-Straightforward LLM Features

### 1. Hotels / Restaurants / Attractions → Google Places validation pipeline
OpenAI generates place names in structured JSON → Python parses → calls Google Places API for each → enriches with real photos, ratings, price levels, reviews. LLM output is **post-processed and validated** against Google data.

### 2. Travel chatbot with RAG
A toggle on the Chat tab switches between two modes. RAG-off: the app injects the current trip context (flights, hotels with Google ratings, restaurants with price levels, weather, itinerary) into the system prompt. RAG-on: the backend embeds the query, retrieves the top-k chunks from ChromaDB (filtered by destination city, with an unfiltered fallback), and the LLM answers with a `Sources (n)` expander listing the citations.

### 3. Budget optimizer (structured JSON → charts)
LLM generates complex JSON (score, tips with priority, daily breakdown, alternatives) → Python parses into **5 different visualizations**: score badge, metrics, expanders, bar chart by category, progress bar, alternatives table.

### 4. Structured multi-day itinerary (schema-validated)
The backend asks the LLM for strict JSON with `days[]`, each day having three blocks (morning/afternoon/evening) with activity, location, travel minutes, estimated cost, and notes. The response is normalised across three possible LLM shapes and Pydantic-validated before rendering as per-day Streamlit tabs. Each day has a one-click "Regenerate this day" button that rewrites only that day while keeping continuity with the others.

### 5. TikTok content discovery
LLM generates structured data (search queries, creators, trending topics, video ideas) → Python creates **clickable TikTok links**, profile buttons, and categorized content cards.

### 6. AI Agent (OpenAI function calling)
A single natural-language goal ("Plan me a 3-day trip to Rome next week from Barcelona, budget €1 000") drives a multi-step loop: the model decides which tool to call (`search_flights`, `search_hotels`, `get_weather`, `retrieve_docs`, `compose_itinerary`), the backend executes it, the result is fed back, and the model decides the next step. On the final iteration the backend forces `tool_choice = compose_itinerary` so the agent always produces a plan. A safety net reconstructs trip parameters from the goal if the agent still fails. The UI shows a step-by-step trace.

### 7. LLM output sanitization
A small regex helper strips fake markdown links like `[Colosseo](Colosseo)` that LLMs occasionally emit (they render as broken internal anchors) while preserving real `http://`, `https://`, `mailto:` links. Applied in both the legacy markdown itinerary and the structured one.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (app.py)                      │
│  14 tabs · Booking.com design · ui_widgets.py components     │
└──────────┬───────────────────────────────────────────────────┘
           │            ┌──────────────────────┐
           │            │  backend_client.py   │  ← thin HTTP wrapper,
           │            │  (optional)          │    silently no-ops if
           │            └──────────┬───────────┘    BACKEND_URL unset
           │                       │
┌──────────▼──────────┐   ┌────────▼──────────────────────────────┐
│  api_functions.py   │   │   FASTAPI BACKEND  (Railway)          │
│  28+ direct calls   │   │   backend/main.py                     │
│  to external APIs   │   │                                       │
│                     │   │   Routers: users, trips, votes,       │
│                     │   │   feedback, itineraries, chat, agent  │
│                     │   │                                       │
│                     │   │   Services: openai_client, chat,      │
│                     │   │   itinerary, agent (function calling) │
│                     │   │                                       │
│                     │   │   RAG: Chroma + ingest (Wikipedia +   │
│                     │   │   curated tips, 40 cities, ~1 800     │
│                     │   │   chunks)                             │
│                     │   │                                       │
│                     │   │   SQLite on /data volume:             │
│                     │   │   users, trips, votes, feedback       │
│                     │   └───────────────────────────────────────┘
│                     │
├─────────┬───────────┼────────────┬──────────┬──────────────┤
│ Amadeus │ Google    │ Google     │ OpenAI   │ Frankfurter  │
│ Flights │ Weather + │ Places +   │ GPT-4o-  │ Exchange     │
│ (OAuth) │ Geocoding │ Directions │ mini     │ Rates        │
└─────────┴───────────┴────────────┴──────────┴──────────────┘
```

Two deployables:

| Component | Platform        | Persists                              |
|-----------|-----------------|---------------------------------------|
| Frontend  | Streamlit Cloud | nothing (client state only)           |
| Backend   | Railway         | `/data` volume (SQLite + Chroma index)|

## 🚀 Quick Start (local)

```bash
git clone https://github.com/francescopolimeni05-cmd/Prototyping-Assignment-2.git
cd Prototyping-Assignment-2
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
AMADEUS_CLIENT_ID = "your_id"
AMADEUS_CLIENT_SECRET = "your_secret"
GOOGLE_API_KEY = "your_key"
OPENAI_API_KEY = "sk-your_key"
BACKEND_URL = "http://localhost:8000"   # optional — omit to run A2-only mode
```

Run the backend (terminal 1):
```bash
export OPENAI_API_KEY=sk-...
uvicorn backend.main:app --reload --port 8000
python -m backend.rag.ingest --cities Rome Paris Tokyo --no-curated   # optional: seed a small KB
```

Run the frontend (terminal 2):
```bash
streamlit run app.py
```

## ☁️ Production Deployment

See **[A3_DEPLOY.md](A3_DEPLOY.md)** for the full Railway + Streamlit Cloud checklist (volume mounting, env vars, RAG ingest, smoke tests).

Live demo:
- Frontend: https://prototyping-assignment-2-rye6ysuweinsofejcqmwbb.streamlit.app/
- Backend: Railway (FastAPI at `/health`, `/docs`)

## 🔑 APIs (6 total)

| API | Used For | Key needed |
|-----|----------|-----------|
| Amadeus | Flight search (with deterministic mock fallback) | Yes |
| Google Weather | Forecasts | Yes (same key) |
| Google Places (New) | Photos, ratings, reviews, price levels | Yes (same key) |
| Google Directions + Embed | Route planning, embedded maps | Yes (same key) |
| OpenAI | Content generation, chatbot, budget, itinerary, TikTok, packing, agent, embeddings | Yes |
| Frankfurter | Exchange rates | No (free, no key) |

**Google Cloud:** Enable Weather API, Geocoding API, Places API (New), Directions API, Maps Embed API.

## 🎨 Design

Booking.com-inspired dark blue theme (#003580) with yellow accents (#febb02), white cards on light gray background, embedded Google Maps, real Google photos and star ratings. Feedback widgets (votes, thumbs) render inline with progressive disclosure — they never block the primary flow.

## 📁 Project Structure

```
VoyageAI/
├── app.py                     # Streamlit UI — 14 tabs, ~1 500 lines
├── api_functions.py           # 28+ external API functions (shared by FE & BE)
├── ui_widgets.py              # Voting, thumbs, RAG sources, structured itinerary, agent trace
├── backend_client.py          # HTTP wrapper — no-ops gracefully if BACKEND_URL unset
├── backend/
│   ├── main.py                # FastAPI app + CORS
│   ├── config.py              # Env / secrets resolution
│   ├── database.py            # SQLAlchemy engine + session
│   ├── models.py              # SQLAlchemy models (User, Trip, Vote, Feedback)
│   ├── schemas.py             # Pydantic schemas (incl. StructuredItinerary)
│   ├── deps.py                # Dependency-injected user resolution
│   ├── routers/               # users, trips, votes, feedback, itineraries, chat, agent
│   ├── services/              # openai_client, chat, itinerary, agent (function calling)
│   ├── rag/                   # Chroma store, retriever, ingest pipeline
│   ├── Dockerfile
│   ├── railway.toml
│   └── requirements.txt
├── requirements.txt           # Streamlit frontend deps
├── secrets.toml.example       # Template for API keys
├── A3_DEPLOY.md               # Full deployment runbook
├── .gitignore
└── README.md
```

## 🔒 Security

API keys stored only in `.streamlit/secrets.toml` (gitignored) and Railway env vars. On Streamlit Cloud, keys live in encrypted Secrets Management. The backend validates every request against `CORS_ORIGINS` and resolves the user via the `X-VoyageAI-User` header. Keys never appear in code or repository.

---

*Built by Francesco Polimeni — PDAI Assignment 3 refinement, April 2026*
