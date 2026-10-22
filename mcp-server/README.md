# Zizhi Tongjian Knowledge Graph — MCP Server

A self-hosted **MCP server** that lets any AI assistant (Alexa+, or any other
MCP host) answer questions about **1,362 years of Chinese history** from a
structured knowledge graph of the *Zizhi Tongjian* (《资治通鉴》,
"Comprehensive Mirror in Aid of Governance") — the great chronicle compiled
by Sima Guang in 1084, covering **403 BC – 959 AD**.

The graph holds **27,141 annotated events** from all **294 juan (volumes)** of
the chronicle, each with a summary, event type, participating persons and
places, and cross-references. Ask things like:

- *"What happened in 403 BC?"* → the Partition of Jin, the chronicle's opening event
- *"Who was Zhi Bo (智伯）?"* → his 3 recorded events and closest associates
- *"Show me the fall of Qin, 221–207 BC"* → a 55-event chronological timeline
- *"玄武门" (Xuanwu Gate)* → the 626 AD coup, found across script variants

## Quickstart

Requirements: Python 3.10+, and this repository's data (the server reads
`../kg/` and `../chapter_md/` relative to this directory; override with
`ZZTJ_DATA_DIR`).

```bash
cd mcp-server
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Streamable HTTP (primary) — serves on http://0.0.0.0:8000/mcp
.venv/bin/python server.py
# …or: PORT=9000 .venv/bin/python server.py

# stdio (for local MCP hosts)
.venv/bin/python server.py --stdio
```

Point any MCP client at it, e.g.:

```json
{
  "mcpServers": {
    "zizhi-tongjian": { "url": "http://localhost:8000/mcp" },
    "zizhi-tongjian-local": {
      "command": "python3",
      "args": ["/path/to/repo/mcp-server/server.py", "--stdio"]
    }
  }
}
```

The server implements MCP spec 2025-11-25 over Streamable HTTP (stateless,
JSON responses) using the official Python SDK (`mcp` v1 — see
`requirements.txt` for why the major version is pinned). It is **read-only**
and serves public-domain historical data, so no account linking / auth is
required for this build.

## Tools

| Tool | Description |
|------|-------------|
| `search_events(query, limit=10)` | Full-text search over event summaries, persons, places, types and era labels. Multiple terms are ANDed; traditional/simplified scripts are folded so either matches. Ranked, then chronological. |
| `get_person(name)` | Person profile: event count, active years, top event types/places, most frequent co-occurring persons, chronological event list (cap 100). Falls back to narrative mentions, then to script-variant matching. |
| `get_events_by_year(year)` | All events of one Gregorian year. **Negative = BC** (`-403`), positive = AD (`626`). Suggests nearest dated years when empty. |
| `get_timeline(from_year, to_year, limit=100)` | Chronological slice between two years (inclusive), total count always reported, cap 300. |
| `get_event(event_id)` | Full record for one event id (e.g. `001-W23-01`), including the raw annotation (cross-references such as `concurrent_with`, `related_lunzans`). |
| `kg_stats()` | Live dataset statistics: totals, distinct persons/places, dated-year coverage and span, top event types. |

## Testing (for judges)

```bash
.venv/bin/python server.py &        # wait for "loaded 27141 events"
.venv/bin/python test_client.py     # exercises every tool via the MCP SDK
```

Expected headline results (full captured output in `TEST_RESULTS.md`):
27,141 events · 294 juan · 26,021 persons · 86.3% of events carry a resolved
Gregorian year · search `三家分晋` returns the 403 BC Partition of Jin ·
`get_events_by_year(626)` returns 97 events of the Xuanwu Gate year.

## How the years work (the interesting part)

The source annotation identifies events by **Chinese era-year labels**
（始皇帝二十三年， 武德九年…) rather than Gregorian years. At startup the
server reconstructs a Gregorian year for each event:

1. explicit years attached to events / year-sections in the KG files;
2. era-year labels pinned by section headers in the annotated chapters
   (〖*武德九年〗（〖%丙申〗，公元六二六年）), incl. Chinese-numeral years;
3. era arithmetic (era start + reign year − 1) from any pinned year of the
   same era — same-name eras reused by different dynasties are disambiguated
   using the volume's year span and neighbouring pinned events;
4. a few letter-coded labels in juan 1/6 (`W23`, `Z52`, `ZX1`, `XW1`) are
   decoded to their era names first.

23,420 / 27,141 events (86.3%) resolve; the rest keep `year: null` — still
searchable, excluded from year/timeline queries.

## Data source

*Zizhi Tongjian*, Wikisource edition with Hu Sansheng's commentary
（維基文庫胡三省音注校刊本）, all 294 juan, annotated into a knowledge graph
in this repository (`kg/events/`, ~27k events). Event text mixes traditional
and simplified characters exactly as annotated; search folds the two scripts.

## Files

- `server.py` — the MCP server (data loading + 6 tools, ~single file)
- `test_client.py` — SDK-based test client exercising every tool
- `TEST_RESULTS.md` — captured test evidence
- `SUBMISSION.md` — hackathon submission copy (draft)
- `FEEDBACK.md` — product feedback draft for the Alexa+/MCP tooling form
