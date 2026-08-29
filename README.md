<div align="center">
    <a href="https://github.com/r0075h3ll/FireEye"><img alt="FireEye" src="https://raw.githubusercontent.com/r0075h3ll/FireEye/main/static/logo/fireeye.png" width="100"/></a>
    <h2>
    FireEye
    </h2>
</div>

<h4 align="center">AWS Monitoring Toolkit</h4>

<div align="center">
<img src="https://img.shields.io/badge/License-Apache%202.0-blue">
<img src="https://img.shields.io/badge/Python-3.12-blue">
<img src="https://img.shields.io/badge/Release-0.7.1-green">
</div>

\
FireEye is an AWS monitoring toolkit for DevOps, Security, and IT teams. It can currently trace strings in AWS Lambda function(s) output logs via CloudWatch using simple [commands](#monitor-lambda-functions-w-cloudwatch-logs-insights).

[//]: # (insert gif)
[![asciicast](https://asciinema.org/a/696182.svg)](https://asciinema.org/a/696182)

### Installation

```bash
git clone https://github.com/r0075h3ll/FireEye && cd FireEye
pip install .

# or

pip install FireEye-AWS
```

### Credentials

FireEye uses your existing AWS configuration. It reads `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and
`AWS_DEFAULT_REGION` if they are set, and otherwise falls back to whatever boto3 finds: `~/.aws/credentials`,
a profile, or an instance role.

A region is required. Without one you get `You must specify a region.` and exit status 1.

The IAM permissions needed are `logs:StartQuery`, `logs:GetQueryResults`, `logs:StopQuery` and
`sts:GetCallerIdentity`.

### Features

##### Monitor Lambda functions w/ CloudWatch Logs Insights

```bash
fireeye --trace Bill --resource-name lambda_name
```

`--resource-name` also accepts a log group directly, and `--arn` accepts a Lambda or EC2 ARN,
qualified ones included:

```bash
fireeye --trace Bill --resource-name /aws/lambda/lambda_name
fireeye --trace Bill --arn arn:aws:lambda:us-east-1:123456789012:function:lambda_name:PROD
```

##### Monitor EC2 instances

EC2 log groups are named by whoever set up the CloudWatch agent, so pass the group explicitly.
Logs are scoped to the streams belonging to the instance.

```bash
fireeye --trace "Out of memory" --resource-name i-0abc1234 --log-group /var/log/syslog
```

Instance scoping assumes the CloudWatch agent writes one stream per instance named after the
instance ID, which is what `"log_stream_name": "{instance_id}"` produces. Verified against agent
1.300069.1 on Amazon Linux 2023.

If your agent uses something else, `{hostname}` or a fixed string, then `--resource-name i-0abc1234`
matches no streams and returns nothing. FireEye cannot tell that apart from a search that genuinely
found no lines. Search the group directly instead, which reads every stream in it:

```bash
fireeye --trace "Out of memory" --resource-name /var/log/syslog
```

Check what your agent is doing with `aws logs describe-log-streams --log-group-name <group>`.

##### Search

`--trace` is a plain substring match by default. Pass `--regex` to use a CloudWatch regex
instead, which also gets you case-insensitive and multi-term searches:

```bash
fireeye --trace '(?i)error|timeout' --resource-name lambda_name --regex --days 7 --limit 200
```

`--days` sets how far back to look (default 3) and `--limit` caps the number of lines
returned (default 100). Both must be 1 or greater.

Without `--trace` the search term defaults to `duration`.

##### Get alerts on a Slack channel

```bash
export SLACK_URL=https://slack-webhook-url
fireeye --trace Bill --resource-name lambda_name --slack-url

# or pass it inline
fireeye --trace Bill --resource-name lambda_name --slack-url https://slack-webhook-url
```

An alert that cannot be delivered is an error, not a warning: if the webhook is unreachable, returns a
non-200, or is not set at all, FireEye exits 1. Long results are trimmed to fit Slack's message limit and
the remainder is counted in a trailing line.

### Output and exit status

Matched log lines go to stdout. Everything else, banner and progress and errors, goes to stderr, so
results can be piped or redirected on their own:

```bash
fireeye --trace ERROR --resource-name lambda_name > matches.txt
```

| Status | Meaning |
| --- | --- |
| 0 | Ran successfully, whether or not anything matched |
| 1 | Failed: no credentials, no region, missing log group, access denied, bad query, Slack alert not delivered |
| 2 | Bad arguments |

Errors print as a single line. Add `--debug` for the full traceback.

This makes it usable from cron:

```bash
0 * * * * fireeye --trace ERROR --resource-name lambda_name --slack-url || logger fireeye failed
```

### Development

```bash
python3 test_fireeye.py
```

No test framework needed. The checks cover ARN parsing, query building and escaping, result handling,
and the Slack payload, and they make no AWS calls.

Packaging is declared in `pyproject.toml`, and the version comes from `fireeye.__version__`. To build
the distributions locally:

```bash
pip install build
python -m build
```

##### Testing against a local AWS

[MiniStack](https://github.com/ministackorg/ministack) emulates CloudWatch Logs locally, so the AWS
paths can be exercised without touching a real account or paying for Logs Insights scans. It is pure
Python and needs no Docker.

```bash
pip install ministack
ministack -d          # starts on port 4566, `ministack --stop` to stop
```

Seed a log group with a Lambda stream and an EC2 style stream:

```python
import time, boto3

logs = boto3.client(
    "logs", region_name="us-east-1", endpoint_url="http://127.0.0.1:4566",
    aws_access_key_id="test", aws_secret_access_key="test",
)
group = "/aws/lambda/example-fn"
logs.create_log_group(logGroupName=group)

now = int(time.time() * 1000)
for stream, events in {
    "2026/01/01/[$LATEST]aaaa": ["REPORT RequestId: 1111\tDuration: 514.37 ms", "ERROR exploded"],
    "i-0abc1234": ["kernel: Out of memory: Killed process 999"],
}.items():
    logs.create_log_stream(logGroupName=group, logStreamName=stream)
    logs.put_log_events(
        logGroupName=group, logStreamName=stream,
        logEvents=[{"timestamp": now - 1000 * i, "message": m} for i, m in enumerate(events)],
    )
```

Point FireEye at it with `AWS_ENDPOINT_URL` and any non-empty credentials:

```bash
export AWS_ENDPOINT_URL=http://127.0.0.1:4566
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1

fireeye --resource-name example-fn --trace ERROR --regex
fireeye --resource-name i-0abc1234 --log-group /aws/lambda/example-fn --trace '(?i)out of memory' --regex
```

Two differences from real CloudWatch are worth knowing before you trust a result:

- MiniStack does not apply `filter @message like "text"`, the quoted form, and returns every event
  instead. The regex form, `like /text/`, filters correctly. So use `--regex` locally. Real
  CloudWatch filters both, verified against a live account.
- A query run immediately after seeding can come back empty. Retry before believing it.

MiniStack cannot tell you whether a CloudWatch agent on a real instance names its streams after the
instance ID. That is a matter of how the agent is configured, not something the code decides.

### To Do

- [x] EC2 Log Monitoring
- [x] Send alerts on slack channel
- [x] Improved search capabilities

### Contributions

You're welcome to open PR for making direct contributions to the project. Additionally, "Issues" section will
be considered for
- bug reports
- feature requests