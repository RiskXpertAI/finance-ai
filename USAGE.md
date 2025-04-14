# 코드 변경후 사용
git pull origin main
sudo docker cp .env fastapi:/app/.env
finance-ai$ sudo docker-compose down
finance-ai$ sudo docker-compose up -d --build




# ———————————
# 백업
sudo docker cp certbot:/etc/letsencrypt ./letsencrypt-backup

# 복구
sudo docker cp ./letsencrypt-backup/. certbot:/etc/letsencrypt/
