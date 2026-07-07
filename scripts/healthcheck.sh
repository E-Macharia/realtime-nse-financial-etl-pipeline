#!/bin/bash
# Health check validation script for NSE Financial ETL Pipeline

# Configuration
API_URL="http://localhost:8000"
WS_URL="ws://localhost:8000/stocks/ws"
STREAMLIT_URL="http://localhost:8501"
MAX_ATTEMPTS=12
SLEEP_TIME=5

echo "=================================================="
echo "🚀 Starting DevOps Pipeline Active Health Checks..."
echo "=================================================="

# Function to check FastAPI REST Endpoint
check_fastapi() {
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/stocks/latest")
  if [ "$code" -eq 200 ]; then
    echo "✅ [SUCCESS] FastAPI REST API is healthy (HTTP $code)"
    return 0
  else
    echo "❌ [WAITING] FastAPI REST API returned HTTP $code"
    return 1
  fi
}

# Function to check Redis Connectivity inside the container
check_redis() {
  if docker exec nse_redis redis-cli ping | grep -q "PONG"; then
    echo "✅ [SUCCESS] Redis cache is healthy and responding (PONG)"
    return 0
  else
    echo "❌ [WAITING] Redis container is not responding to ping"
    return 1
  fi
}

# Function to check WebSocket handshake connectivity via Python utility
check_websocket() {
  if python -c "import asyncio, websockets; asyncio.run(websockets.connect('$WS_URL', close_timeout=1.0))" 2>/dev/null; then
    echo "✅ [SUCCESS] WebSocket server handshake established successfully"
    return 0
  else
    echo "❌ [WAITING] WebSocket endpoint handshake failed"
    return 1
  fi
}

# Function to check Streamlit Dashboard Endpoint
check_streamlit() {
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" "$STREAMLIT_URL")
  if [ "$code" -eq 200 ] || [ "$code" -eq 304 ]; then
    echo "✅ [SUCCESS] Streamlit dashboard UI is healthy (HTTP $code)"
    return 0
  else
    echo "❌ [WAITING] Streamlit dashboard returned HTTP $code"
    return 1
  fi
}

# Ingestion loop with retry mechanism to handle service startup delays
for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
  echo "Checking service health (Attempt $attempt of $MAX_ATTEMPTS)..."
  
  fastapi_ok=0
  redis_ok=0
  websocket_ok=0
  streamlit_ok=0
  
  check_fastapi && fastapi_ok=1
  check_redis && redis_ok=1
  check_websocket && websocket_ok=1
  check_streamlit && streamlit_ok=1
  
  if [ "$fastapi_ok" -eq 1 ] && [ "$redis_ok" -eq 1 ] && [ "$websocket_ok" -eq 1 ] && [ "$streamlit_ok" -eq 1 ]; then
    echo "=================================================="
    echo "🎉 All pipeline services are healthy and online!"
    echo "=================================================="
    exit 0
  fi
  
  echo "Some services are not fully ready yet. Retrying in ${SLEEP_TIME}s..."
  sleep "$SLEEP_TIME"
done

echo "=================================================="
echo "🚨 HEALTH CHECK FAILED! One or more services are offline."
echo "=================================================="
exit 1
