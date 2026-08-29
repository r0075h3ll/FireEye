import argparse

from fireeye.cloudwatch import CloudWatch, collect_logs, print_logs
from fireeye.exceptions import CloudWatchLogException
from fireeye.logger import logger
from fireeye.slack import SlackApp, create_payload

parser = argparse.ArgumentParser()
parser.add_argument(
    "--trace", help="Match a string/character", dest="to_trace", default="duration"
)
parser.add_argument("--arn", help="AWS Resource ARN", dest="arn", default=False)
parser.add_argument(
    "--resource-name",
    help="AWS Lambda name or EC2 instance ID",
    dest="res_name",
    default=False,
)
parser.add_argument(
    "--log-group",
    help="CloudWatch log group. Required for EC2, defaults to /aws/lambda/<name>",
    dest="log_group",
    default="",
)
parser.add_argument(
    "--regex",
    help="Treat --trace as a regular expression, e.g. '(?i)error|timeout'",
    dest="regex",
    action="store_true",
)
parser.add_argument(
    "--days", help="How far back to search", dest="days", type=int, default=3
)
parser.add_argument(
    "--limit", help="Maximum log lines to return", dest="limit", type=int, default=100
)
parser.add_argument(
    "--slack-url",
    help="Slack incoming webhook URL. Falls back to the SLACK_URL environment variable",
    dest="slack_webhook",
    nargs="?",
    const="",
    default=False,
)

args = parser.parse_args()
if (args.arn or args.res_name) is False:
    exit(parser.print_help())


def main():
    try:
        cloudwatch = CloudWatch(
            args.arn or args.res_name,
            log_group=args.log_group,
            days=args.days,
            limit=args.limit,
        )
        ctx_info = cloudwatch.get_ctx_info()

        logger.info(
            f"Account ID: {ctx_info.get('acc_id')}, Region: {ctx_info.get('default_region')}, "
            f"IAM User: {ctx_info.get('iam_user')}"
        )

        logs = cloudwatch.fetch_logs(args.to_trace, regex=args.regex)

        print_logs(logs)

        if args.slack_webhook is not False:
            slack_app = SlackApp(args.slack_webhook)
            slack_app.send(
                create_payload(ctx_info, cloudwatch.query, collect_logs(logs))
            )

        if logs["response"] is None:
            raise CloudWatchLogException("Invalid Response")

        if not logs["response"]:
            logger.info("No matching log lines")
    except Exception as e:
        logger.info(e, exc_info=True)


if __name__ == "__main__":
    main()
