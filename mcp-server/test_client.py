#!/usr/bin/env python3
"""Exercise every MCP tool of the Zizhi Tongjian KG server over Streamable HTTP.

Usage:  python test_client.py [base_url]     (default http://127.0.0.1:8000/mcp)
"""
import asyncio
import json
import sys

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"


def _factory(headers=None, timeout=None, auth=None):
    # trust_env=False: ignore http_proxy/no_proxy env vars. Some environments
    # export no_proxy lists with bracketed IPv6 entries that crash httpx's
    # URLPattern parser before the first request is even sent.
    return httpx.AsyncClient(headers=headers, timeout=timeout, auth=auth,
                             trust_env=False)

CALLS = [
    ("kg_stats", {}),
    ("search_events", {"query": "三家分晋", "limit": 5}),
    ("get_person", {"name": "智伯"}),
    ("get_events_by_year", {"year": -403}),
    ("get_events_by_year", {"year": 626}),
    ("get_timeline", {"from_year": -221, "to_year": -207, "limit": 5}),
    ("get_event", {"event_id": "001-W23-01"}),
]


def shrink(name, payload):
    """Keep evidence readable: truncate long event lists in the printout."""
    p = json.loads(json.dumps(payload, ensure_ascii=False))
    for key in ("results", "events"):
        if isinstance(p.get(key), list) and len(p[key]) > 3:
            p[key] = p[key][:3] + [f"... ({len(p[key])} shown in full result)"]
    return json.dumps(p, ensure_ascii=False, indent=1)


async def main():
    async with streamablehttp_client(URL, httpx_client_factory=_factory) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])
            for name, args in CALLS:
                res = await session.call_tool(name, args)
                payload = res.structuredContent
                if not payload:
                    text = "".join(c.text for c in res.content
                                   if getattr(c, "type", "") == "text")
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        payload = {"raw_text": text}
                print(f"\n=== {name}({json.dumps(args, ensure_ascii=False)}) "
                      f"isError={res.isError} ===")
                print(shrink(name, payload))


if __name__ == "__main__":
    asyncio.run(main())
