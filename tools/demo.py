"""Builds the sample blog (soloblog/demo.py) into a data folder of its own.

    python tools/demo.py demo-data              # then: DATA_DIR=demo-data python app.py
    python tools/demo.py demo-data --password secret

The folder must be new or empty. Photos are downloaded once into
demo-cache/ beside it and reused next time."""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("data", help="the data folder to build into")
parser.add_argument("--password", default="demo", help="the admin's password (default: demo)")
parser.add_argument("--cache", help="where downloaded photos are kept (default: demo-cache beside the data folder)")
args = parser.parse_args()

data = os.path.abspath(args.data)
if os.path.isdir(data) and os.listdir(data):
    sys.exit(f"{data} isn't empty - pick a new folder")
# config reads these once, when it's first imported
os.environ["DATA_DIR"] = data
os.environ.setdefault("SESSION_SECRET", "demo-builder")
os.environ.setdefault("UPDATE_CHECK", "0")
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import logging  # noqa: E402

from soloblog import demo  # noqa: E402

# what it's doing, on the screen
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
demo.build(args.password, args.cache or os.path.join(os.path.dirname(data), "demo-cache"))
