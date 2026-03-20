import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from src.clean import is_bot

EMPLOYEE_CACHE_FILE = Path(__file__).parent / "../config/posthog_employees.json"

def _load_or_fetch_employees():
    if EMPLOYEE_CACHE_FILE.exists():
        with open(EMPLOYEE_CACHE_FILE, "r") as f:
            return set(json.load(f))
            
    users_file = Path(__file__).parent / "../data/processed/users.txt"
    if not users_file.exists():
        return set()
        
    with open(users_file, "r") as f:
        content = f.read().strip()
        
    if not content:
        return set()
        
    try:
        import ast
        
        load_dotenv()
        TOKEN = os.getenv('TOKEN')
        headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
        
        # Parse the comma-separated quoted string into a Python list
        users_list = ast.literal_eval(f"[{content}]")
        employees = set()
        
        print(f"Checking {len(users_list)} contributors against GitHub API for company tags...")
        for user in users_list:
            if is_bot(user):
                continue
                
            url = f"https://api.github.com/users/{user}"
            resp = requests.get(url, headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                company = data.get("company")
                if company and "posthog" in company.lower():
                    employees.add(user)
                
        # Cache results to prevent hitting rate limits on future runs
        EMPLOYEE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EMPLOYEE_CACHE_FILE, "w") as f:
            json.dump(list(employees), f, indent=4)
            
        return employees
        
    except Exception as e:
        print(f"Warning: Failed to fetch employee list: {e}")
        return set()

# Initialize at module load so it doesn't incur constant file I/O
POSTHOG_EMPLOYEES = _load_or_fetch_employees()

def is_posthog_employee(username):
    if not username:
        return False
    return username in POSTHOG_EMPLOYEES


def append_is_employee(df, user_column):
    """
    Adds an 'is_employee' boolean column by mapping the given user column
    through the PostHog employee cache.
    """
    if user_column in df.columns:
        df['is_employee'] = df[user_column].apply(is_posthog_employee)
    return df

def append_is_bot(df, user_column):
    """
    Adds an 'is_bot' boolean column using the string-matching algorithm.
    """
    if user_column in df.columns:
        df['is_bot'] = df[user_column].apply(is_bot)
    return df


def pr_cycle_time(df):
    if 'created_at' in df.columns and 'merged_at' in df.columns:
        created = pd.to_datetime(df['created_at'])
        merged = pd.to_datetime(df['merged_at'])
        df['pr_duration'] = merged - created
    else:
        df['pr_duration'] = pd.NaT
        
    return df


def pr_inferred_type(df):
    if 'title' not in df.columns:
        df['pr_type'] = 'unknown'
        return df
        
    weights_path = Path(__file__).parent / "../config/type_weights.json"
    valid_types = set()
    if weights_path.exists():
        with open(weights_path, 'r') as f:
            valid_types = set(json.load(f).keys())
            
    # Extract conventional commit type from the title string
    extracted = df['title'].str.extract(r'^([a-zA-Z]+)(?:\(.*\))?:', expand=False)
    extracted = extracted.str.lower()
    
    # Keep type if valid, otherwise map it to 'unknown'
    df['pr_type'] = extracted.where(extracted.isin(valid_types), 'unknown')
    
    return df

    
