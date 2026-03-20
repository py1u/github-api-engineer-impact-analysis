import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')

def get_pr_details(pr_number):
    """Fetch detailed information for a specific Pull Request."""
    url = f"https://api.github.com/repos/PostHog/posthog/pulls/{pr_number}"
    print(f"Fetching details for PR #{pr_number}...")
    
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
        
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Sleep to respect GitHub rate limits
    time.sleep(1)
    
    return response.json()

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_filepath = os.path.join(base_dir, "data", "processed", "prs.json")
    output_dir = os.path.join(base_dir, "data", "processed")
    output_filepath = os.path.join(output_dir, "prs_detailed.json")
    
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_filepath):
        print(f"Input file not found at {input_filepath}. Please run extract_prs.py first.")
        return
        
    with open(input_filepath, "r", encoding="utf-8") as f:
        prs_list = json.load(f)
        
    detailed_prs = []
    
    print(f"Found {len(prs_list)} PRs to process...")
    
    for pr_info in prs_list:
        pr_num = pr_info.get("PR number")
        if not pr_num:
            continue
            
        try:
            data = get_pr_details(pr_num)
            
            # Extract only the specified fields
            extracted = {
                "pr_number": data.get("number"),
                "pr_title": data.get("title"),
                "state": data.get("state"),
                "user.login": data.get("user", {}).get("login") if data.get("user") else None,
                "created_at": data.get("created_at"),
                "closed_at": data.get("closed_at"),
                "merged_at": data.get("merged_at"),
                "additions": data.get("additions"),
                "deletions": data.get("deletions"),
                "comments": data.get("comments"),
                "review_comments": data.get("review_comments"),
                "commits": data.get("commits")
            }
            detailed_prs.append(extracted)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching PR #{pr_num}: {e}")
            
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(detailed_prs, f, indent=4)
        
    print(f"\nSaved detailed information for {len(detailed_prs)} PRs to {output_filepath}")

if __name__ == "__main__":
    main()
