# storage.py
import json
import os
from config import MAX_HISTORY

HISTORY_FILE = "history.json"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-MAX_HISTORY:], f, indent=2)


def add_to_history(history, record):
    history.append(record)
    save_history(history)
    return history[-MAX_HISTORY:]
