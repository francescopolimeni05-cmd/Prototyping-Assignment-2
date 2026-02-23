# ✈️ VoyageAI — AI-Powered Travel Planner

Streamlit prototype for an AI-powered travel agency that aggregates real-time data from **4 APIs** to help users plan complete trips in one place.

> **PDAI Assignment 1** — Prototyping with Streamlit

## 🎯 The Problem

Planning a trip today means jumping between 5+ websites: Google Flights for flights, Booking.com for hotels, TripAdvisor for attractions, Google Maps for restaurants, and a weather app. VoyageAI consolidates everything into a single AI-powered interface.

## ✨ Features

| Tab | Data Source | What it does |
|-----|-----------|--------------|
| ✈️ Flights | **Amadeus API** | Search real flights across 400+ airlines (economy, premium, business) |
| 🏨 Hotels | **OpenAI + Google Places** | AI-recommended hotels with real Google photos, ⭐ ratings & reviews |
| 🌤️ Weather | **Google Weather API** | Current conditions + 10-day forecast + 48h hourly chart (DeepMind AI) |
| 🏛️ Attractions | **OpenAI + Google Places** | Famous landmarks with real photos, star ratings & Google Maps links |
| 🍽️ Restaurants | **OpenAI + Google Places** | Restaurants by cuisine preference with photos, ratings & reviews |
| 🌙 Nightlife | **OpenAI + Google Places** | Bars, clubs & cafes with real Google data |
| 📋 Itinerary | **OpenAI GPT-4o-mini** | AI-generated day-by-day plan using all collected trip data |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (app.py)                 │
│  Sidebar (inputs) │ Tabs (flights/hotels/weather/...)   │
│  21 widget types  │ Custom CSS + Google Fonts            │
└─────────┬───────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│              API FUNCTIONS (api_functions.py)            │
│                     20 functions                         │
├─────────────┬──────────────┬──────────────┬─────────────┤
│  Amadeus    │ Google       │ Google       │  OpenAI     │
│  Flights    │ Weather +    │ Places (New) │  GPT-4o-    │
│  (OAuth2)   │ Geocoding    │ Photos +     │  mini       │
│             │              │ Ratings +    │  (JSON mode)│
│  Real flight│ Real-time    │ Reviews      │  Hotels,    │
│  search &   │ weather +    │              │  restaurants│
│  pricing    │ forecasts    │ Enriches ALL │  attractions│
│             │              │ AI results   │  nightlife, │
│             │              │ with real    │  itinerary  │
│             │              │ Google data  │             │
└─────────────┴──────────────┴──────────────┴─────────────┘
```

**Key design:** OpenAI generates recommendations with real place names → Google Places enriches each place with real photos, verified star ratings, review counts, user reviews, and Google Maps links. This creates a **validation loop** ensuring AI suggestions are real.

## 🚀 Quick Start

```bash
git clone https://github.com/francescopolimeni05-cmd/Prototyping-Assignment-1.git
cd Prototyping-Assignment-1
pip install -r requirements.txt
```

### Configure API Keys

Create `.streamlit/secrets.toml` (this file is gitignored):

```toml
AMADEUS_CLIENT_ID = "your_id"
AMADEUS_CLIENT_SECRET = "your_secret"
GOOGLE_API_KEY = "your_key"
OPENAI_API_KEY = "sk-your_key"
```

Then run:
```bash
streamlit run app.py
```

## 🔑 API Keys (all free tier)

| API | Sign Up | Free Tier | Used For |
|-----|---------|-----------|----------|
| Amadeus | [developers.amadeus.com](https://developers.amadeus.com/) | 2,000 req/month | Flight search |
| Google Cloud | [console.cloud.google.com](https://console.cloud.google.com/) | $200 credit/month | Weather, Geocoding, Places photos/ratings |
| OpenAI | [platform.openai.com](https://platform.openai.com/) | Pay-as-you-go (~$0.01/search) | Hotels, restaurants, attractions, itinerary |

**Google Cloud setup:** Enable these 3 APIs in your project:
- Weather API
- Geocoding API
- Places API (New)

## 📁 Project Structure

```
VoyageAI/
├── app.py                  # Streamlit UI — 7 tabs, sidebar, custom CSS
├── api_functions.py        # 20 API functions — Amadeus, Google, OpenAI
├── requirements.txt        # streamlit, requests, pandas
├── secrets.toml.example    # Template for API keys
├── .gitignore              # Protects secrets.toml
└── README.md
```

## 🎨 Streamlit Widgets Used (21 types)

**Input widgets:**
`st.text_input` · `st.selectbox` · `st.date_input` · `st.slider` · `st.number_input` · `st.select_slider` · `st.multiselect` · `st.radio` · `st.button`

**Layout widgets:**
`st.sidebar` · `st.columns` · `st.tabs` · `st.expander`

**Data display:**
`st.metric` · `st.progress` · `st.bar_chart` · `st.line_chart` · `st.map` · `st.image` · `st.download_button`

**Feedback:**
`st.spinner` · `st.toast` · `st.success` · `st.warning` · `st.error` · `st.info` · `st.caption`

**Other:**
`st.session_state` (caching) · `st.markdown` with custom HTML/CSS · Google Fonts (Playfair Display)

## 🔧 Key Technical Decisions

- **API key security:** Keys stored only in `.streamlit/secrets.toml` (gitignored), never exposed in UI
- **Session state caching:** All API results cached in `st.session_state` — switching tabs doesn't re-fetch data
- **OpenAI JSON mode:** Uses `response_format: json_object` for reliable structured responses
- **Google Places enrichment:** Every AI-generated place is enriched with real Google data (photos, ratings, reviews)
- **Separation of concerns:** UI logic (`app.py`) separated from API logic (`api_functions.py`) — 20 modular functions
- **Error handling:** All API calls wrapped in try/catch with user-friendly error messages
- **Budget flow:** Selected flight/hotel costs flow into the itinerary tab, updating remaining daily budget

## 📸 Screenshots

The app features:
- 🖼️ Hero city photo from Google Places
- ⭐ Real star ratings with review counts on every place
- 📸 Google Photos for hotels, restaurants, attractions, bars
- 📊 Flight price comparison chart
- 🌡️ Temperature trend line chart
- 📍 Interactive map of destination
- 💬 Real Google user reviews

---

*Built by Francesco Polimeni — PDAI Assignment 1, February 2026*
