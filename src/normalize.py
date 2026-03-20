import os
import json
import sys
import pandas as pd

# Allow relative sibling imports
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

def main():
    input_filepath = os.path.join(base_dir, 'data', 'processed', 'prs_graphql_detailed.json')
    output_dir = os.path.join(base_dir, 'data', 'transform')
    
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            raw_prs = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find '{input_filepath}'. Please run the GraphQL pipeline first.")
        sys.exit(1)
        
    prs_data = []
    reviews_data = []
    comments_data = []
    
    for pr in raw_prs:
        pr_id = pr.get('number')
        if not pr_id:
            continue
            
        pr_author = pr.get('author', {}).get('login') if pr.get('author') else None
        
        # 1. Populate PRs Table
        prs_data.append({
            'pr_id': pr_id,
            'title': pr.get('title'),
            'author': pr_author,
            'created_at': pr.get('createdAt'),
            'merged_at': pr.get('mergedAt'),
            'additions': pr.get('additions', 0),
            'deletions': pr.get('deletions', 0)
        })
        
        # 2. Populate PR Reviews Table
        if 'reviews' in pr and pr['reviews'] and 'nodes' in pr['reviews']:
            for review in pr['reviews']['nodes']:
                if not review: continue
                
                reviewer = review.get('author', {}).get('login') if review.get('author') else None
                
                # Exclude the PR author from reviews
                if reviewer != pr_author:
                    reviews_data.append({
                        'pr_id': pr_id,
                        'reviewer': reviewer,
                        'state': review.get('state')
                    })
                    
        # 3. Populate PR Inline Comments Table
        if 'reviewThreads' in pr and pr['reviewThreads'] and 'nodes' in pr['reviewThreads']:
            for thread in pr['reviewThreads']['nodes']:
                if not thread: continue
                
                if 'comments' in thread and thread['comments'] and 'nodes' in thread['comments']:
                    for comment in thread['comments']['nodes']:
                        if not comment: continue
                        
                        commenter = comment.get('author', {}).get('login') if comment.get('author') else None
                        
                        # Exclude the PR author from this loop
                        if commenter != pr_author:
                            comments_data.append({
                                'pr_id': pr_id,
                                'commenter': commenter
                            })
                            
    # Transform to DFs specifying strict ordering requested by the rules
    df_prs = pd.DataFrame(prs_data, columns=[
        'pr_id', 'title', 'author', 'created_at', 'merged_at', 'additions', 'deletions'
    ])
    
    df_reviews = pd.DataFrame(reviews_data, columns=[
        'pr_id', 'reviewer', 'state'
    ])
    
    df_comments = pd.DataFrame(comments_data, columns=[
        'pr_id', 'commenter'
    ])
    
    # Save datasets locally safely using PyArrow backing implemented in Pandas to_parquet
    os.makedirs(output_dir, exist_ok=True)
    df_prs.to_parquet(os.path.join(output_dir, 'prs.parquet'), engine='pyarrow', index=False)
    df_reviews.to_parquet(os.path.join(output_dir, 'reviews.parquet'), engine='pyarrow', index=False)
    df_comments.to_parquet(os.path.join(output_dir, 'comments.parquet'), engine='pyarrow', index=False)
    
    print("\nNormalization Script Success.")
    print(f" -> Generated {len(df_prs)} rows inside `prs.parquet`")
    print(f" -> Generated {len(df_reviews)} rows inside `reviews.parquet`")
    print(f" -> Generated {len(df_comments)} rows inside `comments.parquet`")

if __name__ == "__main__":
    main()