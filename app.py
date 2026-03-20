# deploy with: streamlit run app.py

import pandas as pd
import streamlit as st
import plotly.express as px
from functools import reduce

st.set_page_config(page_title="PostHog Engineering Impact Dashboard", layout="wide")

@st.cache_data
def load_data():
    """Loads and caches the fully engineered dataframes from the static analytics exports."""
    df_prs = pd.read_parquet("data/analytics/prs_engineered.parquet", engine="pyarrow")
    df_reviews = pd.read_parquet("data/analytics/reviews_engineered.parquet", engine="pyarrow")
    df_comments = pd.read_parquet("data/analytics/comments_engineered.parquet", engine="pyarrow")
    
    if 'created_at' in df_prs.columns:
        df_prs['created_at'] = pd.to_datetime(df_prs['created_at'])
    if 'merged_at' in df_prs.columns:
        df_prs['merged_at'] = pd.to_datetime(df_prs['merged_at'])
        
    return df_prs, df_reviews, df_comments

df_prs, df_reviews, df_comments = load_data()

# --- 1. Cycle Time Logic ---
df_prs['cycle_time_hours'] = (df_prs['merged_at'] - df_prs['created_at']).dt.total_seconds() / 3600
cycle_times = df_prs.groupby('author')['cycle_time_hours'].median().reset_index(name='median_cycle_time_hrs')
cycle_times.rename(columns={'author': 'engineer'}, inplace=True)

# --- Relational Joins & Filters ---
df_reviews_joined = pd.merge(df_reviews, df_prs[['pr_id', 'author']], on='pr_id', how='left')
valid_reviews = df_reviews_joined[
    (df_reviews_joined['is_bot'] == False) & 
    (df_reviews_joined['state'] == 'APPROVED') & 
    (df_reviews_joined['reviewer'] != df_reviews_joined['author'])
]

df_comments_joined = pd.merge(df_comments, df_prs[['pr_id', 'author']], on='pr_id', how='left')
# Removed the word_count quality filter (Idea 2) to adhere to constraints
valid_comments = df_comments_joined[
    (df_comments_joined['is_bot'] == False) & 
    (df_comments_joined['commenter'] != df_comments_joined['author'])
]

# --- Aggregations ---
maker_scores = df_prs.groupby('author').size().reset_index(name='prs_shipped')
maker_scores.rename(columns={'author': 'engineer'}, inplace=True)

gatekeeper_scores = valid_reviews.groupby('reviewer').size().reset_index(name='reviews_provided')
gatekeeper_scores.rename(columns={'reviewer': 'engineer'}, inplace=True)

mentor_scores = valid_comments.groupby('commenter').size().reset_index(name='inline_comments')
mentor_scores.rename(columns={'commenter': 'engineer'}, inplace=True)

# Master merge including cycle_times
dataframes = [maker_scores, gatekeeper_scores, mentor_scores, cycle_times]
leaderboard = reduce(
    lambda left, right: pd.merge(left, right, on='engineer', how='outer'),
    dataframes
).fillna(0)

# --- Normalization & Final Scoring ---
leaderboard['norm_prs'] = leaderboard['prs_shipped'] / (leaderboard['prs_shipped'].max() or 1)
leaderboard['norm_reviews'] = leaderboard['reviews_provided'] / (leaderboard['reviews_provided'].max() or 1)
leaderboard['norm_comments'] = leaderboard['inline_comments'] / (leaderboard['inline_comments'].max() or 1)

W_PR = 1.0
W_REVIEW = 1.5
W_MENTOR = 2.5

leaderboard['weighted_pr'] = leaderboard['norm_prs'] * W_PR
leaderboard['weighted_review'] = leaderboard['norm_reviews'] * W_REVIEW
leaderboard['weighted_mentor'] = leaderboard['norm_comments'] * W_MENTOR

leaderboard['total_impact_score'] = (
    leaderboard['weighted_pr'] + 
    leaderboard['weighted_review'] + 
    leaderboard['weighted_mentor']
)

# --- Cycle Time Tie-Breaker ---
# Sort by highest impact score, then by LOWEST (fastest) cycle time
leaderboard = leaderboard.sort_values(
    by=['total_impact_score', 'median_cycle_time_hrs'], 
    ascending=[False, True]
)
top_5 = leaderboard.head(5)

# --- UI Dashboard ---

st.title("PostHog Engineering Impact Dashboard")

st.markdown("""
### Impact Methodology & Derivation
Impact is measured as a composite of three normalized metrics to prevent volume bias, mapped to a weight based on team leverage. 

**The Derivation Formula:**
`Total Score = (Normalized Maker × 1.0) + (Normalized Unblocker × 1.5) + (Normalized Mentor × 2.5)`

* **Maker (1.0x):** Raw PRs Shipped / Max Team PRs
* **Unblocker (1.5x):** Peer Approvals Provided / Max Team Approvals
* **Mentor (2.5x):** Inline Code Comments Provided / Max Team Comments
* **Tie-Breaker:** Median PR Cycle Time (Faster delivery wins ties)
""")

st.markdown("---")
st.header("Top 5 Engineers Analysis")

# --- NEW: Derivation Transparency Table ---
st.subheader("Metrics Derivation Breakdown")
st.markdown("This table illustrates exactly how raw effort translates into the final weighted score.")
derivation_cols = [
    'engineer', 'prs_shipped', 'weighted_pr', 
    'reviews_provided', 'weighted_review', 
    'inline_comments', 'weighted_mentor', 
    'median_cycle_time_hrs', 'total_impact_score'
]
st.dataframe(top_5[derivation_cols].style.format({
    'weighted_pr': '{:.2f}',
    'weighted_review': '{:.2f}',
    'weighted_mentor': '{:.2f}',
    'median_cycle_time_hrs': '{:.1f} hrs',
    'total_impact_score': '{:.2f}'
}), use_container_width=True)


col1, col2 = st.columns(2)

with col1:
    st.subheader("Impact Composition")
    df_melted = top_5.melt(
        id_vars=['engineer'], 
        value_vars=['weighted_pr', 'weighted_review', 'weighted_mentor'],
        var_name='Impact Type', 
        value_name='Weighted Score'
    )
    fig_bar = px.bar(
        df_melted, 
        y='engineer', 
        x='Weighted Score', 
        color='Impact Type', 
        orientation='h',
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("Delivery Velocity (Median Cycle Time)")
    # New chart specifically focusing on the cycle time tie-breaker
    fig_cycle = px.bar(
        top_5,
        x='median_cycle_time_hrs',
        y='engineer',
        orientation='h',
        color='median_cycle_time_hrs',
        color_continuous_scale='Blues_r', # Reversed so darker is faster (better)
        labels={'median_cycle_time_hrs': 'Median Hours from Open to Merge'}
    )
    fig_cycle.update_layout(yaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig_cycle, use_container_width=True)

st.markdown("---")
st.header("Global Team Distribution")

col3, col4 = st.columns(2)

with col3:
    st.subheader("Score Distribution (All Engineers)")
    fig_hist = px.histogram(
        leaderboard, 
        x="total_impact_score", 
        nbins=20,
        marginal="box", 
        labels={'total_impact_score': 'Total Impact Score'},
        color_discrete_sequence=['#3366CC']
    )
    fig_hist.update_layout(yaxis_title="Count of Engineers")
    st.plotly_chart(fig_hist, use_container_width=True)

with col4:
    st.subheader("Share of Top 5 Total Impact")
    fig_pie = px.pie(
        top_5, 
        values='total_impact_score', 
        names='engineer', 
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# --- NEW SECTION: Cohort Analysis & Bots ---
st.markdown("---")
st.header("Cohort Analysis & Bot Operations")
st.markdown("Analyzing how elite contributors scale against the rest of the team, and investigating the footprint of automated dependencies.")

# Classify all contributors
top_5_names = leaderboard.head(5)['engineer'].tolist()
top_10_names = leaderboard.head(10)['engineer'].tolist()
top_50_names = leaderboard.head(50)['engineer'].tolist()
top_100_names = leaderboard.head(100)['engineer'].tolist()

def assign_cohort(engineer, is_bot_val):
    if is_bot_val:
        return 'Bots'
    if engineer in top_5_names:
        return 'Top 5'
    if engineer in top_10_names:
        return 'Top 6-10'
    if engineer in top_50_names:
        return 'Top 11-50'
    if engineer in top_100_names:
        return 'Top 51-100'
    return 'Rest of Humans'

df_prs['cohort'] = df_prs.apply(lambda row: assign_cohort(row['author'], row.get('is_bot', False)), axis=1)
df_reviews['cohort'] = df_reviews.apply(lambda row: assign_cohort(row['reviewer'], row.get('is_bot', False)), axis=1)
df_comments['cohort'] = df_comments.apply(lambda row: assign_cohort(row['commenter'], row.get('is_bot', False)), axis=1)

cohort_order = ['Top 5', 'Top 6-10', 'Top 11-50', 'Top 51-100', 'Rest of Humans', 'Bots']
cohort_colors = {
    'Top 5': '#FF9900', 
    'Top 6-10': '#FFB347', 
    'Top 11-50': '#FFD180', 
    'Top 51-100': '#FFE5B4', 
    'Rest of Humans': '#CCCCCC', 
    'Bots': '#E02424'
}

cohort_prs = df_prs['cohort'].value_counts().reset_index()
cohort_prs.columns = ['cohort', 'Volume']
cohort_prs['Activity Type'] = 'PRs Shipped'

cohort_reviews = df_reviews['cohort'].value_counts().reset_index()
cohort_reviews.columns = ['cohort', 'Volume']
cohort_reviews['Activity Type'] = 'Reviews'

cohort_comments = df_comments['cohort'].value_counts().reset_index()
cohort_comments.columns = ['cohort', 'Volume']
cohort_comments['Activity Type'] = 'Comments'

cohort_activity = pd.concat([cohort_prs, cohort_reviews, cohort_comments])

# 1. Bar Chart
st.subheader("Raw Volume Disparity (Bots vs Teams)")
fig_bar_activity = px.bar(
    cohort_activity,
    x='cohort',
    y='Volume',
    color='Activity Type',
    barmode='group',
    category_orders={'cohort': cohort_order},
    color_discrete_sequence=['#5A99D8', '#44A047', '#E5A93D']
)
st.plotly_chart(fig_bar_activity, use_container_width=True)

col5, col6 = st.columns(2)

with col5:
    st.subheader("PR Delivery Velocity Over Time")
    df_prs_time = df_prs.dropna(subset=['merged_at']).copy()
    time_series_prs = df_prs_time.groupby(
        [pd.Grouper(key='merged_at', freq='W-MON'), 'cohort']
    ).size().reset_index(name='prs_merged')
    
    fig_line_cohort = px.line(
        time_series_prs, 
        x='merged_at', 
        y='prs_merged', 
        color='cohort',
        category_orders={'cohort': cohort_order},
        color_discrete_map=cohort_colors,
        labels={'merged_at': 'Week', 'prs_merged': 'PRs Merged'}
    )
    st.plotly_chart(fig_line_cohort, use_container_width=True)

with col6:
    st.subheader("Heatmap: Task Concentration")
    heatmap_data = cohort_activity.pivot(index='cohort', columns='Activity Type', values='Volume').fillna(0)
    heatmap_data = heatmap_data.reindex(cohort_order)
    
    fig_heatmap = px.imshow(
        heatmap_data.values,
        y=heatmap_data.index,
        x=heatmap_data.columns,
        text_auto=True,
        aspect="auto",
        color_continuous_scale='Magma_r'
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

st.subheader("Scatter: PR Footprint (Additions vs Deletions by Cohort)")
fig_scatter_cohort = px.scatter(
    df_prs, 
    x="additions", 
    y="deletions", 
    color="cohort",
    opacity=0.6,
    log_x=True, 
    log_y=True,
    category_orders={'cohort': cohort_order},
    color_discrete_map=cohort_colors,
    labels={'additions': 'Lines Added (Log)', 'deletions': 'Lines Deleted (Log)'}
)
st.plotly_chart(fig_scatter_cohort, use_container_width=True)