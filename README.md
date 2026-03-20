# Engineering Impact Analysis

## Introduction
In this problem, I want to measure engineering impact by how much an engineer accelerates and enables the rest of the team. My goal is to understand how impactful engineers are. An impactful engineer doesn't just ship their own code. They unblock peers and raise the codebase's quality through active mentorship. 

I believe impact is when an engineer is conscience of the team's goals and proactively works to help the team succeed. This means they unblock peers, raise the codebase's quality through active mentorship, and proactively collaborate with teammates from different backgrounds. It is not just about shipping code, it is about enabling others and being passionate and empathetic about the customer as much as their teammates and their product.

My approach to defining engineering impact centers on "team leverage"—measuring not just what an engineer ships, but how they accelerate others.

## Domain: PostHog
PostHog is a open source github organization with a lot of repositories. We are interested in measuring the impact of engineers in this organization. 

## Data Source
Data is collected by using Github REST and GraphQL APIs. The data is stored in the `data/processed` directory. The REST API allowed me to pull PR numbers and metadata within a 90 day window between December 18th, 2025 and March 18th, 2026. 

To handle the massive scale of their repository without hitting rate limits, I bypassed the REST API's N+1 problem and utilized GitHub's GraphQL API. This allowed me to pull PR reviews and comments within the same time window and provide a better recursive trace of reviews and comments from a top level PR.

## Methodology

This was executed in three distinct phases:

### 1. Targeted Data Extraction
Instead of blindly pulling commit counts, I first researched PostHog’s engineering documentation to understand their specific use of Conventional Commits. The GraphQL API allowed me to efficiently extract 90 days of merged Pull Requests, peer reviews, and nested comment threads in a single, paginated payload.

### 2. Metric Engineering & Transformation
Raw counts are inherently noisy. Using Python and Pandas, I rigorously filtered the data to remove bot accounts, automated dependency updates, and self-reviews. I then engineered a normalized "Total Impact Score" based on three weighted pillars:

- Impact 1 (1.0x): PRs shipped, dynamically weighted by PR type (e.g., feat > chore).
- Impact 2 (1.5x): Peer approvals that unblock the CI/CD pipeline.
- Impact 3 (2.5x): High-effort inline code comments that upskill the team.
- Velocity Tie-Breaker: Median PR cycle time.

### 3. Data Visualization
Deployed Streamlit dashboard to surface these insights. To prevent volume bias, all metrics are normalized (0 to 1) against the team maximums. I prioritized visualization over tabular metrics to provide a global view of the top engineers impact compared to the rest of the organization.

## Structure

I structured this project as modular as possible for data collection, transformation, and aggregation of impact metrics. The purpose was to provide readability and clear seperation of concerns making debugging and future enhancements in the project possible.

```
.
├── __pycache__
├── api
│   ├── extract_pr_details.py
│   ├── extract_pr_recursive.py
│   └── extract_prs.py
├── app.py
├── config
│   ├── known_bots.json
│   ├── posthog_employees.json
│   └── type_weights.json
├── data
│   ├── processed
│   ├── raw
│   └── transform
├── docs
│   ├── agent_sessions
│   ├── intro.md
│   ├── samples
│   └── structure
├── instructions.md
├── main.py
├── pyproject.toml
├── README.md
├── report.md
├── requirements.txt
├── src
│   ├── __init__.py
│   ├── clean.py
│   ├── engineer.py
│   └── normalize.py
└── test
```

## Dependencies
The `requirements.txt` file outlines the core libraries used to power this analysis:
- **Pandas and PyArrow**: Used for robust DataFrame manipulation and Parquet serialization.
- **Requests**: Handled direct REST limits and GraphQL API pagination queries.
- **Python-dotenv**: Loaded personal GitHub tokens securely from the environment.
- **Streamlit and Plotly Express**: Used to design, cache, and deploy the interactive data dashboard visually.
