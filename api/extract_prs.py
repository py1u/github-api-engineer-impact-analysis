import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')

def get_total_count(start_str, end_str):
    """Make a lightweight query to get the total number of items in the date range."""
    url = f"https://api.github.com/search/issues?q=repo:PostHog/posthog+is:pr+is:merged+base:master+merged:{start_str}..{end_str}&per_page=1"
    print(f"Checking count for {start_str} to {end_str}...")
    
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Sleep to respect GitHub Search API limits (30 req/min auth'd, 10 req/min unauth'd)
    time.sleep(2)
    
    return response.json().get('total_count', 0)

def get_chunks(start_date, end_date):
    chunks = []
    
    def split_range(s, e):
        # Format dates in ISO8601 for precise querying
        s_str = s.strftime("%Y-%m-%dT%H:%M:%SZ")
        e_str = e.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        count = get_total_count(s_str, e_str)
        print(f"  Count: {count}")
        
        # If count == 1000, pagination will query page=11 and crash (since 10*100 = 1000). So we must use strictly < 1000.
        if count < 1000:
            chunks.append((s_str, e_str))
        else:
            mid = s + (e - s) / 2
            split_range(s, mid)
            split_range(mid + timedelta(seconds=1), e)
            
    split_range(start_date, end_date)
    return chunks

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw")
    processed_dir = os.path.join(base_dir, "data", "processed")
    
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    # Overall target range based on original query: 2025-12-18 to 2026-03-18
    start_date = datetime(2025, 12, 18, tzinfo=timezone.utc)
    end_date = datetime(2026, 3, 18, tzinfo=timezone.utc)
    
    print("Determining chunks to avoid API result limits (total < 1000 items per search)...")
    date_chunks = get_chunks(start_date, end_date)
    
    all_raw_items = []
    all_processed_data = []

    print("\nStarting extraction per chunk...")
    for s_str, e_str in date_chunks:
        print(f"\nFetching chunk: {s_str} to {e_str}")
        page = 1
        
        while True:
            print(f"  Fetching page {page}...")
            url = f"https://api.github.com/search/issues?q=repo:PostHog/posthog+is:pr+is:merged+base:master+closed:{s_str}..{e_str}&per_page=100&page={page}"
            
            headers = {}
            if TOKEN:
                headers["Authorization"] = f"Bearer {TOKEN}"

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Sleep to respect rate limits
            time.sleep(2)
            
            items = data.get("items", [])
            if not items:
                break
                
            all_raw_items.extend(items)
            
            # Process incoming items
            for pr in items:
                extracted = {
                    "PR number": pr.get("number"),
                    "created_at": pr.get("created_at"),
                    "closed_at": pr.get("closed_at")
                }
                all_processed_data.append(extracted)
                
            # If we received less than per_page items, we're on the last page of this chunk
            if len(items) < 100:
                break
            
            page += 1

    # Save aggregated raw data
    raw_filepath = os.path.join(raw_dir, "prs.json")
    with open(raw_filepath, "w", encoding="utf-8") as f:
        # Wrap the list in a dict to mimic original GitHub API structure if desired,
        # but storing as a large array of items is often preferred when aggregated.
        json.dump({"items": all_raw_items, "total_count": len(all_raw_items)}, f, indent=4)
    print(f"\nSaved {len(all_raw_items)} raw PRs to {raw_filepath}")
    
    # Save processed data
    processed_filepath = os.path.join(processed_dir, "prs.json")
    with open(processed_filepath, "w", encoding="utf-8") as f:
        json.dump(all_processed_data, f, indent=4)
    print(f"Saved {len(all_processed_data)} processed PRs to {processed_filepath}")

if __name__ == "__main__":
    main()

