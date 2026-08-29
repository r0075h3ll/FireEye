import logging
import sys

# Escape codes only when the stream is a terminal, so piped output and log
# files do not fill up with them.
if sys.stdout.isatty():
    end = "\033[00m"
    dark_green = "\033[92m"
else:
    end = ""
    dark_green = ""

if sys.stderr.isatty():
    red = "\033[31m"
    green = "\033[32m"
    reset = "\033[00m"
else:
    red = ""
    green = ""
    reset = ""

formatter = logging.Formatter(
    f"{red}%(asctime)s - %(name)s{reset} :: {green}%(levelname)s - %(message)s{reset}"
)
# Diagnostics go to stderr. Matched log lines are printed to stdout, so the
# two can be separated by whoever is calling.
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)

logger.setLevel("INFO")
logger.addHandler(handler)
