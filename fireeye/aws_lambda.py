"""Deprecated alias for :mod:`fireeye.cloudwatch`.

The module was renamed when EC2 support arrived, since the class in it was
never Lambda specific. This keeps `from fireeye.aws_lambda import ...` working
for anyone who wrote against an earlier release.
"""

import warnings

from fireeye.cloudwatch import (  # noqa: F401
    CloudWatch,
    build_query,
    collect_logs,
    is_instance_id,
    parse_arn,
    print_logs,
    quote,
    time_diff,
)

warnings.warn(
    "fireeye.aws_lambda has moved to fireeye.cloudwatch and will be removed in a "
    "future release",
    DeprecationWarning,
    stacklevel=2,
)
