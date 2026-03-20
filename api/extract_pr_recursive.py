import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')
GRAPHQL_URL = "https://api.github.com/graphql"

def run_graphql_query(query, variables=None):
    """Executes a GraphQL query against the GitHub API."""
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    
    response = requests.post(
        GRAPHQL_URL,
        json={'query': query, 'variables': variables},
        headers=headers
    )
    response.raise_for_status()
    
    # Sleep to respect rate limit points (GraphQL limits can be strict)
    time.sleep(2)
    return response.json()

def get_total_count(start_str, end_str):
    """Fallback to the REST API for a simple/lightweight count, identical to previous chunking."""
    url = f"https://api.github.com/search/issues?q=repo:PostHog/posthog+is:pr+is:merged+base:master+merged:{start_str}..{end_str}&per_page=1"
    
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    time.sleep(2)
    return response.json().get('total_count', 0)

def get_chunks(start_date, end_date):
    """Recursively split date range if it contains 1000 or more items."""
    chunks = []
    
    def split_range(s, e):
        s_str = s.strftime("%Y-%m-%dT%H:%M:%SZ")
        e_str = e.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        count = get_total_count(s_str, e_str)
        print(f"  Count {s_str} - {e_str}: {count}")
        
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
    output_dir = os.path.join(base_dir, "data", "processed")
    output_filepath = os.path.join(output_dir, "prs_graphql_detailed.json")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Base date range aligned with the PostHog query
    start_date = datetime(2025, 12, 18, tzinfo=timezone.utc)
    end_date = datetime(2026, 3, 18, tzinfo=timezone.utc)
    
    print("Determining chunks to avoid GitHub Search API 1000 node limit...")
    date_chunks = get_chunks(start_date, end_date)
    
    all_prs = []
    
    # GraphQL carefully selecting only the attributes specified
    graphql_query = """
    query ($queryString: String!, $cursor: String) {
      search(query: $queryString, type: ISSUE, first: 25, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          ... on PullRequest {
            number
            title
            url
            author {
              login
            }
            createdAt
            mergedAt
            additions
            deletions
            changedFiles
            
            reviews(first: 10) {
              nodes {
                author {
                  login
                }
                state
                createdAt
              }
            }
            
            reviewThreads(first: 10) {
              nodes {
                isResolved
                comments(first: 5) {
                  nodes {
                    author {
                      login
                    }
                    bodyText
                    createdAt
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    print("\nStarting extraction per chunk utilizing GraphQL...")
    for s_str, e_str in date_chunks:
        print(f"\nFetching chunk: {s_str} to {e_str}")
        cursor = None
        has_next_page = True
        
        # Ensure we filter explicitly identical to the chunking rules
        query_string = f"repo:PostHog/posthog is:pr is:merged base:master merged:{s_str}..{e_str}"
        
        page = 1
        while has_next_page:
            print(f"  Fetching GraphQL page {page}...")
            
            variables = {
                "queryString": query_string,
                "cursor": cursor
            }
            
            try:
                result = run_graphql_query(graphql_query, variables)
                
                # Halt if valid GraphQL syntax but endpoint throws permission/quota errors
                if "errors" in result:
                    print(f"GraphQL Errors encountered: {result['errors']}")
                    break
                    
                search_data = result.get("data", {}).get("search", {})
                nodes = search_data.get("nodes", [])
                
                # Append the clean dictionary shapes returned by GraphQL directly
                all_prs.extend(nodes)
                
                page_info = search_data.get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")
                
                page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching GraphQL API: {e}")
                break
                
    # Save the aggregated dataset
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(all_prs, f, indent=4)
        
    print(f"\nSaved {len(all_prs)} detailed PRs to {output_filepath}")

if __name__ == "__main__":
    main()
