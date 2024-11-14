import datetime
from fireeye.aws import AWS
from fireeye.logger import logger

def time_diff():
    this_time = datetime.datetime.now()
    step_size = 3
    past_time = int((this_time - datetime.timedelta(days=step_size)).timestamp())

    return past_time, int(this_time.timestamp())


def parse_arn(arn: str):  # Filter resource name from un-qualified lambda arn
    logger.info("Parsing ARN")
    try:
        if arn.split(":")[2] == "lambda":
            lambda_name = arn.split(":")[-1]

            return lambda_name
    except:
        logger.info("Failed to parse ARN")

    return arn


class CloudWatch(AWS):
    def __init__(self, arn):
        super().__init__()

        self.resource_name = f"/aws/lambda/{parse_arn(arn)}"  # Lambda name
        self.lambda_arn = arn  # optional
        self.log_stream_count = 3  # default set to fetch latest 3 streams
        self.aws_session = super().aws_session()
        self.start_time, self.end_time = time_diff()
        self.query = ""

    def _create_query(self, to_trace):
        query = f'fields @timestamp, @message | filter @message like "{to_trace}"'

        self.query = query

    def lambda_logs(self, to_trace):
        lambda_client = self.aws_session.client("logs")

        self._create_query(to_trace)

        query_id = lambda_client.start_query(
            logGroupName=self.resource_name,
            startTime=self.start_time,
            endTime=self.end_time,
            queryString=self.query,
            limit=self.log_stream_count,
        )

        logger.info(f"Query String :: {self.query}")
        logger.info(f"Time Range :: {datetime.datetime.fromtimestamp(self.start_time)} to {datetime.datetime.fromtimestamp(self.end_time)}")
        logger.info(f"Log Group :: {self.resource_name}")

        query_results = lambda_client.get_query_results(queryId=query_id.get('queryId', False))

        return {"response": query_results}
