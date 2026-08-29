import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

__version__ = "0.7.0"


def banner():
    print(f"\n\tFireEye v{__version__}\n")


banner()
