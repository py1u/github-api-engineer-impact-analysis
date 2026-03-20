# for testing small scripts

import pandas as pd

df_prs = pd.read_parquet("../data/transform/prs.parquet", engine="pyarrow")
df_reviews = pd.read_parquet("../data/transform/reviews.parquet", engine="pyarrow")
df_comments = pd.read_parquet("../data/transform/comments.parquet", engine="pyarrow")

print("df_prs:")
print(df_prs.head())
print("="*40)
print("df_reviews:")
print(df_reviews.head())
print("="*40)
print("df_comments:")
print(df_comments.head())
print("="*40)
