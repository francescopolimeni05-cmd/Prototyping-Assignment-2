# ✈️ VoyageAI — AI-Powered Travel Planner

Streamlit prototype for an AI-powered travel agency that aggregates real-time data from **6 APIs** and uses **LLMs in 5 non-straightforward ways** to help users plan complete trips in one place.

> **PDAI Assignment 2** — Prototyping with LLMs

## 🎯 The Problem

Planning a trip today means jumping between 5+ websites: Google Flights for flights, Booking.com for hotels, TripAdvisor for attractions, Google Maps for restaurants, and a weather app. VoyageAI consolidates everything into a single AI-powered interface — like having a personal travel agent powered by AI.

## ✨ 13 Tabs

| Tab | Data Source | What it does |
|-----|-----------|--------------|
| ✈️ Flights | **Amadeus API** | Search real flights across 400+ airlines (economy, premium, business) |
| 🏨 Hotels | **OpenAI + Google Places** | AI-recommended hotels with real Google photos, ⭐ ratings, price levels & reviews |
| 🌤️ Weather | **Google Weather API** | Current conditions + 10-day forecast + 48h hourly chart |
| 🏛️ Attractions | **OpenAI + Google Places** | Famous landmarks with real photos, star ratings & Google Maps links |
| 🍽️ Restaurants | **OpenAI + Google Places** | Restaurants with Google price levels (€/€€/€€€), photos & ratings |
| 🌙 Nightlife | **OpenAI + Google Places** | Bars, clubs & cafes with real Google data |
| 📋 Itinerary | **OpenAI** | AI-generated day-by-day plan using all collected data + Google ratings |
| 💬 Chat | **OpenAI (multi-turn)** | Travel chatbot with RAG-like context from all trip data |
| 💰 Budget AI | **OpenAI (structured JSON)** | Budget optimizer with charts, tips, and savings suggestions |
| 🎵 TikTok | **OpenAI** | TikTok travel content discovery with direct search links |
| 💱 Currency | **Frankfurter API** | Real-time exchange rates + converter |
| 🚇 Directions | **Google Directions + Maps Embed** | Route planning with embedded Google Maps |
| 🎒 Packing | **OpenAI** | Smart packing list based on weather + activities |

## 🤖 5 Non-Straightforward LLM Features

### 1. Hotels/Restaurants/Attractions → Google Places Validation Pipeline
OpenAI generates place names in structured JSON → Python parses → calls Google Places API for each → enriches with real photos, ratings, price levels, reviews. The LLM output is **post-processed and validated** against Google data.

### 2. Travel Chatbot (Multi-turn + RAG-like)
Before each message, the app builds a context string from ALL collected data (flights, hotels with Google ratings, restaurants with Google price levels, weather, itinerary, user selections). This is injected into the system prompt — a **RAG-like pattern** using the app's own data.

### 3. Budget Optimizer (Structured JSON → Charts)
LLM generates complex JSON (score, tips with priority, daily breakdown, alternatives) → Python parses into **5 different visualizations**: score badge, metrics, expanders, bar chart by category, progress bar, alternatives table.

### 4. AI Itinerary with Enriched Context
The itinerary prompt receives restaurants with **Google price levels**, attractions with **Google ratings**, the user's **selected flight and hotel**, and **real weather data**. It uses all of this to generate a contextual, personalized plan.

### 5. TikTok Content Discovery
LLM generates structured data (search queries, creators, trending topics, video ideas) → Python creates **clickable TikTok links**, profile buttons, and categorized content cards.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (app.py)                      │
│  13 tabs · Booking.com design · 23+ widget types             │
└──────────┬───────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────┐
│               API FUNCTIONS (api_functions.py)                │
│                      28+ functions                            │
├──────────┬────────────┬────────────┬──────────┬──────────────┤
│ Amadeus  │ Google     │ Google     │ OpenAI   │ Frankfurter  │
│ Flights  │ Weather +  │ Places +   │ GPT-4o-  │ Exchange     │
│ (OAuth2) │ Geocoding  │ Directions │ mini     │ Rates        │
│          │            │ + Embed    │ (5 uses) │ (no key)     │
└──────────┴────────────┴────────────┴──────────┴──────────────┘
```

## 🚀 Quick Start

```bash
git clone https://github.com/francescopolimeni05-cmd/Prototyping-Assignment-2.git
cd Prototyping-Assignment-2
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
AMADEUS_CLIENT_ID = "your_id"
AMADEUS_CLIENT_SECRET = "your_secret"
GOOGLE_API_KEY = "your_key"
OPENAI_API_KEY = "sk-your_key"
```

Then: `streamlit run app.py`

## 🔑 APIs (6 total)

| API | Used For | Key needed |
|-----|----------|-----------|
| Amadeus | Flight search | Yes |
| Google Weather | Forecasts | Yes (same key) |
| Google Places (New) | Photos, ratings, reviews, price levels | Yes (same key) |
| Google Directions + Embed | Route planning, embedded maps | Yes (same key) |
| OpenAI | Content generation, chatbot, budget, itinerary, TikTok, packing | Yes |
| Frankfurter | Exchange rates | No (free, no key) |

**Google Cloud:** Enable Weather API, Geocoding API, Places API (New), Directions API, Maps Embed API.

## 🎨 Design

Booking.com-inspired dark blue theme (#003580) with yellow accents (#febb02), white cards on light gray background, embedded Google Maps, real Google photos and star ratings.

## 📁 Project Structure

```
VoyageAI/
├── app.py                  # Streamlit UI — 13 tabs, 1000+ lines
├── api_functions.py        # 28+ API functions
├── requirements.txt        # streamlit, requests, pandas
├── secrets.toml.example    # Template for API keys
├── .gitignore              # Protects secrets
└── README.md
```

## 🔒 Security

API keys stored only in `.streamlit/secrets.toml` (gitignored). On Streamlit Cloud, keys are in encrypted Secrets Management. Keys never appear in code or repository.

---

*Built by Francesco Polimeni — PDAI Assignment 2, March 2026*