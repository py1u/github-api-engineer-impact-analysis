import os
import pandas as pd
from src.engineer import pr_cycle_time, pr_inferred_type, append_is_employee, append_is_bot

def get_dataframes():
    """
    Reads the base Parquet output from the normalization stage and layers on all 
    engineered attributes and data transformations prior to analytical UI ingestion.
    """
    df_prs = pd.read_parquet("data/transform/prs.parquet", engine="pyarrow")
    df_reviews = pd.read_parquet("data/transform/reviews.parquet", engine="pyarrow")
    df_comments = pd.read_parquet("data/transform/comments.parquet", engine="pyarrow")
    
    if 'merged_at' in df_prs.columns:
        df_prs['merged_at'] = pd.to_datetime(df_prs['merged_at'])
    if 'additions' not in df_prs.columns:
        df_prs['additions'] = 0
    if 'deletions' not in df_prs.columns:
        df_prs['deletions'] = 0
        
    # Append cycle time calculations to DataFrame
    df_prs = pr_cycle_time(df_prs)
    
    # Infer PR types from title
    df_prs = pr_inferred_type(df_prs)
    
    # Add engineered boolean flags
    df_prs = append_is_employee(df_prs, 'author')
    df_reviews = append_is_employee(df_reviews, 'reviewer')
    df_comments = append_is_employee(df_comments, 'commenter')
    
    df_prs = append_is_bot(df_prs, 'author')
    df_reviews = append_is_bot(df_reviews, 'reviewer')
    df_comments = append_is_bot(df_comments, 'commenter')
    
    return df_prs, df_reviews, df_comments