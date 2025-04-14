import requests
import os
import logging

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# 레벨별 슬랙 알림 여부 설정
ALERT_LEVELS = ["ERROR", "CRITICAL"]

def send_slack_alert(message: str, level: str = "INFO"):
    """ 슬랙 알림 모듈 """

    if not SLACK_WEBHOOK_URL:
        logging.warning("[Slack] Slack Webhook URL 없음")
        return

    log_message = f"[Slack-{level}] {message}"

    if level in ALERT_LEVELS:
        # 에러 이상 레벨은 슬랙 알림 발송
        payload = {"text": f"[{level}] {message}"}
        try:
            response = requests.post(SLACK_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            logging.info(f"[Slack] 알림 전송 완료")
        except Exception as e:
            logging.error(f"[Slack] 알림 전송 실패: {e}")
    else:
        # 디버깅, 인포 레벨은 로그만
        logging.info(log_message)