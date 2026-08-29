import os

import urllib3

from fireeye.logger import logger

http = urllib3.PoolManager()


def format_matches(matches: list, max_lines: int = 20):
    if not matches:
        return "No matching log lines."

    lines = [f"{stamp} {message}" for stamp, message in matches[:max_lines]]
    if len(matches) > max_lines:
        lines.append(f"... and {len(matches) - max_lines} more")

    return "\n".join(lines)


def create_payload(info: dict, query: str, matches: list):
    account_id = info.get("acc_id", "none")
    resource_arn = info.get("resource_arn") or "none"
    resource_name = info.get("res_name", "none")

    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "AWS Alert from FireEye",
                    "emoji": True,
                },
            },
            {"type": "divider"},
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {
                                "type": "text",
                                "text": f"Account ID: {account_id}",
                                "style": {"bold": True},
                            },
                            {"type": "text", "text": "\n"},
                            {
                                "type": "text",
                                "text": f"Resource ARN: {resource_arn}",
                                "style": {"bold": True},
                            },
                            {"type": "text", "text": "\n"},
                            {
                                "type": "text",
                                "text": f"Resource Name: {resource_name}",
                                "style": {"bold": True},
                            },
                        ],
                    }
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```Query: {query}\n\n{format_matches(matches)}```",
                },
            },
        ]
    }


class SlackApp:
    def __init__(self, url=""):
        self.url = url or os.getenv("SLACK_URL", "")

    def send(self, payload: dict):
        if not self.url:
            logger.info("No Slack webhook URL, skipping alert")
            return False

        try:
            resp = http.request("POST", self.url, json=payload, timeout=10, retries=1)
        except Exception as e:
            logger.info(e)
            return False

        if resp.status != 200:
            logger.info(f"Slack returned {resp.status}: {resp.data.decode(errors='replace')}")
            return False

        logger.info("Notification sent successfully!")
        return True
