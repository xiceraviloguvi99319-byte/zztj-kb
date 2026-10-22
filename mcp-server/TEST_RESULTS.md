# Test Results — Zizhi Tongjian KG MCP Server

All tests were run against the real server and the real dataset in this
repository (no mocks, no fixtures). Date: 2026-10-22.

## Environment & commands

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt        # pins mcp>=1.20,<2 (see FEEDBACK.md)
.venv/bin/python server.py                       # Streamable HTTP on :8000/mcp
.venv/bin/python test_client.py                  # official MCP SDK client
```

Server startup line (stderr):

```
[zztj-mcp] loading knowledge graph from <repo root> ...
[zztj-mcp] loaded 27141 events, 26021 persons, year coverage 23420/27141
```

Note: `test_client.py` builds its httpx client with `trust_env=False`. In
sandboxed/CI environments with proxy variables set, httpx otherwise reads
`no_proxy` (which may contain bracketed IPv6 entries) and crashes with
`httpx.InvalidURL: Invalid port: ':1]'` before the first request.

## Verdicts

| # | Call | Result |
|---|------|--------|
| 1 | `kg_stats()` | ✅ 27,141 events, 294 juan, 26,021 persons, 8,557 places, 86.3% dated, span 403 BC – 960 AD |
| 2 | `search_events("三家分晋")` | ✅ 1 match: event `001-W23-01`, the 403 BC legalization of the Partition of Jin — the chronicle's opening event |
| 3 | `get_person("智伯")` | ✅ person-index hit, 3 events (the complete Zhi Bo arc: demanding land, the siege of Jinyang, his destruction), top associates 赵襄子/韩康子/魏桓子 |
| 4 | `get_events_by_year(-403)` | ✅ 13 events, era 威烈王二十三年 |
| 5 | `get_events_by_year(626)` | ✅ 97 events, era 武德九年 (the Xuanwu Gate year) |
| 6 | `get_timeline(-221, -207)` | ✅ 55 events in range, first = unification of China, 221 BC |
| 7 | `get_event("001-W23-01")` | ✅ full record incl. raw annotation with `related_lunzans` cross-reference |
| 8 | extra: `search_events("玄武门")` (simplified query, traditional text) | ✅ 17 matches, top hit `191-武德九年-41` "玄武門之變…" 626 AD |
| 9 | extra: `get_person("赵襄子")` (simplified name) | ✅ matched via script folding, 5 events |
| 10 | stdio transport (`server.py --stdio`, SDK stdio client) | ✅ tools listed, calls served |

## Full output of test_client.py

```
TOOLS: ['search_events', 'get_person', 'get_events_by_year', 'get_timeline', 'get_event', 'kg_stats']

=== kg_stats({}) isError=False ===
{
 "total_events": 27141,
 "volumes_juan": 294,
 "distinct_persons": 26021,
 "distinct_places": 8557,
 "events_with_gregorian_year": 23420,
 "year_coverage_percent": 86.3,
 "year_span": {
  "earliest": "403 BC",
  "latest": "960 AD"
 },
 "top_event_types": [
  [
   "政治",
   11990
  ],
  [
   "軍事",
   5161
  ],
  [
   "军事",
   2295
  ],
  [
   "外交",
   1114
  ],
  [
   "任免",
   726
  ],
  [
   "災異",
   579
  ],
  [
   "人事",
   452
  ],
  [
   "政",
   355
  ],
  [
   "論疏",
   252
  ],
  [
   "去世",
   248
  ],
  [
   "經濟",
   229
  ],
  [
   "灾异",
   190
  ]
 ],
 "year_resolution_method": "Era-year labels in event ids are pinned to Gregorian years by section headers in the annotated chapters (chapter_md) and by explicit year fields in the KG files; remaining years are derived by era arithmetic (era start + reign year - 1), with same-name eras from different dynasties disambiguated by volume year spans. Unresolvable events keep year=null.",
 "data_source": "Zizhi Tongjian (资治通鉴), Wikisource Hu Sansheng annotated edition, all 294 juan; events annotated into a knowledge graph (persons, places, types, cross-references)."
}

=== search_events({"query": "三家分晋", "limit": 5}) isError=False ===
{
 "query": "三家分晋",
 "total_matches": 1,
 "returned": 1,
 "results": [
  {
   "id": "001-W23-01",
   "year": -403,
   "year_display": "403 BC",
   "era": "威烈王二十三年",
   "juan": 1,
   "type": "政治/分封",
   "desc": "周威烈王命晋大夫魏斯、赵籍、韩虔为诸侯（三家分晋合法化）",
   "persons": [
    "魏斯",
    "赵籍",
    "韩虔"
   ],
   "places": []
  }
 ]
}

=== get_person({"name": "智伯"}) isError=False ===
{
 "found": true,
 "name": "智伯",
 "matched_as": "person_index",
 "event_count": 3,
 "first_year": -403,
 "last_year": -403,
 "top_types": [
  [
   "政治/外交",
   1
  ],
  [
   "军事/围攻",
   1
  ],
  [
   "军事/政变",
   1
  ]
 ],
 "top_places": [
  [
   "蔺",
   1
  ],
  [
   "皋狼",
   1
  ],
  [
   "晋阳",
   1
  ]
 ],
 "top_associates": [
  [
   "赵襄子",
   3
  ],
  [
   "韩康子",
   2
  ],
  [
   "魏桓子",
   2
  ],
  [
   "段规",
   1
  ],
  [
   "任章",
   1
  ],
  [
   "张孟谈",
   1
  ]
 ],
 "events": [
  {
   "id": "001-W23-04",
   "year": -403,
   "year_display": "403 BC",
   "era": "威烈王二十三年",
   "juan": 1,
   "type": "政治/外交",
   "desc": "智伯向韩康子、魏桓子索地（各得万家之邑），向赵襄子索蔺、皋狼之地被拒",
   "persons": [
    "智伯",
    "韩康子",
    "魏桓子",
    "赵襄子",
    "段规",
    "任章"
   ],
   "places": [
    "蔺",
    "皋狼"
   ]
  },
  {
   "id": "001-W23-05",
   "year": -403,
   "year_display": "403 BC",
   "era": "威烈王二十三年",
   "juan": 1,
   "type": "军事/围攻",
   "desc": "智伯帅韩魏之甲攻赵，赵襄子走晋阳；三家围而灌之，城不浸者三版",
   "persons": [
    "智伯",
    "赵襄子"
   ],
   "places": [
    "晋阳"
   ]
  },
  {
   "id": "001-W23-06",
   "year": -403,
   "year_display": "403 BC",
   "era": "威烈王二十三年",
   "juan": 1,
   "type": "军事/政变",
   "desc": "韩魏倒戈：张孟谈密约韩魏，决水灌智伯军，杀智伯、尽灭智氏之族（唯辅果在）",
   "persons": [
    "张孟谈",
    "韩康子",
    "魏桓子",
    "赵襄子",
    "智伯"
   ],
   "places": []
  }
 ],
 "events_truncated": false
}

=== get_events_by_year({"year": -403}) isError=False ===
{
 "year": -403,
 "year_display": "403 BC",
 "count": 13,
 "eras": [
  "威烈王二十三年"
 ],
 "events": [
  {
   "id": "001-W23-01",
   "year": -403,
   "year_display": "403 BC",
   "era": "威烈王二十三年",
   "juan": 1,
   "type": "政治/分封",
   "desc": "周威烈王命晋大夫魏斯、赵籍、韩虔为诸侯（三家分晋合法化）",
   "persons": [
    "魏斯",
    "赵籍",
    "韩虔"
   ],
   "places": []
  },
  {
   "id": "001-W23-02",
   "year": -403,
   "year_display": "403 BC",
   "era": "威烈王二十三年",
   "juan": 1,
   "type": "政治/继承",
   "desc": "智宣子欲立瑶为后，智果以'才胜德'谏，不听；智果别族为辅氏",
   "persons": [
    "智宣子",
    "智瑶",
    "智果",
    "智宵"
   ],
   "places": []
  },
  {
   "id": "001-W23-03",
   "year": -403,
   "year_display": "403 BC",
   "era": "威烈王二十三年",
   "juan": 1,
   "type": "政治/继承",
   "desc": "赵简子择后：伯鲁失简、无恤守简，立无恤（赵襄子）；使尹铎治晋阳、宽民",
   "persons": [
    "赵简子",
    "赵伯鲁",
    "赵无恤",
    "尹铎"
   ],
   "places": [
    "晋阳"
   ]
  },
  "... (13 shown in full result)"
 ]
}

=== get_events_by_year({"year": 626}) isError=False ===
{
 "year": 626,
 "year_display": "626 AD",
 "count": 97,
 "eras": [
  "武德九年"
 ],
 "events": [
  {
   "id": "191-武德九年-01",
   "year": 626,
   "year_display": "626 AD",
   "era": "武德九年",
   "juan": 191,
   "type": "政治",
   "desc": "詔太常少卿祖孝孫等更定雅樂",
   "persons": [
    "祖孝孫"
   ],
   "places": []
  },
  {
   "id": "191-武德九年-02",
   "year": 626,
   "year_display": "626 AD",
   "era": "武德九年",
   "juan": 191,
   "type": "政治",
   "desc": "以左僕射裴寂為司空",
   "persons": [
    "裴寂"
   ],
   "places": []
  },
  {
   "id": "191-武德九年-03",
   "year": 626,
   "year_display": "626 AD",
   "era": "武德九年",
   "juan": 191,
   "type": "政治",
   "desc": "以齊王元吉為司徒",
   "persons": [
    "李元吉"
   ],
   "places": []
  },
  "... (97 shown in full result)"
 ]
}

=== get_timeline({"from_year": -221, "to_year": -207, "limit": 5}) isError=False ===
{
 "from_year": -221,
 "to_year": -207,
 "total_in_range": 55,
 "returned": 5,
 "truncated": true,
 "events": [
  {
   "id": "007-始皇帝二十六年-01",
   "year": -221,
   "year_display": "221 BC",
   "era": "始皇帝二十六年",
   "juan": 7,
   "type": "軍事/滅國",
   "desc": "王賁入臨淄，齊王建降，遷共餓死，齊亡，六國盡滅",
   "persons": [
    "王賁",
    "齊王建"
   ],
   "places": [
    "臨淄",
    "共"
   ]
  },
  {
   "id": "007-始皇帝二十六年-02",
   "year": -221,
   "year_display": "221 BC",
   "era": "始皇帝二十六年",
   "juan": 7,
   "type": "政治/制度",
   "desc": "始皇帝定稱號：皇帝、制、詔、朕；追尊莊襄王為太上皇；除謚法",
   "persons": [
    "秦始皇",
    "莊襄王"
   ],
   "places": []
  },
  {
   "id": "007-始皇帝二十六年-03",
   "year": -221,
   "year_display": "221 BC",
   "era": "始皇帝二十六年",
   "juan": 7,
   "type": "政治/制度",
   "desc": "用鄒衍五德說，以秦為水德，尚黑，以十月為歲首",
   "persons": [
    "鄒衍"
   ],
   "places": []
  },
  "... (5 shown in full result)"
 ]
}

=== get_event({"event_id": "001-W23-01"}) isError=False ===
{
 "id": "001-W23-01",
 "year": -403,
 "year_display": "403 BC",
 "era": "威烈王二十三年",
 "juan": 1,
 "type": "政治/分封",
 "desc": "周威烈王命晋大夫魏斯、赵籍、韩虔为诸侯（三家分晋合法化）",
 "persons": [
  "魏斯",
  "赵籍",
  "韩虔"
 ],
 "places": [],
 "raw": {
  "desc": "周威烈王命晋大夫魏斯、赵籍、韩虔为诸侯（三家分晋合法化）",
  "id": "001-W23-01",
  "related_lunzans": [
   "臣光论礼：名分之坏"
  ],
  "type": "政治/分封",
  "人物": [
   "魏斯",
   "赵籍",
   "韩虔"
  ]
 },
 "found": true
}

```
