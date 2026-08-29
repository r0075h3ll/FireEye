import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

__version__ = "0.7.0"


def banner():
    # stderr, so it does not end up in piped or redirected search results
    print(f"\n\tFireEye v{__version__}\n", file=sys.stderr)


banner()
