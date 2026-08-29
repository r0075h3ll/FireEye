<div align="center">
    <a href="https://github.com/r0075h3ll/FireEye"><img alt="FireEye" src="/static/logo/fireeye.png" width="100"/></a>
    <h2>
    FireEye
    </h2>
</div>

<h4 align="center">AWS Monitoring Toolkit</h4>

<div align="center">
<img src="https://img.shields.io/badge/License-Apache%202.0-blue">
<img src="https://img.shields.io/badge/Python-3.12-blue">
<img src="https://img.shields.io/badge/Release-0.7.0-green">
</div>

\
FireEye is an AWS monitoring toolkit for DevOps, Security, and IT teams. It can currently trace strings in AWS Lambda function(s) output logs via CloudWatch using simple [commands](#monitor-lambda-functions-w-cloudwatch-logs-insights).

[//]: # (insert gif)
[![asciicast](https://asciinema.org/a/696182.svg)](https://asciinema.org/a/696182)

### Installation

```bash
git clone https://github.com/r0075h3ll/FireEye && cd FireEye
pip install setuptools
python3 setup.py install

# or

pip3 install FireEye-AWS
```

### Features

##### Monitor Lambda functions w/ CloudWatch Logs Insights

```bash
fireeye --trace Bill --resource-name lambda_name
```

##### Monitor EC2 instances

EC2 log groups are named by whoever set up the CloudWatch agent, so pass the group explicitly.
Logs are scoped to the streams belonging to the instance.

```bash
fireeye --trace "Out of memory" --resource-name i-0abc1234 --log-group /var/log/syslog
```

##### Search

`--trace` is a plain substring match by default. Pass `--regex` to use a CloudWatch regex
instead, which also gets you case-insensitive and multi-term searches:

```bash
fireeye --trace '(?i)error|timeout' --resource-name lambda_name --regex --days 7 --limit 200
```

`--days` sets how far back to look (default 3) and `--limit` caps the number of lines
returned (default 100).

##### Get alerts on a Slack channel

```bash
export SLACK_URL=https://slack-webhook-url
fireeye --trace Bill --resource-name lambda_name --slack-url

# or pass it inline
fireeye --trace Bill --resource-name lambda_name --slack-url https://slack-webhook-url
```

### To Do

- [x] EC2 Log Monitoring
- [x] Send alerts on slack channel
- [x] Improved search capabilities

### Contributions

You're welcome to open PR for making direct contributions to the project. Additionally, "Issues" section will
be considered for
- bug reports
- feature requests