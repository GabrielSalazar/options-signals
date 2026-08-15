#!/bin/bash

# Deploy to Railway.app script
# Usage: ./deploy_railway.sh [staging|production]

set -e

ENVIRONMENT=${1:-staging}
RAILWAY_TOKEN=${RAILWAY_TOKEN:-}

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}[Deploy] Starting deployment to Railway ($ENVIRONMENT)...${NC}"

# Step 1: Check Railway token
if [ -z "$RAILWAY_TOKEN" ]; then
  echo -e "${RED}Error: RAILWAY_TOKEN not set${NC}"
  echo "Set it with: export RAILWAY_TOKEN=your_token_here"
  exit 1
fi

# Step 2: Install Railway CLI (if not present)
if ! command -v railway &> /dev/null; then
  echo -e "${YELLOW}Installing Railway CLI...${NC}"
  npm install -g @railway/cli
fi

# Step 3: Login to Railway
echo -e "${YELLOW}[Deploy] Authenticating with Railway...${NC}"
railway login --token "$RAILWAY_TOKEN"

# Step 4: Check git status
echo -e "${YELLOW}[Deploy] Checking git status...${NC}"
if [ -n "$(git status --porcelain)" ]; then
  echo -e "${RED}Error: Uncommitted changes detected${NC}"
  git status
  echo "Commit or stash changes before deploying"
  exit 1
fi

# Step 5: Build Docker image
echo -e "${YELLOW}[Deploy] Building Docker image...${NC}"
docker build -t b3-options-signals:$ENVIRONMENT .

# Step 6: Deploy to Railway
echo -e "${YELLOW}[Deploy] Deploying to Railway ($ENVIRONMENT)...${NC}"
railway deploy --environment $ENVIRONMENT

# Step 7: Check health
echo -e "${YELLOW}[Deploy] Checking health endpoint...${NC}"
sleep 10  # Wait for deployment

HEALTH_URL="https://$(railway domain)"
if [ -z "$HEALTH_URL" ]; then
  echo -e "${YELLOW}⚠ Could not get Railway domain, checking manually...${NC}"
else
  echo -e "${YELLOW}Health check URL: $HEALTH_URL/health${NC}"
  # Try health check (may take time)
  for i in {1..30}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
      echo -e "${GREEN}✓ Health check passed (HTTP $HTTP_CODE)${NC}"
      break
    else
      echo -e "${YELLOW}  Attempt $i: HTTP $HTTP_CODE (retrying...)${NC}"
      sleep 2
    fi
  done
fi

echo -e "${GREEN}[Deploy] Deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Visit Railway console to monitor logs"
echo "2. Test the API endpoint"
echo "3. Update API_URL if domain changed"
echo "4. Disable cron-job.org keep-alive (no longer needed)"
echo ""
