# Intro

Author: Peter Lu
Date: 2026-03-19

---

In this problem, I want to measure engineering impact by how much an engineer accelerates and enables the rest of the team. My goal is to understand how impactful engineers are. An impactful engineer doesn't just ship their own code. They unblock peers and raise the codebase's quality through active mentorship. 

# Domain: PostHog
PostHog is a open source github organization with a lot of repositories. We are interested in measuring the impact of engineers in this organization. 

# Data Source
Data is collected by using Github REST and GraphQL APIs. The data is stored in the `data/processed` directory. The REST API allowed me to pull PR numbers and metadata within a 90 day window between December 18th, 2025 and March 18th, 2026. The GraphQL API allowed me to pull PR reviews and comments within the same time window and provide a better recursive trace of reviews and comments from a top level PR.

# Data Schema

## PRs Table

========================================
df_prs:
   pr_id       author            created_at             merged_at  additions  deletions
0  44621  andrewm4894  2026-01-09T10:56:03Z  2026-01-09T11:14:40Z         27         24
1  44618       frankh  2026-01-09T10:38:30Z  2026-01-09T11:06:37Z          2          1
2  44614    jonmcwest  2026-01-09T10:06:36Z  2026-01-09T10:45:48Z         29          6
3  44611      skoob13  2026-01-09T09:58:46Z  2026-01-09T10:21:48Z          4          2
4  44609    jonmcwest  2026-01-09T09:22:05Z  2026-01-09T10:21:42Z         10          6
========================================

df_reviews:
   pr_id       reviewer      state  is_bot
0  44621   cubic-dev-ai  COMMENTED    True
1  44621  greptile-apps  COMMENTED    True
2  44621      Gilbert09   APPROVED   False
3  44618      jonmcwest   APPROVED   False
4  44618   cubic-dev-ai  COMMENTED    True
========================================

df_comments:
   pr_id                      commenter  is_bot
0  44618  copilot-pull-request-reviewer    True
1  44618                  greptile-apps    True
2  44618                  greptile-apps    True
3  44614  copilot-pull-request-reviewer    True
4  44599                  greptile-apps    True
========================================