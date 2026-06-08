# Real-Time NSE Financial Data Engineering ETL Pipeline

A production-grade, end-to-end, containerized data engineering pipeline designed to ingest, clean, transform, store, and visualize stock market data from the National Stock Exchange (NSE) of India. 

This repository showcases best practices in modern data engineering, utilizing a micro-batch streaming architecture, idempotent database writes, high-speed memory caching, statistical anomaly detection, and a real-time event-driven dashboard.

---

## 🏗️ System Architecture

The pipeline consists of five decoupled service layers operating within a dedicated containerized network:

```
[ Ingestion Layer (Extract) ]
             │   (Pulls stock ticks via yfinance or GBM Simulator)
             ▼
[ Transformation Layer (Transform) ]
             │   (Cleans schemas & computes rolling SMAs, Volatility, Momentum)
             ▼
[ Storage Layer (Load) ]
      ┌──────┴──────┐
      ▼             ▼
[ PostgreSQL ]   [ Redis Cache ]
(Data Warehouse) (Pub/Sub + KV Store)
      ▲             ▲
      └──────┬──────┘
             ▼
[ Serving Layer (API - FastAPI) ]
             │   (REST endpoints + Live WebSocket Broadcast)
             ▼
[ Visualization Layer (Streamlit) ]
                 (Interactive Plotly Charts & Live Alerts)
```

1. **Extract**: A stream generator daemon fetches market ticks from Yahoo Finance (`yfinance`) or runs a **Geometric Brownian Motion (GBM)** simulator when markets are closed.
2. **Transform**: Formats data, enforces schema validation, and runs rolling calculations (SMA, volatility, momentum) plus statistical anomaly classification.
3. **Load**: Performs transaction-safe, idempotent upserts into PostgreSQL (`raw_stock_data` and `processed_metrics`). 
4. **Cache & Publish**: Stores the latest price ticks in Redis for sub-millisecond API response times and publishes records to a Redis Pub/Sub channel (`stock_updates`).
5. **Serve**: FastAPI exposes REST API endpoints and a WebSocket server. The WebSocket listens to the Redis channel and streams data to UI clients.
6. **Visualize**: Streamlit polls the API and establishes WebSocket sessions to present live charts, distribution returns, and alerts.

---

## 🛠️ Tech Stack

- **Core Language**: Python (3.11)
- **Data Wrangling**: Pandas, NumPy
- **API Framework**: FastAPI, Uvicorn, WebSockets
- **Database (OLAP/Warehouse)**: PostgreSQL 15, SQLAlchemy (with PostgreSQL-native upserts)
- **Caching & Broker**: Redis 7 (KV cache & Pub/Sub)
- **Frontend Dashboard**: Streamlit, Plotly Express
- **Containerization**: Docker, Docker Compose

---

## 📊 Financial Indicators & Anomaly Equations

The transformation engine applies mathematical formulas over time-series sliding windows using Pandas:

### 1. Moving Averages (5-Min & 15-Min SMA)
$$\text{SMA}_k = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}$$
Calculated using time-based window indexes over the raw tick timestamps. This ensures that calculations remain accurate even when streaming intervals experience network drift.

### 2. Price Volatility
Calculated as the rolling standard deviation ($\sigma$) of the percentage changes over a 5-minute window:
$$\text{Volatility} = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}$$

### 3. Price Momentum
Represents the Rate of Change (ROC) over a sliding 5-minute interval:
$$\text{Momentum} = \frac{P_t - P_{t-5m}}{P_{t-5m}} \times 100$$

### 4. Anomaly Detection
- **Volume Spike**: Flagged when a tick's volume ($V_t$) exceeds the 15-minute rolling average ($\mu_V$) by more than 3 standard deviations ($\sigma_V$):
  $$V_t > \mu_V + 3 \times \sigma_V$$
- **Price Shock**: Triggered when the absolute percentage change of a tick is greater than 3 times the rolling volatility:
  $$|R_t| > 3 \times \text{Volatility}$$
- **Price Drop Alert**: A critical alert triggered when the current price drops $\ge 5\%$ below the maximum price recorded in the last 5 minutes:
  $$P_t \le \text{Max}(P_{t-5m \dots t}) \times 0.95$$

---

## 🚀 Setup & Execution (Docker Compose)

The entire ecosystem is containerized and can be launched with a single command.

### Prerequisites
- Docker installed
- Docker Compose installed

### Run the pipeline
From the root folder `nse-etl-pipeline`, build and run the services:

```bash
docker compose up --build
```

This starts:
1. **PostgreSQL** (`localhost:5432`) - Initialized with default user/password/db (`postgres`/`postgres`/`finance_db`).
2. **Redis** (`localhost:6379`) - Caching and event broker.
3. **ETL Daemon** (starts streaming ingestion).
4. **FastAPI** (`http://localhost:8000`) - Serving API routes.
5. **Streamlit** (`http://localhost:8501`) - Dashboard portal.

Verify the setup by opening [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🔌 API Documentation

FastAPI provides an interactive OpenAPI interface available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Key Endpoints

- **GET `/stocks/latest`**
  Returns the most recent tick and computed metrics for all 10 tickers.
  *Optimization: Fetches from Redis cache first. If a cache miss occurs, queries PostgreSQL and caches the result.*

- **GET `/stocks/history/{ticker}`**
  Returns chronological metrics (default: 50 records) for a given symbol. Used to plot lines and flags.
  *Example:* `http://localhost:8000/stocks/history/RELIANCE.NS?limit=100`

- **GET `/stocks/summary`**
  Returns aggregate statistics including Top Gainer, Top Loser, average volatility, active alerts, and triggered anomalies.

- **WebSocket `/stocks/ws`**
  Subscribes clients to real-time broadcasts. 
  *Optimization: Listens to the Redis `stock_updates` pub/sub channel. If Redis is down, it seamlessly transitions to querying PostgreSQL for newer timestamps every 2 seconds.*

---

## 📁 Directory Structure

```
nse-etl-pipeline/
├── extract/
│   ├── api_client.py       # Live yfinance scraper + GBM simulator
│   └── stream_generator.py # ETL background thread coordinator
├── transform/
│   ├── cleaner.py          # Data cleansing & schema validation
│   └── indicators.py       # SMA, Volatility, Momentum, and Anomalies
├── load/
│   ├── db.py               # Session creation & PostgreSQL upsert scripts
│   └── models.py           # SQLAlchemy database tables and indices
├── api/
│   ├── main.py             # FastAPI entrypoint, lifespans and middleware
│   └── routes.py           # API REST endpoints & WebSockets
├── dashboard/
│   └── app.py              # Streamlit frontend & Plotly charts
├── config/
│   └── settings.py         # Pydantic settings loading from environment
├── docker/
│   ├── etl.Dockerfile      # Dockerfile for streaming daemon
│   └── api.Dockerfile      # Shared Dockerfile for API & Streamlit
├── docker-compose.yml      # Orchestration compose configurations
├── requirements.txt        # PIP dependencies
└── README.md               # Detailed project information
```

---

## ⚙️ Local Development (Without Docker)

To run the pipeline services locally for development:

1. **Start Postgres and Redis** locally on their default ports.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the database migrations & ETL stream**:
   ```bash
   python extract/stream_generator.py
   ```
4. **Start the API service** (in a new terminal):
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```
5. **Start the Streamlit dashboard** (in a new terminal):
   ```bash
   streamlit run dashboard/app.py --server.port 8501
   ```
