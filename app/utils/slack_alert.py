# app/utils/slack_alert.py

import requests
import os
import logging

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_alert(message: str, level: str = "INFO"):
    if not SLACK_WEBHOOK_URL:
        logging.warning("[Slack] Slack Webhook URL이 없음")

        return

    # 성공, 디버깅은 로그만
    if level in ["DEBUG", "INFO"]:
        logging.info(f"[Slack-{level}] {message}")
        return

    # 실패만 알림
    payload = {"text": f"[{level}] {message}"}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Slack 알림 실패: {e}")