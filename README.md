# Real-Time NSE Financial Data Engineering & DevOps Pipeline

An end-to-end, containerized real-time financial data engineering pipeline designed to ingest, clean, transform, and visualize stock market metrics from the Nairobi Securities Exchange (NSE), integrated with a **production-grade Jenkins CI/CD pipeline** to automate validation, testing, containerization, deployment, and health checks.

This repository showcases both data engineering excellence (micro-batching, statistical anomaly detection, named volume caching) and **modern DevOps practices** (declarative CI/CD pipeline, multi-stage builds, container orchestration, and automated environment validations).

## 🏗️ System & CI/CD Architecture

The system operates across two decoupled layers: the **Ingestion & Serving Layer** (the application) and the **Automation Layer** (Jenkins CI/CD).

```
   [ Code Push to GitHub ]
              │
              ▼
    ┌───────────────────┐
    │  Jenkins Server   │ (CI/CD Orchestration)
    └───────────────────┘
              │
      (1) Checkout & lint syntax
      (2) Run pytest unit tests
      (3) Build unified multi-stage images
      (4) Deploy via Docker Compose
      (5) Run active curl healthchecks
              │
              ▼
    ┌───────────────────┐
    │  Docker Engine    │ (Containerized Runtime)
    └───────────────────┘
      ├── db (PostgreSQL persistent volume)
      ├── redis (High-speed memory broker)
      ├── etl (Python ingestion daemon)
      ├── api (FastAPI serving REST/WebSockets)
      └── dashboard (Streamlit UI dashboard)
```

## 🛠️ DevOps CI/CD Pipeline Stages

Our declarative `Jenkinsfile` automates the release cycle through **9 sequential stages**:

1. **Checkout Source Code**: Clones the GitHub repository and extracts the short Git commit hash to uniquely tag images.
2. **Install Dependencies**: Creates an isolated Python virtual environment and installs packages from `requirements-backend.txt`.
3. **Static Code Validation**: Scans all Python scripts recursively via `scripts/validate.py` to ensure zero compilation or syntax errors before building images.
4. **Run Unit Tests**: Executes `pytest` and outputs a JUnit XML report (`test-results.xml`) which is parsed, visualised, and archived as a build artifact.
5. **Build Docker Image**: Builds the unified multi-stage `Dockerfile` and tags the three service images (`etl`, `api`, `dashboard`) with `latest`, the Jenkins `${BUILD_NUMBER}`, and the Git `${COMMIT_HASH}`.
6. **Docker Image Verification**: Lists the built images and confirms their metadata sizes.
7. **Deploy using Docker Compose**: Executes `deployment/deploy.sh` to stop previous containers, prune orphaned layers, and start the new image tags.
8. **Health Checks**: Calls `scripts/healthcheck.sh` to ping and verify connectivity for FastAPI, Redis, WebSockets, and Streamlit.
9. **Cleanup**: Runs `docker image prune` to delete untagged dangling build layers and reclaim disk space.

## 🐳 Docker Multi-Stage & Network Workflow

* **Unified Multi-Stage Dockerfile**: We unified legacy separate configurations into a single `Dockerfile` at the root. The common dependencies (compiled libraries, package installations) are compiled once in the `base` stage, and inherited instantly by target stages (`etl`, `api`, `dashboard`), speeding up rebuilds.
* **Persistent Storage**: PostgreSQL data is mapped to a named Docker volume (`postgres_data`) on the host. When Jenkins redeploys the containers, the old databases are destroyed but the volume stays intact, ensuring historical data is preserved.
* **Network Isolation**: All containers run on an isolated bridge network `finance_network`. Only the API (port `8000`) and Streamlit (port `8501`) expose ports to the outside world; the PostgreSQL database and Redis are kept secure and resolve internally using Docker's DNS.

---

## 🚀 Running Jenkins Locally

You can spin up a local Jenkins server that can interface with your host's Docker engine to run the pipeline:

### 1. Run Jenkins Container (Docker-out-of-Docker)

Execute this command to launch Jenkins and mount the host's Docker socket and binary:

```bash
docker run -d -u root -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --name jenkins-server jenkins/jenkins:lts
```

* **Note on Docker access**: Mounting `/var/run/docker.sock` allows the Jenkins server inside the container to execute `docker` and `docker compose` commands directly on your host machine's Docker engine.

### 2. Configure the Jenkins Job

1. Open **[http://localhost:8080](http://localhost:8080)** in your browser and complete the initial setup.
2. Install recommended plugins (including **Git** and **Pipeline**).
3. Create a new item -> **Pipeline** project named `realtime-nse-pipeline`.
4. In the **Pipeline** configuration section:
   * Definition: Select **Pipeline script from SCM**.
   * SCM: Select **Git**.
   * Repository URL: Enter your GitHub repository link.
   * Branch Specifier: `*/main`.
   * Script Path: `Jenkinsfile`.
5. Save the configuration.

---

## 🔄 Triggering and Managing Builds

### Trigger a Build

* **Manual Trigger**: Click **Build Now** on the left-hand sidebar of your Jenkins project.
* **Automated Webhooks**: In your GitHub repository Settings under Webhooks, add your Jenkins URL (e.g., `http://<your-ip>:8080/github-webhook/`) to automatically trigger a build every time a developer runs `git push`.
* **SCM Polling**: In Jenkins under **Build Triggers**, check **Poll SCM** and enter `H/5 * * * *` to poll your GitHub repository for changes every 5 minutes.

### Rerun Failed Builds

1. Open the failed build number in Jenkins.
2. Click **Rebuild** on the left menu to run the entire pipeline again.
3. For long-running builds, click **Restart from Stage** on the pipeline visualizer to skip already successful steps and resume compilation exactly where the error occurred (e.g., restarting directly from the *Deploy* stage after fixing a port collision).

---

## 📁 Project Structure

```
nse-etl-pipeline/
├── Jenkinsfile              # Declarative CI/CD pipeline automation script
├── Dockerfile               # Unified multi-stage Dockerfile
├── docker-compose.yml       # Production-style service orchestration configuration
├── .env.example             # Template containing pipeline configuration variables
├── requirements.txt         # Lightweight dependencies for Streamlit Cloud
├── requirements-backend.txt # Full dependencies for backend & Docker compilations
├── extract/                 # E - API retrieval and GBM simulation scripts
├── transform/               # T - Cleansing and Pandas indicator calculations
├── load/                    # L - SQLAlchemy schema layouts and DB upserts
├── api/                     # Serving REST API and WebSocket protocols
├── dashboard/               # Visualizing Streamlit UI layouts
├── scripts/                 # Validation & active health check utilities
│   ├── validate.py          # Python syntax validation script
│   └── healthcheck.sh       # TCP/HTTP service health verification script
├── deployment/              # Release scripts
│   └── deploy.sh            # Idempotent deploy executor script
├── tests/                   # Pytest automation test suite
│   ├── test_cleaner.py      # Cleaner unit tests
│   ├── test_indicators.py   # Indicators unit tests
│   └── test_api.py          # FastAPI route integration tests
└── docs/                    # Educational manuals
    ├── CI_CD_PIPELINE.md    # Pipeline step details
    └── DOCKER_WORKFLOW.md   # Container networking & volumes







    WEBHOOKS AND JENKINS SERVER

    This is perfect! Your ngrok dashboard confirms that unrefinedly-periphrastic-leslee.ngrok-free.dev is indeed your permanent, registered dev domain.

Since it has been active on your account for 7 months, it will never change or expire, meaning:

You can start your background tunnel anytime using:
bash


nohup ngrok http 8080 --domain=unrefinedly-periphrastic-leslee.ngrok-free.dev > ngrok.log 2>&1 &
Your GitHub webhooks for this project and any future projects will always point to: https://unrefinedly-periphrastic-leslee.ngrok-free.dev/github-webhook/
Your automated Jenkins CI/CD environment is now fully complete, robust, and permanent!
```

<!-- Automated webhook trigger validation -->
