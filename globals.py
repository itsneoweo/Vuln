import os
import json
from collections import defaultdict
from pathlib import Path
from os import walk

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(SCRIPT_DIR / "config.json")
with open(CONFIG_PATH, 'r') as file:
    CONFIG = json.loads(file.read())

MESSAGES_DIR = Path(SCRIPT_DIR / "messages")
ERRORS_DIR = Path(MESSAGES_DIR / "errors")
INFOS_DIR = Path(MESSAGES_DIR / "infos")

ERRORS = defaultdict()
INFOS = defaultdict()

error_filepaths = [Path(name) for name in next(walk(ERRORS_DIR), (None, None, []))[2]]
info_filepaths = [Path(name) for name in next(walk(INFOS_DIR), (None, None, []))[2]]

for path in error_filepaths:
    with open(ERRORS_DIR / path) as file:
        ERRORS[path.stem] = file.read()

for path in info_filepaths:
    with open(INFOS_DIR / path) as file:
        INFOS[path.stem] = file.read()