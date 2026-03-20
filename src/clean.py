import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

BOT_FILE = Path(__file__).parent / "../config/known_bots.json"

with open(BOT_FILE, "r") as f:
    BOT_BLOCKLIST = set(json.load(f)["known_bots"])


def is_bot(username):
    """
    Determine if a username is a bot using:
    1. Known bot blocklist (primary signal)
    2. Heuristic fallbacks (secondary)
    """
    if not username:
        return False
        
    username_lower = username.lower()
    
    if username_lower in BOT_BLOCKLIST:
        return True
        
    if '[bot]' in username_lower:
        return True
        
    if username_lower.endswith('-bot'):
        return True
        
    return False


def is_human(username):
    return not is_bot(username)

EMPLOYEE_CACHE_FILE = Path(__file__).parent / "../config/posthog_employees.json"







