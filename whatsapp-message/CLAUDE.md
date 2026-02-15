# Trump Social Feed Monitor -> WhatsApp Notifier

## Architecture

A 24/7 Python service that polls Trump's social media posts, analyzes them with Claude AI, and sends WhatsApp notifications via Twilio.

```
Factbase JSON API -> Scraper (Playwright) -> Parser -> State Filter -> Analyzer (Claude) -> Notifier (Twilio WhatsApp)
```

### Poll Cycle Flow
1. **Scraper** fetches posts from Factbase REST API (`/wp-json/factbase/v1/twitter`) using Playwright headless Chromium
2. **Parser** converts raw JSON dicts into `Post` dataclasses, detects platform (Truth Social vs Twitter)
3. **StateManager** filters out already-seen posts using SHA-256 post IDs persisted in `seen_posts.json`
4. **PostAnalyzer** sends new posts to Claude API for summarization, topic tagging, and relevance scoring (0.0-1.0)
5. **WhatsAppNotifier** formats the analysis and sends via Twilio if relevance exceeds threshold
6. Loop sleeps `POLL_INTERVAL_SECONDS` (default 420s / 7min) and repeats

## Key Components

| File | Responsibility |
|---|---|
| `main.py` | Async polling loop, logging setup, graceful shutdown |
| `scraper.py` | Playwright browser management, Factbase API fetching |
| `parser.py` | JSON-to-Post conversion, platform detection, timestamp parsing |
| `analyzer.py` | Claude API integration, JSON response parsing, relevance filtering |
| `notifier.py` | Twilio WhatsApp message formatting and sending |
| `state.py` | JSON-backed seen-post tracking, 5000 ID cap to prevent unbounded growth |
| `models.py` | `Post` and `Analysis` dataclasses |
| `config.py` | `.env` loading via python-dotenv, all configuration in one place |

## Configuration

All config loaded from `.env` (see `.env.example`). Key settings:
- `ANTHROPIC_API_KEY` / `CLAUDE_MODEL` - Claude AI for post analysis
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_FROM` / `WHATSAPP_TO` - Twilio WhatsApp
- `POLL_INTERVAL_SECONDS` (default 420) - polling frequency
- `MIN_RELEVANCE_SCORE` (default 0.3) - skip low-relevance posts

## Testing

```bash
python -m pytest tests/ -v
```

26 tests covering all modules. External services (Claude API, Twilio, Playwright) are mocked. Test fixtures in `tests/fixtures/`.

## Running

```bash
cp .env.example .env   # fill in credentials
pip install -r requirements.txt
playwright install chromium
python main.py
```

## Important Details

- **API vs HTML scraping**: The site is JS-rendered, but exposes a REST API at `/wp-json/factbase/v1/twitter?sort=date&sort_order=desc&format=json`. We fetch this directly via Playwright rather than parsing rendered HTML.
- **State persistence**: `seen_posts.json` tracks post IDs across restarts. Capped at 5000 entries.
- **Error resilience**: Each poll cycle is wrapped in try/except - failures are logged and the loop continues.
- **WhatsApp sandbox**: Twilio sandbox requires recipients to send a join code to `+14155238886` before receiving messages.

## Monitoring

An independent monitoring dashboard runs as a separate process from the main service.

| File | Responsibility |
|---|---|
| `event_logger.py` | JSONL event writer, appends to `events_log.json`, auto-rotates at 10,000 lines |
| `monitor_server.py` | Stdlib HTTP server on port 8080, serves HTML dashboard + `/api/events` JSON endpoint |

**Events logged:** `service_start`, `service_stop`, `poll_start`, `poll_end`, `notification_sent`, `notification_skipped`, `error`

**Running the dashboard:**
```bash
python monitor_server.py   # open http://localhost:8080
```

The dashboard shows service status (Online/Degraded/Down/Stopped), uptime, 24h stats, and a scrollable event list. It auto-refreshes every 30 seconds and works even when the main service is stopped.
