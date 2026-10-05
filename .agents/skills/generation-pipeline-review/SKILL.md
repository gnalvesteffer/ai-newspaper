---
name: daily-signal-generation-pipeline-review
description: Diagnose and improve how topic searches become accepted, summarized articles, especially when output falls short of the requested count.
---

# Generation pipeline review

Use when a paper returns too few articles, generation is slow, or search, screening, scraping, and summary stages need tuning. Read [project-guide](../project-guide/SKILL.md) before changing pipeline ownership or queue behavior.

- Follow candidates end to end: planned searches, raw results, deduplication, date/location checks, relevance screening, article reads, summaries, and accepted output. Use `research_coverage` and generation logs to locate where candidates disappear.
- Compare requested target with accepted unique stories, not raw search hits. Distinguish no coverage from invalid dates, duplicates, irrelevant results, blocked retrieval, and model failures.
- Exercise natural-language, keyword-like, comma-containing place names, long prompts with constraints, broad interests, and scarce local topics. Let the configured model plan useful search angles; do not split commas or add generic-topic heuristics as a substitute for meaning.
- Improve yield with relevant independent searches and reserve candidates while respecting recency, geography, relevance, publisher diversity, and the requested cap. Never pad with unrelated stories or count duplicate feeds as distinct articles.
- Preserve accepted partial output if a later worker fails. Keep search/scrape work independently queued from LLM calls where possible; measure time by stage before tuning concurrency or caching.
- Treat the personalized feature's supplemental research as a separate output from the paper quota. Check that the configured model chooses focused follow-up queries from the topic and coverage gaps, direct publisher pages are read in parallel with cancellation support, failures leave the accepted paper usable and are explained in the UI even when no queries were planned, and cited `web-*` sources stay separate from story counts. Validate deck, section, and visual citations against exact quote presence in retrieved source text for traceability; this does not prove semantic support of the paraphrase. Require a quote for workflow feedback arrows too. Preserve source text and dates/status for saved-edition chat and explanations. For local topics, verify supplemental research retains place boundaries; older background must not be presented as recent news.
- Add deterministic tests for replenishing rejected slots, late failures, cancellation, and scope propagation when implementation changes. Supplement mocks with a small authorized live run; record requested/accepted counts, elapsed time, and coverage.
- Report whether output met the request and why. Avoid claiming a yield improvement from raw candidate counts or fixture-only UI screenshots.
