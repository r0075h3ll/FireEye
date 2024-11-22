import os

import urllib3

from fireeye.logger import logger

requests = urllib3.PoolManager()
webhook_url = os.getenv("SLACK_URL", False)


def create_payload(txt="Hi, it's FireEye here!"):
    message = {
        "text": f"{txt}"
    }


class SlackApp:
    def __init__(self, url=False):
        self.url = url

    def send(self, payload: str):
        resp = None
        try:
            resp = requests.request("POST", self.url or webhook_url, data=payload)
        except Exception as e:
            logger.info(e)

        if resp.status != 200:
            return
        logger.info("Notification sent successfully!")
