# Report

Author: Peter Lu
Date: 2026-03-19

---

Start: 2026-03-19 6:48 PM
End: 2026-03-19 8:15 PM

Recorded Time: 87 minutes

# Analysis(max: 300 words)

I believe impact is when an engineer is conscience of the team's goals and proactively works to help the team succeed. This means they unblock peers, raise the codebase's quality through active mentorship, and proactively collaborate with teammates from different backgrounds. It is not just about shipping code, it is about enabling others and being passionate and empathetic about the customer as much as their teammates and their product.

My approach to defining engineering impact at PostHog centers on "team leverage"—measuring not just what an engineer ships, but how they accelerate others. This was executed in three distinct phases:

1. Targeted Data Extraction
Instead of blindly pulling commit counts, I first researched PostHog’s engineering documentation to understand their specific use of Conventional Commits. To handle the massive scale of their repository without hitting rate limits, I bypassed the REST API's N+1 problem and utilized GitHub's GraphQL API. This allowed me to efficiently extract 90 days of merged Pull Requests, peer reviews, and nested comment threads in a single, paginated payload.

2. Metric Engineering & Transformation
Raw counts are inherently noisy. Using Python and Pandas, I rigorously filtered the data to remove bot accounts, automated dependency updates, and self-reviews. I then engineered a normalized "Total Impact Score" based on three weighted pillars:

Impact 1 (1.0x): PRs shipped, dynamically weighted by PR type (e.g., feat > chore).

Impact 2 (1.5x): Peer approvals that unblock the CI/CD pipeline.

Impact 3 (2.5x): High-effort inline code comments (>5 words) that upskill the team.

Velocity Tie-Breaker: Median PR cycle time.

3. Data Visualization
Deployed Streamlit dashboard to surface these insights. To prevent volume bias, all metrics are normalized (0 to 1) against the team maximums. I prioritized visualization over tabular metrics to provide a global view of the top engineers impact compared to the rest of the organization.
