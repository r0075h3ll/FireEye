import argparse
import sys

from botocore.exceptions import BotoCoreError, ClientError

from fireeye.cloudwatch import CloudWatch, collect_logs, print_logs
from fireeye.exceptions import ARNFormatError, CloudWatchLogException
from fireeye.logger import logger
from fireeye.slack import SlackApp, create_payload


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be 1 or greater, got {value}")

    return number


parser = argparse.ArgumentParser(prog="fireeye")
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
    "--days", help="How far back to search", dest="days", type=positive, default=3
)
parser.add_argument(
    "--limit",
    help="Maximum log lines to return",
    dest="limit",
    type=positive,
    default=100,
)
parser.add_argument(
    "--slack-url",
    help="Slack incoming webhook URL. Falls back to the SLACK_URL environment variable",
    dest="slack_webhook",
    nargs="?",
    const="",
    default=False,
)
parser.add_argument(
    "--debug",
    help="Print the full traceback when something fails",
    dest="debug",
    action="store_true",
)

args = parser.parse_args()
if not (args.arn or args.res_name):
    parser.print_help()
    sys.exit(2)


def fail(message):
    # exc_info only means something while an exception is being handled
    logger.error(message, exc_info=args.debug and sys.exc_info()[0] is not None)

    return 1


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
    except (ARNFormatError, CloudWatchLogException) as e:
        return fail(e)
    except ClientError as e:
        return fail(e.response.get("Error", {}).get("Message", e))
    except BotoCoreError as e:
        return fail(e)
    except KeyboardInterrupt:
        logger.error("Interrupted")

        return 130

    print_logs(logs)

    if logs["response"] is None:
        return fail("CloudWatch returned no results field")

    if not logs["response"]:
        logger.info("No matching log lines")

    if args.slack_webhook is not False:
        slack_app = SlackApp(args.slack_webhook)
        if not slack_app.send(
            create_payload(ctx_info, cloudwatch.query, collect_logs(logs))
        ):
            return fail("Slack alert was not delivered")

    return 0


if __name__ == "__main__":
    sys.exit(main())
