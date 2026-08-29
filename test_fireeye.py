"""Self-check for the pure helpers. Run: python3 test_fireeye.py"""

from fireeye.cloudwatch import (
    build_query,
    collect_logs,
    is_instance_id,
    parse_arn,
    print_logs,
    quote,
)
from fireeye.exceptions import ARNFormatError
from fireeye.slack import create_payload, format_matches


def test_parse_arn():
    assert parse_arn("arn:aws:lambda:eu-west-1:123456789012:function:biller") == "biller"
    assert parse_arn("arn:aws:ec2:eu-west-1:123456789012:instance/i-0abc1234") == "i-0abc1234"
    assert parse_arn("biller") == "biller"

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


if __name__ == "__main__":
    for name, case in sorted(globals().items()):
        if name.startswith("test_"):
            case()
            print(f"ok {name}")
