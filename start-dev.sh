#!/bin/bash
set -e

echo "🚀 Starting Gainsly development environment..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")"

# Kill any existing processes before starting new ones
echo -e "${YELLOW}Cleaning up existing processes...${NC}"

# Kill existing uvicorn processes for this app
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo -e "${YELLOW}Stopping existing backend (uvicorn)...${NC}"
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    sleep 1
fi

# Kill existing vite dev server on port 5173
if lsof -ti:5173 > /dev/null 2>&1; then
    echo -e "${YELLOW}Stopping existing frontend (port 5173)...${NC}"
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Kill existing ollama serve processes (but not ollama app)
if pgrep -f "ollama serve" > /dev/null; then
    echo -e "${YELLOW}Stopping existing Ollama serve...${NC}"
    pkill -f "ollama serve" 2>/dev/null || true
    sleep 1
fi

echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

echo -e "${BLUE}Starting Ollama...${NC}"
ollama serve > ollama.log 2>&1 &
OLLAMA_PID=$!
echo -e "${GREEN}✓ Ollama started (PID: $OLLAMA_PID)${NC}"

echo -e "${BLUE}Starting PostgreSQL (Docker)...${NC}"
if ! docker ps --format '{{.Names}}' | grep -q '^alloy$'; then
    if docker ps -a --format '{{.Names}}' | grep -q '^alloy$'; then
        docker start alloy
    else
        docker run -d \
            --name alloy \
            -p 5433:5432 \
            -e POSTGRES_USER=gainsly \
            -e POSTGRES_PASSWORD=gainslypass \
            -e POSTGRES_DB=gainslydb \
            --health-cmd="pg_isready -U gainsly -d gainslydb" \
            --health-interval=5s \
            --health-timeout=5s \
            --health-retries=5 \
            pgvector/pgvector:pg16
    fi
fi
echo -e "${GREEN}✓ PostgreSQL container started${NC}"

echo -e "${BLUE}Starting backend (FastAPI)...${NC}"
source .venv/bin/activate
echo -e "${BLUE}Running migrations (Alembic)...${NC}"
alembic upgrade head
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
sleep 3

# Start frontend
echo ""
echo -e "${BLUE}Starting frontend (Vite)...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}✓ Development environment ready!${NC}"
echo ""
echo "Ollama:   http://localhost:11434"
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Handle cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $OLLAMA_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    docker stop alloy 2>/dev/null || true
    echo "All services stopped"
    wait
}

trap cleanup EXIT INT TERM

# Keep script running
wait
