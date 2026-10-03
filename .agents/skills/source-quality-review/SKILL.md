---
name: daily-signal-source-quality-review
description: Review whether collected sources are credible, current, relevant to a reader's topic, and faithfully represented in the paper.
---

# Source quality review

Use when investigating questionable articles, improving source selection or summaries, or checking a generated paper for trustworthiness. Read [project-guide](../project-guide/SKILL.md) for source retrieval ownership and evidence-label conventions.

- Trace a sample from search result through resolved destination, extracted text, model input, final headline, summary, and source link. Confirm the link reaches the publisher article, not a search redirect.
- Check publication dates and lookback eligibility; distinguish publication date from crawl/update dates and mark unverified dates honestly.
- Assess relevance to the full topic, including location and editorial boundaries. Treat connected phrases and punctuation as natural language. Identify duplicates by resolved canonical URL and substantially repeated reporting.
- Compare every claim in the summary and “Why it matters” with retrieved source text. Flag unsupported specifics, invented context, overconfident causal claims, and source excerpt limitations.
- Review publisher identity and source diversity. Prefer original reporting or primary documents when available; do not equate domain reputation or search rank with article quality.
- Separate a genuine shortage of relevant reporting from scraper failures, stale feeds, rejected candidates, and duplicate results. Report examples and evidence, not just an overall quality score.
- When changing selection or summarization, preserve source URLs and retrieval labels. Use representative fixtures for common topics and sparse/local topics; live requests need bounded scope and existing user authorization.
