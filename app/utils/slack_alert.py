import requests
import os

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_alert(message: str):
    """ 슬랙 Webhook으로 알림 전송 """
    if not SLACK_WEBHOOK_URL:
        print("Slack Webhook URL이 없습니다.")
        return

    payload = {
        "text": message
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Slack 알림 실패: {e}")