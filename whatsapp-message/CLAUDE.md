# Trump Social Feed Monitor -> WhatsApp Notifier

## Architecture

A 24/7 Python service that polls Trump's social media posts, analyzes them with Claude AI, and sends WhatsApp notifications via Twilio.

```
trumpstruth.org (HTML) -> Scraper (Playwright) -> Parser -> State Filter -> Analyzer (Claude: classify+summarize) -> Notifier (Twilio WhatsApp)
         |                      ↑ fallback                                       ↑ taxonomy
         +-- rollcall.com (JSON API) --+                                   taxonomy.py
```

### Poll Cycle Flow
1. **Scraper** fetches posts from trumpstruth.org (HTML parsing, primary) with rollcall.com Factbase API as fallback, using Playwright headless Chromium. Returns a `FetchResult(posts, source)` where source is `"primary"` or `"fallback"`.
2. **Parser** converts raw JSON dicts into `Post` dataclasses, detects platform (Truth Social vs Twitter)
3. **StateManager** filters out already-seen posts using SHA-256 post IDs persisted in `seen_posts.json`
4. **PostAnalyzer** sends new posts to Claude API for combined classification + summarization in one call. Classifies as economic (10 categories with subcategories, market sentiment) or non-economic (9 categories). Returns `Analysis` with `is_economic`, `primary_category`, `subcategory`, `market_sentiment`, `confidence`, plus summary, topics, and relevance score (0.0-1.0). Taxonomy injected from `taxonomy.py`.
5. **Non-economic filter**: If `NOTIFY_NON_ECONOMIC=false`, non-economic posts are logged as skipped and not sent.
6. **WhatsAppNotifier** formats the analysis with category headers (economic: sentiment emoji + `[Category → Subcategory]`, non-economic: `📌 [Category]`) and sends via Twilio if relevance exceeds threshold
7. Loop sleeps `POLL_INTERVAL_SECONDS` (default 420s / 7min) and repeats

## Key Components

| File | Responsibility |
|---|---|
| `taxonomy.py` | Economic (10) and non-economic (9) category definitions, `get_taxonomy_text()` for prompt injection |
| `classify_post.py` | Standalone CLI for single-post classification (`python classify_post.py "text"`) |
| `main.py` | Async polling loop, non-economic filtering, logging setup, graceful shutdown |
| `scraper.py` | Playwright browser management, HTML parsing (trumpstruth.org) + JSON API fallback (rollcall.com) |
| `parser.py` | JSON-to-Post conversion, platform detection, timestamp parsing |
| `analyzer.py` | Claude API integration, combined classify+summarize prompt, JSON response parsing, relevance filtering |
| `notifier.py` | Twilio WhatsApp message formatting (category headers, sentiment emoji) and sending |
| `state.py` | JSON-backed seen-post tracking, 5000 ID cap to prevent unbounded growth |
| `models.py` | `Post` and `Analysis` dataclasses (`Analysis` includes classification fields: `is_economic`, `primary_category`, `subcategory`, `market_sentiment`, `confidence`) |
| `config.py` | `.env` loading via python-dotenv, all configuration in one place |

## Configuration

All config loaded from `.env` (see `.env.example`). Key settings:
- `ANTHROPIC_API_KEY` / `CLAUDE_MODEL` - Claude AI for post analysis
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_FROM` / `WHATSAPP_TO` - Twilio WhatsApp
- `SCRAPE_URL` (default `https://trumpstruth.org/`) - primary source
- `FALLBACK_SCRAPE_URL` (default `https://rollcall.com/factbase/trump/topic/social`) - fallback source
- `POLL_INTERVAL_SECONDS` (default 420) - polling frequency
- `MIN_RELEVANCE_SCORE` (default 0.3) - skip low-relevance posts
- `NOTIFY_NON_ECONOMIC` (default `true`) - set `false` to skip WhatsApp notifications for non-economic posts

## Testing

```bash
python -m pytest tests/ -v
```

60 tests covering all modules including classification. External services (Claude API, Twilio, Playwright) are mocked. Test fixtures in `tests/fixtures/`.

## Running

```bash
cp .env.example .env   # fill in credentials
pip install -r requirements.txt
playwright install chromium
python main.py
```

## Important Details

- **Primary source (trumpstruth.org)**: Server-rendered HTML archive. Posts are in `.status` divs with `.status__content` for text, `.status-info__meta` for timestamps (human-readable like "February 14, 2026, 10:05 AM"), and `.status-header__right a` for links. Uses `domcontentloaded` + 5s wait.
- **Fallback source (rollcall.com)**: Factbase JSON API at `/wp-json/factbase/v1/twitter?sort=date&sort_order=desc&format=json`. Used automatically when the primary source fails. Set `FALLBACK_SCRAPE_URL` to empty to disable fallback.
- **State persistence**: `seen_posts.json` tracks post IDs across restarts. Capped at 5000 entries.
- **Error resilience**: Each poll cycle is wrapped in try/except - failures are logged and the loop continues.
- **WhatsApp sandbox**: Twilio sandbox requires recipients to send a join code to `+14155238886` before receiving messages.

## Monitoring

An independent monitoring dashboard runs as a separate process from the main service.

| File | Responsibility |
|---|---|
| `event_logger.py` | JSONL event writer, appends to `events_log.json`, auto-rotates at 10,000 lines |
| `monitor_server.py` | Stdlib HTTP server on port 8080, serves tabbed HTML dashboard + `/api/events` JSON endpoint + `/api/classify` POST endpoint |

**Events logged:** `service_start`, `service_stop`, `poll_start`, `poll_end`, `notification_sent`, `notification_skipped`, `error`

**Running the dashboard:**
```bash
python monitor_server.py   # open http://localhost:8080
```

The dashboard has two tabs:

- **Dashboard tab**: Service status (Online/Degraded/Down/Stopped), uptime, 24h stats (including fallback count, economic post count, avg confidence), and a scrollable event list. Notification events expand to show classification details (category, subcategory, sentiment, confidence). Poll events from the fallback source are tagged `[FALLBACK]` in the event list, and the success rate chart shows fallback polls as an orange overlay. Auto-refreshes every 30 seconds and works even when the main service is stopped.
- **Classify tab**: Interactive classification debug panel. Paste a post into the textarea, click "Classify", and see the full classification JSON result with a Success/Failure badge. Calls `POST /api/classify` which uses `classify_post.classify()` under the hood. Useful for quick manual testing of the classifier without the CLI.
