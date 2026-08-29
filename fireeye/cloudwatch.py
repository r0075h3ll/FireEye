import datetime
import re
import time

from fireeye.aws import AWS
from fireeye.exceptions import ARNFormatError, CloudWatchLogException
from fireeye.logger import logger, dark_green, end

INSTANCE_ID = re.compile(r"i-[0-9a-f]{8,17}\Z")


def _fields(row: list):
    """A result row as {field name: value}.

    Rows come back as a list of {"field": ..., "value": ...}, and which fields
    are present depends on the query, so index by name rather than position.
    """
    return {f.get("field"): f.get("value") for f in row}


def print_logs(api_response: dict):
    for row in api_response["response"] or []:
        fields = _fields(row)
        print(f"{dark_green}{fields.get('@logStream', '')}{end}")
        print(fields.get("@message", ""))


def collect_logs(api_response: dict):
    """Timestamp/message pairs, as a list so identical timestamps are kept."""
    return [
        (_fields(row).get("@timestamp"), _fields(row).get("@message"))
        for row in api_response["response"] or []
    ]


def time_diff(days: int = 3):
    this_time = datetime.datetime.now()
    past_time = int((this_time - datetime.timedelta(days=days)).timestamp())

    return past_time, int(this_time.timestamp())


def parse_arn(arn: str):  # Filter resource name from un-qualified lambda arn
    if not arn.startswith("arn:"):
        return arn

    logger.info("Parsing ARN")
    parts = arn.split(":")
    if len(parts) < 6:
        raise ARNFormatError(f"Not a well formed ARN: {arn}")

    service = parts[2]
    if service not in ("lambda", "ec2"):
        raise ARNFormatError(
            f"FireEye reads Lambda and EC2 logs, but this ARN is for {service}: {arn}"
        )

    return parts[-1].split("/")[-1]


def is_instance_id(name: str):
    return bool(INSTANCE_ID.match(name))


def quote(to_trace: str):
    """Escape a search term for a CloudWatch string literal.

    Without this a term containing a double quote closes the literal early and
    the rest is parsed as query syntax, which is how searching for something
    like {"status": 500} ended up as a MalformedQueryException.
    """
    return to_trace.replace("\\", "\\\\").replace('"', '\\"')


def build_query(to_trace: str, regex: bool = False, log_stream: str = ""):
    """CloudWatch Logs Insights query matching `to_trace` in the message body.

    Plain search is a case-sensitive substring match. `regex` switches to a
    CloudWatch regex literal, so `--regex '(?i)timeout|error'` covers
    case-insensitive and multi-term searches.
    """
    match = f"/{to_trace}/" if regex else f'"{quote(to_trace)}"'
    query = f"fields @timestamp, @message, @logStream | filter @message like {match}"

    if log_stream:
        query += f' | filter @logStream like "{log_stream}"'

    return f"{query} | sort @timestamp desc"


class CloudWatch(AWS):
    def __init__(self, resource, log_group="", days=3, limit=100, wait=60):
        super().__init__()

        self.resource_name = parse_arn(resource)  # Lambda name or EC2 instance ID
        self.resource_arn = resource if resource.startswith("arn:") else False
        self.limit = limit
        self.wait = wait  # seconds to wait for a query to finish
        self.aws_session = super().aws_session()
        self.start_time, self.end_time = time_diff(days)
        self.query = ""

        if is_instance_id(self.resource_name):
            # EC2 log groups are named by whoever configured the CloudWatch
            # agent, so there is nothing sensible to guess here.
            if not log_group:
                raise CloudWatchLogException(
                    "EC2 monitoring needs --log-group (the log group the "
                    "CloudWatch agent writes to)"
                )
            self.log_group = log_group
            self.log_stream = self.resource_name
        else:
            self.log_group = log_group or f"/aws/lambda/{self.resource_name}"
            self.log_stream = ""

    def get_ctx_info(self):
        sts_client = self.aws_session.client("sts")
        get_caller_id = sts_client.get_caller_identity()

        return {
            "acc_id": get_caller_id.get("Account"),
            "default_region": self.aws_session.region_name,
            "iam_user": get_caller_id.get("Arn").split(":")[-1],
            "resource_arn": self.resource_arn,
            "res_name": self.resource_name,
        }

    def _wait_for_results(self, logs_client, query_id):
        deadline = time.monotonic() + self.wait

        while True:
            results = logs_client.get_query_results(queryId=query_id)
            status = results.get("status")

            if status not in ("Scheduled", "Running"):
                if status != "Complete":
                    raise CloudWatchLogException(f"Query {status.lower()}")

                return results

            if time.monotonic() >= deadline:
                logs_client.stop_query(queryId=query_id)
                raise CloudWatchLogException(
                    f"Query did not finish within {self.wait}s"
                )

            time.sleep(1)

    def fetch_logs(self, to_trace, regex=False):
        logs_client = self.aws_session.client("logs")
        self.query = build_query(to_trace, regex, self.log_stream)

        # Log what is about to run, not what ran, so a rejected query still
        # shows the group and query string that caused it.
        logger.info(f"Query String :: {self.query}")
        logger.info(
            f"Time Range :: {datetime.datetime.fromtimestamp(self.start_time)} to "
            f"{datetime.datetime.fromtimestamp(self.end_time)}"
        )
        logger.info(f"Log Group :: {self.log_group}")

        query_id = logs_client.start_query(
            logGroupName=self.log_group,
            startTime=self.start_time,
            endTime=self.end_time,
            queryString=self.query,
            limit=self.limit,
        )

        query_results = self._wait_for_results(logs_client, query_id.get("queryId"))

        return {"response": query_results.get("results", None)}

    lambda_logs = fetch_logs  # kept for callers on the old name
