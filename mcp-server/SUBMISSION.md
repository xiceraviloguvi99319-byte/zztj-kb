# Devpost Submission — DRAFT

**Hackathon:** Build, Ship, Shape: Amazon Developer Hackathon
**Track:** Alexa+ (self-hosted MCP server) · also eligible: Open Source mini challenge

---

## Project title (suggestion)

**Zizhi Tongjian MCP — Ask 1,300 Years of Chinese History**

## Tagline

An MCP server that turns the *Zizhi Tongjian* — China's great 1,362-year
chronicle (403 BC–959 AD) — into a queryable knowledge graph of 27,141
events, so Alexa+ and any AI assistant can answer history questions from
structured data instead of hallucinating them.

## Description

### The problem

Ask a voice assistant about Chinese history before the modern era and you
get fluent, confident, and frequently wrong answers. The primary sources
exist — above all the *Zizhi Tongjian* (《资治通鉴》), Sima Guang's
294-volume chronicle of 403 BC–959 AD — but they are written in classical
Chinese, organized by reign eras rather than Gregorian years, and locked in
book form. There is no structured, machine-queryable interface to them.

### What it does

This project exposes a complete event-level knowledge graph of the
*Zizhi Tongjian* as a **self-hosted MCP server** (spec 2025-11-25,
Streamable HTTP, plus stdio for local hosts). Any MCP-compatible assistant
can call six tools:

- `search_events` — full-text search across 27,141 event summaries, persons,
  places and event types (traditional/simplified script folding included);
- `get_person` — a person's recorded life in the chronicle: event count,
  active years, closest associates, chronological event list;
- `get_events_by_year` — everything the chronicle records for one year,
  addressed by Gregorian year (`-403` … `959`);
- `get_timeline` — chronological slices, e.g. the fall of Qin (221–207 BC);
- `get_event` — the full annotation record of one event, including
  cross-references to Sima Guang's own editorial essays;
- `kg_stats` — live dataset statistics.

Example answers it powers: the Partition of Jin in 403 BC (the book's
opening event), Zhi Bo's complete three-event arc and the coalition that
destroyed him, the 97 recorded events of 626 AD, the year of the Xuanwu
Gate coup.

### How it works

- **The data** (pre-existing, open): all 294 juan of the Wikisource
  Hu Sansheng annotated edition, annotated into a knowledge graph —
  27,141 events, 26,021 distinct persons, 8,557 places.
- **The hard part — dates.** The source labels events by Chinese era-year
  （始皇帝二十三年， 武德九年）, not Gregorian years. The server rebuilds a
  Gregorian timeline at startup: era-year labels are pinned from the
  annotated chapters' section headers (including Chinese-numeral years like
  公元六二六年）, remaining years are derived by era arithmetic, and era
  names reused by rival dynasties are disambiguated against volume year
  spans. Result: 86.3% of events carry an exact Gregorian year; the rest
  stay honestly undated (`year: null`).
- **The server**: a single-file Python app on the official MCP SDK
  (FastMCP), in-memory indexes, stateless Streamable HTTP at `/mcp`,
  read-only — public-domain data, no account linking needed.

### What's novel

- To our knowledge the **first MCP interface to a complete classical
  Chinese chronicle**: not a RAG demo over excerpts, but the whole work —
  every volume, every event — as structured tools an agent can compose.
- The **era-year → Gregorian resolution pipeline**, which turns a
  reign-era-labelled corpus into a timeline any modern system can query.
- It treats an LLM's weakest spot (pre-modern non-Western history) with the
  strongest medicine: deterministic lookups over curated data, no model
  inside the tools.

### What was built for this hackathon

The knowledge graph itself is our earlier open-source work. **The MCP
server layer — `mcp-server/` in this repo: the server, the Gregorian-year
resolution pipeline, the script-folding search, the test client and this
documentation — was designed and built for this hackathon** to bring the
graph to Alexa+ and the MCP ecosystem.

## Built with

- Python 3.12
- Model Context Protocol (spec 2025-11-25), official Python SDK (`mcp` v1, FastMCP)
- Streamable HTTP transport (+ stdio)
- Data: *Zizhi Tongjian*, Wikisource Hu Sansheng annotated edition (public domain text)
- No paid services; runs anywhere Python runs

## Try it

```bash
cd mcp-server && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python server.py            # http://localhost:8000/mcp
.venv/bin/python test_client.py       # exercises all six tools
```

See `mcp-server/README.md` and `mcp-server/TEST_RESULTS.md` for details and
captured test evidence.
