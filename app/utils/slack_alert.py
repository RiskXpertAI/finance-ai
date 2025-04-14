# app/utils/slack_alert.py

import requests
import os
import logging

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_alert(message: str, level: str = "INFO"):
    """ 슬랙 Webhook으로 알림 전송 """
    if not SLACK_WEBHOOK_URL:
        logging.warning("Slack Webhook URL이 없습니다.")
        return

    # Health Check 성공 등은 로그만 남기고 알림 안 보냄
    if level == "DEBUG":
        logging.info(f"[Slack DEBUG] {message}")
        return

    payload = {
        "text": f"[{level}] {message}"
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Slack 알림 실패: {e}")