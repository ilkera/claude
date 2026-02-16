---
name: classify-trump-post
description: Classify a Trump social media post using the economic/non-economic taxonomy
argument-hint: "post text to classify"
allowed-tools: Bash
---

Classify the given Trump social media post by running the classifier script. Pass the full argument as the post text.

Run this command from the whatsapp-message directory:

```bash
cd /Users/ilkera/Depot/projects/claude-repo/whatsapp-message && python classify_post.py "$ARGUMENTS"
```

Display the JSON result to the user. The output includes:
- `is_economic` — whether the post is about economic topics
- `primary_category` / `subcategory` — topic classification from the taxonomy
- `market_sentiment` — bullish/bearish/neutral (economic posts only)
- `confidence` — classification confidence score
- `summary` — one-sentence summary
- `topics` — hashtag topics
- `relevance_score` — newsworthiness score
