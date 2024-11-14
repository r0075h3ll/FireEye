import argparse
import fireeye.slack as slack_message
from fireeye.aws_lambda import CloudWatch
from fireeye.logger import logger
from fireeye.slack import SlackApp
from fireeye.exceptions import CloudWatchLogException
import pdb



parser = argparse.ArgumentParser()
parser.add_argument("--trace", help="Match a string/character", dest="to_trace", default="duration")
parser.add_argument("--arn", help="AWS Resource ARN", dest="arn", default=False)
parser.add_argument("--resource-name", help="AWS Lambda Name", dest="res_name", default=False)
parser.add_argument("--slack-url", help="Slack App incoming webhook URL", dest="slack_webhook", default=False)

args = parser.parse_args()
if (args.arn or args.res_name) is False:
    exit(parser.print_help())


def main():
    try:
        # pdb.set_trace()
        lambda_logs = CloudWatch(args.arn or args.res_name)
        logs = lambda_logs.lambda_logs(args.to_trace)

        print(logs)

        if not logs["response"]:
            raise CloudWatchLogException("Invalid Response")

        if args.slack_webhook:
            slack_app = SlackApp(url=args.slack_webhook)
            payload = slack_message.create_payload()

            slack_app.send(payload)
            pass
    except Exception as e:
        logger.info(e, exc_info=True)


main()