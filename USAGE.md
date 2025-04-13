# 개발용 Dockerfile
docker build -f Dockerfile.dev -t financeai-dev .
docker run -e ENV=development -p 8000:8000 financeai-dev

# 운영용 Dockerfile.dev
docker build -f Dockerfile -t financeai-prod .
docker run -e ENV=production -p 8000:8000 financeai-prod