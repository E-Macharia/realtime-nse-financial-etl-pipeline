# 🐳 Containerized Architecture & Docker Workflow Guide

This document describes the container setup, multi-stage configurations, networking, and volumes defined in the NSE Financial ETL Pipeline.

---

## 🏗️ Container Network Topography

All services run inside an isolated Docker bridge network `finance_network`, enabling secure container-to-container communication using internal Docker DNS resolution:

```
                          [ Client Web Browser ]
                             │            │
             (Port 8501)     ▼            ▼     (Port 8000)
       ┌────────────────────────┐      ┌────────────────────────┐
       │   Streamlit Container  │      │    FastAPI Container   │
       │      (dashboard)       │      │         (api)          │
       └────────────────────────┘      └────────────────────────┘
                    │                              │
                    │ (Internal API call:          │
                    │  http://api:8000)            │
                    ▼                              ▼
 ─────────────────────────────────────────────────────────────────────────────
                             finance_network
 ─────────────────────────────────────────────────────────────────────────────
         ▲                                                 ▲
         │                                                 │
 ┌────────────────────────┐                        ┌───────────────┐
 │   ETL Daemon Container │                        │  Redis Cache  │
 │         (etl)          │ ─── (Reads/Writes) ──> │  Container    │
 └────────────────────────┘                        └───────────────┘
         │
         │ (Ingests ticks, queries averages, writes transactions)
         ▼
 ┌────────────────────────┐
 │   PostgreSQL DB        │ <─── (Volume Mount: postgres_data)
 │        (db)            │
 └────────────────────────┘
```

---

## 📖 Multi-Stage Dockerfile Guide

We unified the separate service Dockerfiles into a single multi-stage `Dockerfile` at the root of the project.

### Benefits of Multi-Stage Builds in DevOps
1. **Caching Efficiency**: The heavy layer of system compilation utilities (`build-essential`, `libpq-dev`, `curl`) and Python package installations is built once in the `base` stage. Subsequent stages (`etl`, `api`, `dashboard`) inherit from this stage instantly.
2. **Maintenance Simplicity**: You manage a single file for all package environment setups instead of tracking multiple files across folders.
3. **Decoupled Deployment Targets**: Jenkins or Docker Compose can target individual build stages using `--target` flags:
   * `docker build --target etl ...`
   * `docker build --target api ...`
   * `docker build --target dashboard ...`

---

## 📁 Named Volumes & Persistent Storage

Database files inside Docker containers are ephemeral and deleted when a container is removed. To prevent data loss during pipeline redeployments, we configure a named volume in `docker-compose.yml`:

```yaml
volumes:
  postgres_data:
    driver: local
```

* **Integration**: The named volume is mounted inside the PostgreSQL container at `/var/lib/postgresql/data`.
* **Idempotency**: When Jenkins executes `docker compose down` and then `docker compose up -d`, the old container is deleted, but the named volume `postgres_data` is preserved. The new container attaches to it on startup, keeping all historical financial ticks and metrics intact.

---

## 🌐 Network Isolation & Service Discovery

Services are connected via a custom bridge network `finance_network`:
* **Container Isolation**: None of the database or caching containers are exposed to the external host unless configured. Only the `api` (port 8000) and `dashboard` (port 8501) expose ports to the outside world.
* **DNS Resolution**: Containers resolve names dynamically. The Streamlit dashboard calls the FastAPI server using the container name: `http://api:8000`. The ETL container connects to Postgres using host name `db` and Redis using host name `redis`.
