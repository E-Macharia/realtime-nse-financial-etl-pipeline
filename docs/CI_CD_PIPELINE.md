# 🤖 CI/CD Pipeline Architecture & Jenkins Guide

This document describes the automated CI/CD pipeline built for the NSE Financial ETL Pipeline using Jenkins and declarative syntax.

---

## 🏗️ CI/CD Architecture Flow

The Jenkins server orchestrates the entire release cycle by executing a series of validation, testing, compilation, deployment, and health validation stages inside an isolated runtime:

```
[ Code Commit / Webhook ]
            │
            ▼
[ Stage 1: Checkout Source Code ]  --> Clones repository
            │
            ▼
[ Stage 2: Install Dependencies ]  --> Creates virtual env, updates pip, installs packages
            │
            ▼
[ Stage 3: Static Code Validation] --> Scans python files, checks syntax compiler errors
            │
            ▼
[ Stage 4: Run Unit Tests ]        --> Runs pytest, exports junit XML, archives reports
            │
            ▼
[ Stage 5: Build Docker Image ]    --> Rebuilds multi-stage targets (etl, api, dashboard)
            │                           Tags: latest, BUILD_NUMBER, GIT_COMMIT
            ▼
[ Stage 6: Verify Image Build ]    --> Displays sizes, checks lists of built images
            │
            ▼
[ Stage 7: Deploy Compose ]        --> Executes deployment/deploy.sh (stops old, recreates updated)
            │
            ▼
[ Stage 8: Health Checks ]         --> Executes scripts/healthcheck.sh (REST API, Redis, WS, UI)
            │
            ▼
[ Stage 9: Cleanup ]               --> Prunes dangling Docker container layers
            │
      ┌─────┴─────┐
      ▼           ▼
[ SUCCESS ]   [ FAILURE ]          --> Publishes notifications (Slack/Email hooks)
```

---

## 📖 Detailed Stage-by-Stage Explanation

### Stage 1: Checkout Source Code
* **Purpose**: Clones the source code from your remote repository (e.g., GitHub) using SCM configurations.
* **DevOps Detail**: Jenkins retrieves the source code and extracts the short **Git Commit Hash** dynamically. This hash acts as an immutable identifier that maps the exact code release directly to the Docker container tags built later in the pipeline.

### Stage 2: Install Dependencies
* **Purpose**: Prepares a fresh, isolated Python virtual environment (`venv`) and installs backend package requirements.
* **DevOps Detail**: Isolating python dependencies prevents version conflicts on the Jenkins host. We install packages from `requirements-backend.txt` to ensure compilation tools (like database headers and `psycopg2-binary`) compile successfully during verification.

### Stage 3: Static Code Validation
* **Purpose**: Verifies Python syntax correctness across all modules before building container layers.
* **DevOps Detail**: Runs `scripts/validate.py` recursively. If a developer accidentally left a syntax error (e.g., an unclosed bracket or typo), python's compiler will catch it, immediately failing the pipeline before wasting time/resources on building Docker layers.

### Stage 4: Run Unit Tests
* **Purpose**: Runs unit test assertions utilizing `pytest`.
* **DevOps Detail**: Executes code validation tests, generating a JUnit-formatted XML report (`test_results.xml`). Jenkins parses this file using the `junit` step to display test trends on the project dashboard. The test report is archived as a build artifact so developers can inspect historical failures. If any test case fails, the build fails immediately.

### Stage 5: Build Docker Image
* **Purpose**: Compiles the unified multi-stage `Dockerfile` to create images for our ETL, API, and Dashboard services.
* **DevOps Detail**: We tag each image with three tags:
  1. `latest`: Used for local running.
  2. `${BUILD_NUMBER}`: Sequential tracking matching the Jenkins execution index.
  3. `${GIT_COMMIT_HASH}`: Absolute mapping to the Git commit that produced the build.

### Stage 6: Docker Image Verification
* **Purpose**: Inspects built images to verify successful outputs and display image size metadata.
* **DevOps Detail**: Displays sizes using `docker images --filter "reference=nse-etl-pipeline-*"`. In a production environment, keeping track of image sizes helps monitor layers expansion and detect bloated images.

### Stage 7: Deploy using Docker Compose
* **Purpose**: Automates the replacement of running containers cleanly.
* **DevOps Detail**: Runs `deployment/deploy.sh`, which tears down any previous project containers, builds updated changes, and starts the container network in detached mode. This ensures the deployment is **idempotent** (safe to run repeatedly).

### Stage 8: Health Checks
* **Purpose**: Actively queries ports and network handshakes to guarantee services are responsive.
* **DevOps Detail**: Runs `scripts/healthcheck.sh`, which tests the FastAPI REST endpoints, checks if Redis pings successfully inside the docker network, validates the WebSocket handshake via a Python script, and verifies that the Streamlit web server returns HTTP 200. It loops with a retry mechanism to handle container startup latency.

### Stage 9: Cleanup
* **Purpose**: Cleans up disk space on the build runner.
* **DevOps Detail**: Calls `docker image prune -f` to delete untagged dangling build cache layers. Without this, a Jenkins server running multiple builds a day would run out of disk space very quickly.

---

## 🛠️ Archiving and Notification Extensions

* **Build Artifacts**: The JUnit XML test report (`test_results.xml`) is archived and permanently saved alongside the build.
* **Slack / Email Integrations**: Post-build action blocks (commented out in the `Jenkinsfile` for simplicity) show how to configure Slack webhook posts (`slackSend`) and email updates (`mail`) to notify engineers of deployment success or failure.
