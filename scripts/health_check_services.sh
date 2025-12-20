#!/bin/bash
# Quick health check for all Curiosity Cottage services
# Usage: ./scripts/health_check_services.sh

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Curiosity Cottage Service Health Check ===${NC}\n"

# 1. Docker Services
echo -e "${YELLOW}Docker Services:${NC}"
if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "cc_db|cc_pulse"; then
    echo -e "${GREEN}✅ Docker services running${NC}"
else
    echo -e "${RED}❌ Some Docker services down${NC}"
fi

# 2. TimescaleDB
echo -e "\n${YELLOW}TimescaleDB:${NC}"
if pg_isready -h localhost -p 5432 -U postgres &>/dev/null; then
    echo -e "${GREEN}✅ Database reachable (port 5432)${NC}"
else
    echo -e "${RED}❌ Database unreachable${NC}"
fi

# 3. OTEL Collector
echo -e "\n${YELLOW}OTEL Collector:${NC}"
if curl -s http://localhost:13133 | grep -q "Server available"; then
    uptime=$(curl -s http://localhost:13133 | jq -r '.uptime')
    echo -e "${GREEN}✅ Collector healthy (uptime: $uptime)${NC}"
else
    echo -e "${RED}❌ Collector health check failed${NC}"
fi

# 4. Ollama (LLM)
echo -e "\n${YELLOW}Ollama (LLM):${NC}"
if curl -s http://localhost:11434/api/tags &>/dev/null; then
    model_count=$(curl -s http://localhost:11434/api/tags | jq '.models | length')
    echo -e "${GREEN}✅ Ollama running ($model_count models loaded)${NC}"
else
    echo -e "${RED}❌ Ollama unreachable${NC}"
fi

# 5. Frontend (Vite)
echo -e "\n${YELLOW}Frontend (Vite):${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
    echo -e "${GREEN}✅ Vite dev server running (port 3000)${NC}"
else
    echo -e "${RED}❌ Vite dev server not responding${NC}"
fi

# 6. Backend API (if running)
echo -e "\n${YELLOW}Backend API:${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}✅ Backend API running (port 8000)${NC}"
else
    echo -e "${YELLOW}⚠️  Backend API not running (optional)${NC}"
fi

echo -e "\n${YELLOW}=== Health Check Complete ===${NC}"
