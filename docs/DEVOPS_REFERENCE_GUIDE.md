# DevOps & CI/CD Reference Manual: NSE Financial ETL Pipeline

This reference document compiles all the shell commands, setup steps, configurations, and scripts implemented to containerize and automate the Nairobi Securities Exchange (NSE) real-time pipeline.

---

## 🏗️ 1. Project Infrastructure Commands

### Clone the Repository
```bash
git clone https://github.com/E-Macharia/realtime-nse-financial-etl-pipeline.git
cd realtime-nse-financial-etl-pipeline
```

### Environment Configurations (`.env`)
Save this content as `.env` at the root of the project to map host ports dynamically and prevent conflicts:
```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=finance_db
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_PORT_HOST=5435        # Maps host database port to avoid conflicts
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PORT_HOST=6379
REDIS_PASSWORD=""
EXCHANGE=NSE
STREAM_INTERVAL_SECONDS=5
SIMULATION_MODE=true           # Set to 'false' to fetch real NSE prices from Yahoo Finance
API_PORT_HOST=8000
DASHBOARD_PORT_HOST=8501
API_URL=http://api:8000
```

### Docker Compose Commands
```bash
# Start all microservices in the background (detached mode) and force rebuilds
docker compose up -d --build

# Verify container status and exposed ports
docker compose ps

# View real-time logs for a specific service (e.g. FastAPI API backend)
docker compose logs -f api

# Stop and remove containers, networks, and persistent database volumes
docker compose down --volumes --rmi all
```

---

## 🤖 2. Jenkins Server Management

### Start Jenkins Server Container (Docker-out-of-Docker)
Run this command to create and run Jenkins in the background. It mounts the host's Docker socket so Jenkins can build and deploy container siblings:
```bash
docker run -d -u root -p 8080:8080 -p 50000:50000 -v jenkins_home:/var/jenkins_home -v /var/run/docker.sock:/var/run/docker.sock --name jenkins-server jenkins/jenkins:lts
```

### Manage Jenkins State
```bash
# Start Jenkins if the container is stopped (e.g. after server reboot)
docker start jenkins-server

# Stop the Jenkins server
docker stop jenkins-server

# Restart Jenkins
docker restart jenkins-server

# Set Jenkins to start automatically whenever the server boots up
docker update --restart unless-stopped jenkins-server
```

### Unlock Jenkins Admin Portal
Run this command to retrieve the temporary initial setup password:
```bash
docker exec jenkins-server cat /var/jenkins_home/secrets/initialAdminPassword
```

### Install Python inside the Jenkins Container
Because the official Jenkins image does not include Python, run this command to install the required tools for syntax linting and running tests:
```bash
docker exec -u root jenkins-server apt-get update && docker exec -u root jenkins-server apt-get install -y python3 python3-venv python3-pip build-essential
```

---

## 🔗 3. Webhook Tunneling (`ngrok`)

### Install `ngrok` (Debian/Ubuntu Server)
```bash
sudo snap install ngrok
```

### Configure and Start Tunnel in the Background
```bash
# 1. Add your free authentication token
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE

# 2. Start the HTTP tunnel on port 8080 in the background
nohup ngrok http 8080 > ngrok.log 2>&1 &

# 3. Retrieve your public forwarding URL
curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*ngrok-free.dev'

# 4. Stop the ngrok background process
pkill ngrok
```

---

## 🧪 4. Local Testing & Verification

### Running Healthchecks Manually
We wrote automated health checks to verify API ports, database status, Redis ping, and WebSocket handshakes:
```bash
# Run validation check
bash scripts/healthcheck.sh

# Run python WebSocket handshake check inside the API container directly
docker exec nse_api_service python -c "exec(\"import asyncio, websockets\nasync def main():\n    async with websockets.connect('ws://127.0.0.1:8000/stocks/ws'): pass\nasyncio.run(main())\")"
```

---

## 🧹 5. System Cleanup Commands (Freeing Up Space)
If you need to wipe everything and clean up disk storage:
```bash
# Stop and delete all app and Jenkins containers
docker rm -f nse_postgres nse_streamlit_dashboard nse_etl_service nse_api_service nse_redis jenkins-server

# Remove persistent data volumes
docker volume rm realtime-nse-financial-etl-pipeline_postgres_data jenkins_home

# Prune all dangling images, container caches, networks, and volumes
docker system prune -a --volumes -f
```
