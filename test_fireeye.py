"""Self-check for the pure helpers. Run: python3 test_fireeye.py"""

from fireeye.cloudwatch import (
    CloudWatch,
    build_query,
    collect_logs,
    is_instance_id,
    parse_arn,
    print_logs,
    quote,
)
from fireeye.exceptions import ARNFormatError, CloudWatchLogException
from fireeye.slack import create_payload, format_matches, utc_now


def test_parse_arn():
    assert parse_arn("arn:aws:lambda:eu-west-1:123456789012:function:biller") == "biller"
    assert parse_arn("arn:aws:ec2:eu-west-1:123456789012:instance/i-0abc1234") == "i-0abc1234"
    assert parse_arn("biller") == "biller"

    # a qualified ARN ends in the alias or version, not the function name
    assert (
        parse_arn("arn:aws:lambda:eu-west-1:123456789012:function:biller:PROD")
        == "biller"
    )

    for bad in ("arn:aws:s3:::my-bucket", "arn:aws:lambda"):
        try:
            parse_arn(bad)
            raise AssertionError(f"{bad} should have been rejected")
        except ARNFormatError:
            pass


def test_is_instance_id():
    assert is_instance_id("i-0abc1234")
    assert is_instance_id("i-0abc1234def5678901") is False  # 18 hex chars, too long
    assert is_instance_id("biller") is False


def test_build_query():
    plain = build_query("Bill")
    assert '@message like "Bill"' in plain
    assert "sort @timestamp desc" in plain

    assert "@message like /(?i)error/" in build_query("(?i)error", regex=True)

    scoped = build_query("Bill", log_stream="i-0abc1234")
    assert '@logStream like "i-0abc1234"' in scoped


def test_quote():
    assert quote('{"status": 500}') == '{\\"status\\": 500}'
    assert quote("back\\slash") == "back\\\\slash"

    # a term with a quote in it must not close the string literal early
    query = build_query('a" | stats count() as c | filter c > 0 | filter @message like "')
    assert query.count('like "') == 1


def test_rows_indexed_by_name():
    # @ptr is always returned and the field order is not guaranteed
    row = [
        {"field": "@ptr", "value": "xyz"},
        {"field": "@message", "value": "boom"},
        {"field": "@logStream", "value": "stream"},
        {"field": "@timestamp", "value": "12:00"},
    ]
    assert collect_logs({"response": [row]}) == [("12:00", "boom")]
    print_logs({"response": [row]})  # must not raise on an unexpected field order


def test_collect_logs():
    event = [
        {"field": "@timestamp", "value": "12:00"},
        {"field": "@message", "value": "boom"},
        {"field": "@logStream", "value": "stream"},
    ]
    assert collect_logs({"response": [event, event]}) == [("12:00", "boom")] * 2
    assert collect_logs({"response": None}) == []


def test_format_matches_stays_under_slack_limit():
    from fireeye.slack import BLOCK_LIMIT

    long_line = "REPORT RequestId: 1c6a91a9\tDuration: 514.37 ms\t" + "x" * 120
    text = format_matches([(f"12:0{i}", long_line) for i in range(20)])

    assert len(text) <= BLOCK_LIMIT + 40  # the "... and N more" line
    assert text.endswith("more")


def test_format_matches():
    assert format_matches([]) == "No matching log lines."
    assert format_matches([("12:00", "boom")]) == "12:00 boom"

    truncated = format_matches([(str(i), "x") for i in range(25)], max_lines=20)
    assert truncated.endswith("... and 5 more")


def test_create_payload():
    payload = create_payload(
        {"acc_id": "123", "res_name": "biller", "resource_arn": False},
        "fields @timestamp",
        [("12:00", "boom")],
    )
    body = payload["blocks"][-1]["text"]["text"]
    assert "boom" in body and "fields @timestamp" in body
    assert "Resource ARN: none" in str(payload)

    # the alert carries its own send time, in UTC, not the log line timestamps
    assert f"Alert Time: {utc_now()[:13]}" in str(payload)


def test_utc_now_format():
    import datetime
    import re

    stamp = utc_now()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", stamp), stamp

    # within a minute of actual UTC, so a local-time clock would not pass
    parsed = datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S UTC")
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    assert abs((now - parsed).total_seconds()) < 60


class FakeLogs:
    """Enough of the CloudWatch Logs client to drive the polling loop."""

    def __init__(self, statuses, interrupt_on=None):
        self.statuses = list(statuses)
        self.interrupt_on = interrupt_on
        self.calls = 0
        self.stopped = []

    def get_query_results(self, queryId):
        self.calls += 1
        if self.calls == self.interrupt_on:
            raise KeyboardInterrupt

        status = self.statuses.pop(0) if self.statuses else "Running"

        # the real API returns an empty list while a query is in progress
        return {"status": status, "results": []}

    def stop_query(self, queryId):
        self.stopped.append(queryId)


def _waiter(wait=60):
    watcher = CloudWatch.__new__(CloudWatch)  # no AWS session, no credentials
    watcher.wait = wait

    return watcher


def test_polling_waits_then_returns():
    logs = FakeLogs(["Scheduled", "Running", "Complete"])
    assert _waiter()._wait_for_results(logs, "q1")["status"] == "Complete"
    assert logs.calls == 3
    assert logs.stopped == []


def test_failed_and_cancelled_queries_raise():
    for status in ("Failed", "Cancelled", "Timeout"):
        try:
            _waiter()._wait_for_results(FakeLogs([status]), "q1")
            raise AssertionError(f"{status} should have raised")
        except CloudWatchLogException as e:
            assert status.lower() in str(e)


def test_timeout_stops_the_query():
    logs = FakeLogs(["Running"])
    try:
        _waiter(wait=0)._wait_for_results(logs, "q1")
        raise AssertionError("should have timed out")
    except CloudWatchLogException as e:
        assert "did not finish" in str(e)

    assert logs.stopped == ["q1"], "a timed out query must be stopped"


def test_interrupt_stops_the_query():
    logs = FakeLogs(["Running", "Running"], interrupt_on=2)
    try:
        _waiter()._wait_for_results(logs, "q1")
        raise AssertionError("should have propagated KeyboardInterrupt")
    except KeyboardInterrupt:
        pass

    assert logs.stopped == ["q1"], "an interrupted query must be stopped"


def test_interrupt_during_the_sleep_stops_the_query():
    import fireeye.cloudwatch as cloudwatch

    def interrupting_sleep(seconds):
        raise KeyboardInterrupt

    logs = FakeLogs(["Running"])
    slept = cloudwatch.time.sleep
    cloudwatch.time.sleep = interrupting_sleep
    try:
        _waiter()._wait_for_results(logs, "q1")
        raise AssertionError("should have propagated KeyboardInterrupt")
    except KeyboardInterrupt:
        pass
    finally:
        cloudwatch.time.sleep = slept

    assert logs.stopped == ["q1"], "an interrupt between polls must stop the query"


def test_stop_failure_is_warned_not_hidden():
    import logging

    class Unstoppable(FakeLogs):
        def stop_query(self, queryId):
            raise RuntimeError("credentials expired")

    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    from fireeye.logger import logger

    handler = Capture()
    logger.addHandler(handler)
    try:
        _waiter(wait=0)._wait_for_results(Unstoppable(["Running"]), "q1")
        raise AssertionError("should have timed out")
    except CloudWatchLogException:
        pass
    finally:
        logger.removeHandler(handler)

    assert any(r.levelno >= logging.WARNING for r in records), records
def test_old_module_path_still_works():
    import sys
    import warnings

    import fireeye.cloudwatch

    # a previous import would have cached the module and swallowed the warning
    sys.modules.pop("fireeye.aws_lambda", None)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import fireeye.aws_lambda as old

    assert old.CloudWatch is fireeye.cloudwatch.CloudWatch, "must be the same class"
    assert old.parse_arn is fireeye.cloudwatch.parse_arn
    assert (
        old.parse_arn("arn:aws:lambda:eu-west-1:123456789012:function:biller")
        == "biller"
    )

    deprecations = [w for w in caught if w.category is DeprecationWarning]
    assert deprecations, "importing the old path must warn"
    assert "1.0.0" in str(deprecations[0].message), "the warning must name a removal version"

    assert set(old.__all__) <= set(dir(fireeye.cloudwatch))


if __name__ == "__main__":
    for name, case in sorted(globals().items()):
        if name.startswith("test_"):
            case()
            print(f"ok {name}")
