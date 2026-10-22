#!/usr/bin/env python3
"""
Zizhi Tongjian Knowledge Graph — MCP Server
=============================================
A self-hosted MCP server (spec 2025-11-25, Streamable HTTP + stdio) that exposes
a structured knowledge graph built from the *Zizhi Tongjian* (《资治通鉴》,
"Comprehensive Mirror in Aid of Governance", Sima Guang, 1084 AD).

The underlying open dataset contains ~27k events annotated from all 294 juan
(volumes) of the Wikisource Hu Sansheng annotated edition, covering 403 BC –
959 AD. This MCP layer was built for the Amazon "Build, Ship, Shape" hackathon
(Alexa+ track: self-hosted MCP server).

Data layout expected (relative to the repository root, i.e. the parent of
this file's directory; override with env ZZTJ_DATA_DIR):
    kg/events/*.json            event files (flat or year-sectioned)
    kg/events/parts146/*.json   split files for juan 146
    chapter_md/*_annotated*.md  annotated chapters whose section headers pin
                                era-year labels to Gregorian years

Year model: integers, negative = BC (e.g. -403 = 403 BC), positive = AD.
There is no year 0 in the source chronology; the data jumps from -1 to 1.

How an event gets its Gregorian year (first match wins):
  1. Explicit year attached to the event or its year-section in the KG files.
  2. Era-year label parsed from the event id (e.g. "007-始皇帝二十三年-01")
     looked up in a pin table built from chapter_md section headers
     (〖*始皇帝二十三年〗（〖%丁丑〗，前224）).
  3. Era arithmetic: an era's start year derived from any pinned year of the
     same era, plus (reign_year - 1). If an era name was reused by several
     dynasties, candidates are disambiguated against the volume's year span
     (from the chapter title) or neighbouring pinned events in the same file.
  4. A handful of letter-coded era segments in juan 1/6 (W23, Z52, ZX1, XW1)
     are decoded to their Chinese era labels first.
Events whose year cannot be resolved keep year=None: they remain searchable
but are excluded from year/timeline queries. Coverage is reported by
kg_stats().
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# --------------------------------------------------------------------------
# Chinese numeral helpers
# --------------------------------------------------------------------------

_DIG = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_DIGITS = "零一二三四五六七八九"


def cn_num(s: str):
    """Parse an Arabic or Chinese numeral (digit-wise 五二四 or composite 二十三)."""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if all(c in _DIG for c in s):  # digit-wise, e.g. 五二四 = 524
        return int("".join(str(_DIG[c]) for c in s))
    if "百" in s or "十" in s:
        tot, cur = 0, 0
        for c in s:
            if c in _DIG:
                cur = _DIG[c]
            elif c == "十":
                tot += (cur if cur else 1) * 10
                cur = 0
            elif c == "百":
                tot += (cur if cur else 1) * 100
                cur = 0
            else:
                return None
        return tot + cur
    if len(s) == 1 and s in _DIG:
        return _DIG[s]
    return None


def int2cn(n: int) -> str:
    """Small int -> Chinese numeral (for decoding letter-coded era segments)."""
    if n <= 10:
        return "十" if n == 10 else _CN_DIGITS[n]
    if n < 20:
        return "十" + _CN_DIGITS[n - 10]
    t, o = divmod(n, 10)
    return _CN_DIGITS[t] + "十" + (_CN_DIGITS[o] if o else "")


# --------------------------------------------------------------------------
# Era-label parsing
# --------------------------------------------------------------------------

_SEG_RE = re.compile(r"^(.+?)(元|[一二三四五六七八九十]+|\d+)年$")
_ID_RE = re.compile(r"^(\d+)-(.+?)-(\d+[a-z]?|論贊|论赞)$")
_CODE_RE = re.compile(r"^(W|Z|ZX|XW)(\d+)$")
_CODE_ERA = {"W": "威烈王", "Z": "昭襄王", "ZX": "莊襄王", "XW": "孝文王"}


def split_seg(seg: str):
    """'始皇帝二十三年' -> ('始皇帝', 23); '高帝元年' -> ('高帝', 1)."""
    m = _SEG_RE.match(seg)
    if not m:
        return None
    n = 1 if m.group(2) == "元" else cn_num(m.group(2))
    if n is None:
        return None
    return m.group(1), n


def decode_seg(seg: str) -> str:
    """Decode letter-coded segments (W23 -> 威烈王二十三年); pass others through."""
    m = _CODE_RE.match(seg)
    if m:
        return _CODE_ERA[m.group(1)] + int2cn(int(m.group(2))) + "年"
    return seg


def seg_of(event_id: str):
    m = _ID_RE.match(event_id or "")
    if not m:
        return None
    return decode_seg(m.group(2).lstrip("*").strip())


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

_YEAR_TOK = r"[〇零一二三四五六七八九十百\d]+"
# 〖*普通五年〗（〖%甲辰〗，公元五二四年）  /  〖*顯王元年〗（癸丑，前368）
_PIN_RE_A = re.compile(
    r"〖\*?([^\]〗（）]+?)〗（[^）]*?，(前|公元)(" + _YEAR_TOK + r")年?）")
# ## 天監四年（乙酉，公元五零五年）
_PIN_RE_B = re.compile(
    r"^##\s*(〖\*?)?([^\s（）〖〗]+?(?:元年|[一二三四五六七八九十\d]+年))(?(1)〗)"
    r"（[^）]*?，(前|公元)(" + _YEAR_TOK + r")年?）", re.M)
# juan title spans: 前368–前321 / 524–525 / 前8–公元15
_SPAN_RE = re.compile(
    r"(前|公元)?(" + _YEAR_TOK + r")\s*[–—~]\s*(前|公元)?(" + _YEAR_TOK + r")")
_VOL_RE = re.compile(r"卷\s*0*(\d+)")


def _to_year(sign, tok):
    n = cn_num(tok)
    if n is None:
        return None
    return -n if sign == "前" else n


class KG:
    def __init__(self, root: Path):
        self.root = root
        self.events: list[dict] = []
        self.by_id: dict[str, dict] = {}
        self.by_year: dict[int, list[dict]] = defaultdict(list)
        self.by_person: dict[str, list[dict]] = defaultdict(list)
        self.by_person_folded: dict[str, list[str]] = defaultdict(list)
        self.juan_spans: dict[int, tuple[int, int]] = {}
        self.seg_pins: dict[str, int] = {}
        self.era_bases: dict[str, set[int]] = defaultdict(set)
        self.year_coverage = 0
        self._load()

    # -- pin table from annotated chapters -------------------------------
    def _load_pins(self):
        files = glob.glob(str(self.root / "chapter_md" / "*.md")) + \
            glob.glob(str(self.root / "chapter_md" / "parts146" / "*.md"))
        for fp in files:
            try:
                txt = Path(fp).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in _PIN_RE_A.finditer(txt):
                y = _to_year(m.group(2), m.group(3))
                if y is not None and m.group(1).strip():
                    self.seg_pins.setdefault(m.group(1).strip(), y)
            for m in _PIN_RE_B.finditer(txt):
                y = _to_year(m.group(3), m.group(4))
                if y is not None and m.group(2).strip():
                    self.seg_pins.setdefault(m.group(2).strip(), y)
            # juan span from the title (first) line
            head = txt[:400]
            vm = re.search(r"#\s*卷\s*0*(\d+)", head)
            if vm:
                jn = int(vm.group(1))
                sm = _SPAN_RE.search(head)
                if sm and jn not in self.juan_spans:
                    a = _to_year(sm.group(1), sm.group(2))
                    b = _to_year(sm.group(3), sm.group(4))
                    if a is not None and b is not None:
                        if sm.group(1) == "前" and sm.group(3) is None and b > 0:
                            b = -b  # 前368–321 style
                        self.juan_spans[jn] = (min(a, b), max(a, b))

    # -- event files -------------------------------------------------------
    def _iter_raw(self):
        """Yield (juan:int, raw_event:dict, section_year:int|None, file_meta:dict)."""
        kg = self.root / "kg" / "events"
        files = sorted(glob.glob(str(kg / "*.json"))) + \
            sorted(glob.glob(str(kg / "parts146" / "*.json")))
        for fp in files:
            try:
                d = json.loads(Path(fp).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            jn = None
            vm = _VOL_RE.search(str(d.get("volume", "")))
            if vm:
                jn = int(vm.group(1))
            for e in d.get("events", []):
                yield jn, e, None, d
            for key in ("years", "year_sections"):
                secs = d.get(key)
                if isinstance(secs, list):
                    for s in secs:
                        sy = s.get("year_bce") if isinstance(s, dict) else None
                        for e in (s or {}).get("events", []):
                            yield jn, e, sy, d

    def _collect_exact_pins(self, raw_rows):
        for jn, e, sec_year, meta in raw_rows:
            seg = seg_of(e.get("id", ""))
            if not seg:
                continue
            if sec_year is not None:
                self.seg_pins.setdefault(seg, sec_year)
            if isinstance(e.get("year_bce"), int):
                self.seg_pins.setdefault(seg, e["year_bce"])
        # single-year flat files (e.g. juan 1): file year_bce + all events share a seg
        by_file: dict[int, list] = defaultdict(list)
        for jn, e, sec_year, meta in raw_rows:
            if sec_year is None:
                by_file[id(meta)].append((jn, e, meta))
        for rows in by_file.values():
            meta = rows[0][2]
            fy = meta.get("year_bce")
            if isinstance(fy, int):
                segs = {seg_of(e.get("id", "")) for _, e, _ in rows}
                segs.discard(None)
                if len(segs) == 1:
                    self.seg_pins.setdefault(segs.pop(), fy)

    def _build_era_bases(self):
        for seg, y in self.seg_pins.items():
            sp = split_seg(seg)
            if sp:
                self.era_bases[sp[0]].add(y - (sp[1] - 1))

    def _resolve_year(self, seg, juan, file_lo, file_hi):
        """Return Gregorian year for an era segment, or None."""
        if seg is None:
            return None
        if seg in self.seg_pins:
            return self.seg_pins[seg]
        sp = split_seg(seg)
        if not sp:
            return None
        name, n = sp
        cands = self.era_bases.get(name)
        if not cands:
            return None
        years = {b + (n - 1) for b in cands}
        if len(years) == 1:
            return years.pop()
        # era name reused by several dynasties: use the volume's span
        span = self.juan_spans.get(juan)
        windows = []
        if span:
            windows.append((span[0] - 2, span[1] + 2))
        if file_lo is not None:
            windows.append((file_lo - 3, file_hi + 3))
        for lo, hi in windows:
            inside = [y for y in years if lo <= y <= hi]
            if len(inside) == 1:
                return inside[0]
        return None

    def _load(self):
        self._load_pins()
        raw_rows = list(self._iter_raw())
        self._collect_exact_pins(raw_rows)
        self._build_era_bases()

        # per-file pinned-year window (for disambiguation fallback)
        file_window: dict[int, tuple[int, int]] = {}
        tmp: dict[int, list[int]] = defaultdict(list)
        for jn, e, sec_year, meta in raw_rows:
            seg = seg_of(e.get("id", ""))
            y = sec_year if sec_year is not None else self.seg_pins.get(seg or "")
            if y is not None:
                tmp[id(meta)].append(y)
        for k, ys in tmp.items():
            file_window[k] = (min(ys), max(ys))

        for jn, e, sec_year, meta in raw_rows:
            eid = e.get("id")
            if not eid or eid in self.by_id:
                continue  # dedupe (juan 146 exists whole + split)
            seg = seg_of(eid)
            if jn is None:
                m = re.match(r"^(\d+)-", eid)
                jn = int(m.group(1)) if m else 0
            lo = hi = None
            if id(meta) in file_window:
                lo, hi = file_window[id(meta)]
            year = sec_year if sec_year is not None else \
                self._resolve_year(seg, jn, lo, hi)
            persons = [p for p in (e.get("人物") or []) if p]
            places = [p for p in (e.get("地点") or e.get("地點") or []) if p]
            rec = {
                "id": eid,
                "juan": jn,
                "era": seg,
                "year": year,
                "type": e.get("type", ""),
                "desc": e.get("desc", ""),
                "persons": persons,
                "places": places,
                "raw": e,
            }
            self.events.append(rec)
            self.by_id[eid] = rec
            if year is not None:
                self.by_year[year].append(rec)
                self.year_coverage += 1
            for p in persons:
                self.by_person[p].append(rec)
        # chronological order: (year is None last), then book order
        order = {id(r): i for i, r in enumerate(self.events)}
        for p in self.by_person:
            fp = fold(p)
            if p not in self.by_person_folded[fp]:
                self.by_person_folded[fp].append(p)
        self.events.sort(key=lambda r: (r["year"] is None, r["year"] or 0,
                                        order[id(r)]))
        for ys in self.by_year.values():
            ys.sort(key=lambda r: order[id(r)])

    # -- formatting ---------------------------------------------------------
    @staticmethod
    def year_display(y):
        if y is None:
            return None
        return f"{-y} BC" if y < 0 else f"{y} AD"

    def public(self, rec, full=False):
        out = {
            "id": rec["id"],
            "year": rec["year"],
            "year_display": self.year_display(rec["year"]),
            "era": rec["era"],
            "juan": rec["juan"],
            "type": rec["type"],
            "desc": rec["desc"],
            "persons": rec["persons"],
            "places": rec["places"],
        }
        if full:
            out["raw"] = rec["raw"]
        return out


# --------------------------------------------------------------------------
# Traditional -> simplified folding for search
# (the corpus mixes scripts: some volumes are annotated in traditional
# characters, others in simplified; queries may use either)
# --------------------------------------------------------------------------

_T2S = {
    "門": "门", "變": "变", "殺": "杀", "將": "将", "軍": "军", "圍": "围",
    "國": "国", "晉": "晋", "趙": "赵", "韓": "韩", "齊": "齐", "魯": "鲁",
    "衛": "卫", "鄭": "郑", "吳": "吴", "陳": "陈", "鄧": "邓", "馮": "冯",
    "呂": "吕", "孫": "孙", "嚴": "严", "華": "华", "蕭": "萧", "謝": "谢",
    "鄒": "邹", "費": "费", "賀": "贺", "湯": "汤", "漢": "汉", "劉": "刘",
    "張": "张", "楊": "杨", "黃": "黄", "廣": "广", "陽": "阳", "陰": "阴",
    "遼": "辽", "長": "长", "樂": "乐", "開": "开", "關": "关", "隊": "队",
    "隨": "随", "險": "险", "隱": "隐", "難": "难", "雙": "双", "離": "离",
    "雜": "杂", "雲": "云", "靈": "灵", "靜": "静", "順": "顺", "領": "领",
    "頭": "头", "顯": "显", "風": "风", "飛": "飞", "馬": "马", "騎": "骑",
    "鬥": "斗", "魚": "鱼", "鮮": "鲜", "鳥": "鸟", "黨": "党", "聽": "听",
    "聲": "声", "職": "职", "舉": "举", "興": "兴", "舊": "旧", "節": "节",
    "莊": "庄", "獲": "获", "萬": "万", "藍": "蓝", "蘭": "兰", "處": "处",
    "虛": "虚", "虜": "虏", "號": "号", "見": "见", "規": "规", "視": "视",
    "覺": "觉", "覽": "览", "觀": "观", "議": "议", "譯": "译", "讀": "读",
    "讓": "让", "貝": "贝", "貞": "贞", "負": "负", "貢": "贡", "貧": "贫",
    "貨": "货", "販": "贩", "貪": "贪", "貫": "贯", "責": "责", "貴": "贵",
    "買": "买", "貸": "贷", "貿": "贸", "賈": "贾", "賊": "贼", "資": "资",
    "賜": "赐", "賞": "赏", "賠": "赔", "賢": "贤", "賣": "卖", "賤": "贱",
    "賦": "赋", "質": "质", "賬": "账", "賴": "赖", "贈": "赠", "贊": "赞",
    "贖": "赎", "屬": "属", "層": "层", "屆": "届", "歲": "岁", "爾": "尔",
    "專": "专", "東": "东", "車": "车", "農": "农", "齒": "齿", "齡": "龄",
    "鳳": "凤", "龍": "龙", "龜": "龟", "於": "于", "與": "与", "為": "为",
    "這": "这", "麼": "么", "們": "们", "個": "个", "來": "来", "時": "时",
    "還": "还", "過": "过", "進": "进", "遠": "远", "運": "运", "邊": "边",
    "達": "达", "遷": "迁", "選": "选", "遺": "遗", "鄉": "乡", "聞": "闻",
    "間": "间", "閣": "阁", "閱": "阅", "際": "际", "雞": "鸡", "電": "电",
    "頂": "顶", "須": "须", "頒": "颁", "預": "预", "頰": "颊", "頸": "颈",
    "頻": "频", "顆": "颗", "題": "题", "額": "额", "顏": "颜", "願": "愿",
    "類": "类", "顧": "顾", "飯": "饭", "飲": "饮", "餓": "饿", "館": "馆",
    "騙": "骗", "騷": "骚", "驅": "驱", "驛": "驿", "驚": "惊", "鬧": "闹",
    "鬱": "郁", "鴻": "鸿", "鵬": "鹏", "鶴": "鹤", "鷹": "鹰", "鹹": "咸",
    "麗": "丽", "麥": "麦", "黍": "黍", "龔": "龚", "聯": "联", "聰": "聪",
    "肅": "肃", "脅": "胁", "脈": "脉", "脹": "胀", "腦": "脑", "臉": "脸",
    "臘": "腊", "臨": "临", "艷": "艳", "藝": "艺", "芻": "刍", "萊": "莱",
    "著": "著", "蒼": "苍", "蓑": "蓑", "蔔": "卜", "藏": "藏", "藩": "藩",
    "蘄": "蕲", "蘆": "芦", "蘇": "苏", "蘋": "苹", "蝦": "虾", "蟄": "蛰",
    "蠟": "蜡", "蠱": "蛊", "蠻": "蛮", "術": "术", "衝": "冲", "製": "制",
    "複": "复", "襲": "袭", "覓": "觅", "覲": "觐", "覿": "觌", "觴": "觞",
    "觸": "触", "訂": "订", "訃": "讣", "計": "计", "訊": "讯", "討": "讨",
    "訓": "训", "託": "托", "記": "记", "訛": "讹", "訟": "讼", "訣": "诀",
    "訪": "访", "設": "设", "許": "许", "訴": "诉", "診": "诊", "詐": "诈",
    "詔": "诏", "評": "评", "詞": "词", "詠": "咏", "詢": "询", "詣": "诣",
    "試": "试", "詩": "诗", "詭": "诡", "詮": "诠", "詰": "诘", "話": "话",
    "該": "该", "詳": "详", "誅": "诛", "誇": "夸", "認": "认", "誕": "诞",
    "誘": "诱", "語": "语", "誠": "诚", "誡": "诫", "誣": "诬", "誤": "误",
    "誦": "诵", "說": "说", "誰": "谁", "課": "课", "調": "调", "談": "谈",
    "請": "请", "諍": "诤", "諒": "谅", "論": "论", "諜": "谍", "諦": "谛",
    "諧": "谐", "諫": "谏", "諭": "谕", "諮": "谘", "諱": "讳", "諳": "谙",
    "諷": "讽", "諸": "诸", "諺": "谚", "諾": "诺", "謀": "谋", "謁": "谒",
    "謂": "谓", "謊": "谎", "謐": "谧", "謔": "谑", "謗": "谤", "謙": "谦",
    "講": "讲", "謠": "谣", "謨": "谟", "謫": "谪", "謬": "谬", "謹": "谨",
    "證": "证", "識": "识", "譚": "谭", "譏": "讥", "譜": "谱", "譭": "毁",
    "貓": "猫", "豬": "猪", "貍": "狸", "屍": "尸", "屢": "屡", "岷": "岷",
    "嶧": "峄", "嶗": "崂", "嶠": "峤", "嶧": "峄", "嶸": "嵘", "嶺": "岭",
    "嶽": "岳", "巋": "岿", "巒": "峦", "巔": "巅", "巖": "岩", "巖": "岩",
    "巔": "巅", "巖": "岩", "嶮": "崄", "嶮": "崄", "嶮": "崄", "嶲": "巂",
    "巂": "巂", "嶴": "岙", "嶴": "岙", "嶸": "嵘", "嶸": "嵘", "嶺": "岭",
}


def fold(s: str) -> str:
    """Fold traditional characters to simplified for search matching."""
    if not s:
        return s
    return "".join(_T2S.get(c, c) for c in s)


def data_root() -> Path:
    env = os.environ.get("ZZTJ_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


print(f"[zztj-mcp] loading knowledge graph from {data_root()} ...",
      file=sys.stderr)
KGDB = KG(data_root())
print(f"[zztj-mcp] loaded {len(KGDB.events)} events, "
      f"{len(KGDB.by_person)} persons, year coverage "
      f"{KGDB.year_coverage}/{len(KGDB.events)}", file=sys.stderr)

# --------------------------------------------------------------------------
# MCP server
# --------------------------------------------------------------------------

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP(
    "zizhi-tongjian-kg",
    instructions=(
        "Query a structured knowledge graph of the Zizhi Tongjian "
        "(资治通鉴), the Chinese chronicle covering 403 BC - 959 AD. "
        "Years are integers: negative = BC (e.g. -403), positive = AD. "
        "Event descriptions and names are in Chinese (traditional/simplified "
        "mixed, as in the source); tool descriptions are in English."
    ),
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8000")),
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def search_events(query: str, limit: int = 10) -> dict:
    """Full-text search over the Zizhi Tongjian knowledge graph.

    Searches event descriptions, person names, place names, event types and
    era labels. The query may be a Chinese keyword or phrase (e.g. "三家分晋",
    "长平之战", "王莽"), a person's name, or a place. Multiple space-separated
    terms are ANDed. Results are ranked (person/place matches first) and then
    chronological. Returns matching events with year, era, type and summary.
    """
    limit = max(1, min(int(limit), 50))
    terms = [t for t in re.split(r"\s+", query.strip()) if t]
    if not terms:
        return {"query": query, "total_matches": 0, "results": []}
    # The corpus mixes traditional and simplified characters; fold both the
    # query and the indexed text to simplified so either script matches.
    fterms = [fold(t) for t in terms]
    scored = []
    for rec in KGDB.events:
        hay = fold(rec["desc"] + "\n" + "\n".join(rec["persons"]) + "\n" +
                   "\n".join(rec["places"]) + "\n" + rec["type"] + "\n" +
                   (rec["era"] or ""))
        if not all(t in hay for t in fterms):
            continue
        fpersons = [fold(p) for p in rec["persons"]]
        fplaces = [fold(p) for p in rec["places"]]
        fdesc = fold(rec["desc"])
        score = 0
        for t in fterms:
            if t in fpersons:
                score += 5
            if t in fplaces:
                score += 3
            if t in fold(rec["type"]):
                score += 2
            score += min(fdesc.count(t), 3)
        scored.append((score, rec))
    scored.sort(key=lambda sr: (-sr[0], sr[1]["year"] is None,
                                sr[1]["year"] or 0))
    return {
        "query": query,
        "total_matches": len(scored),
        "returned": min(limit, len(scored)),
        "results": [KGDB.public(r) for _, r in scored[:limit]],
    }


@mcp.tool()
def get_person(name: str) -> dict:
    """Get a profile of a historical person from the Zizhi Tongjian graph.

    Looks up the person (Chinese name, e.g. "智伯" — used in narrative text,
    "刘邦", "曹操", "李世民") in the graph's person index. Returns the number
    of events they appear in, the active year span, main event types and
    places, the people they most often appear with, and a chronological list
    of their events (capped at 100). If the name is not a distinct index
    entry, falls back to narrative mentions in event descriptions.
    """
    recs = KGDB.by_person.get(name)
    matched_note = None
    if not recs:
        # script-variant lookup (e.g. simplified query for a traditional name)
        canon = KGDB.by_person_folded.get(fold(name), [])
        if len(canon) == 1:
            recs = KGDB.by_person[canon[0]]
            matched_note = f"Matched index entry '{canon[0]}' (script variant)."
    if recs:
        years = [r["year"] for r in recs if r["year"] is not None]
        types = Counter(r["type"] for r in recs if r["type"])
        places = Counter(p for r in recs for p in r["places"])
        assoc = Counter(p for r in recs for p in r["persons"] if p != name)
        evs = sorted(recs, key=lambda r: (r["year"] is None, r["year"] or 0))
        return {
            "found": True,
            "name": name,
            "matched_as": "person_index",
            **({"note": matched_note} if matched_note else {}),
            "event_count": len(recs),
            "first_year": min(years) if years else None,
            "last_year": max(years) if years else None,
            "top_types": types.most_common(5),
            "top_places": places.most_common(5),
            "top_associates": assoc.most_common(10),
            "events": [KGDB.public(r) for r in evs[:100]],
            "events_truncated": len(recs) > 100,
        }
    # fallback: narrative mentions in descriptions (script-folded)
    fname = fold(name)
    hits = [r for r in KGDB.events if fname in fold(r["desc"])]
    if hits:
        return {
            "found": True,
            "name": name,
            "matched_as": "description_mentions",
            "note": "Not a distinct person-index entry; these are events whose "
                    "narrative text mentions the name.",
            "event_count": len(hits),
            "events": [KGDB.public(r) for r in hits[:100]],
            "events_truncated": len(hits) > 100,
        }
    suggestions = [p for p in KGDB.by_person if name in p or p in name][:5]
    return {
        "found": False,
        "name": name,
        "message": "No person or mention found under this exact name.",
        "suggestions": suggestions,
    }


@mcp.tool()
def get_events_by_year(year: int) -> dict:
    """Get all recorded events for one Gregorian year.

    Year convention: negative = BC (e.g. -403 is 403 BC, the opening year of
    the chronicle), positive = AD (e.g. 626, the year of the Xuanwu Gate
    Incident). Coverage is 403 BC - 959 AD. If the requested year has no
    dated events, the nearest years that do are suggested.
    """
    year = int(year)
    recs = KGDB.by_year.get(year, [])
    out = {
        "year": year,
        "year_display": KGDB.year_display(year),
        "count": len(recs),
        "eras": sorted({r["era"] for r in recs if r["era"]}),
        "events": [KGDB.public(r) for r in recs],
    }
    if not recs and KGDB.by_year:
        nearest = sorted(KGDB.by_year, key=lambda y: abs(y - year))[:3]
        out["note"] = "No dated events for this year in the graph."
        out["nearest_years_with_events"] = sorted(nearest)
    return out


@mcp.tool()
def get_timeline(from_year: int, to_year: int, limit: int = 100) -> dict:
    """Get a chronological slice of events between two Gregorian years.

    Years: negative = BC, positive = AD (e.g. from_year=-221, to_year=-207
    covers the fall of the Qin dynasty). Both bounds inclusive. Results are
    in chronological order, capped by limit (default 100, max 300); the
    total count in range is always reported so callers can page by
    narrowing the range.
    """
    lo, hi = sorted((int(from_year), int(to_year)))
    limit = max(1, min(int(limit), 300))
    recs = [r for r in KGDB.events
            if r["year"] is not None and lo <= r["year"] <= hi]
    return {
        "from_year": lo,
        "to_year": hi,
        "total_in_range": len(recs),
        "returned": min(limit, len(recs)),
        "truncated": len(recs) > limit,
        "events": [KGDB.public(r) for r in recs[:limit]],
    }


@mcp.tool()
def get_event(event_id: str) -> dict:
    """Get the full record of one event by its id (e.g. "001-W23-01").

    Returns the normalized event (year, era, juan, type, summary, persons,
    places) plus the complete raw annotation record from the knowledge
    graph, which may include cross-references (concurrent_with,
    related_lunzans — links to Sima Guang's editorial essays), source notes
    and remarks.
    """
    rec = KGDB.by_id.get(event_id.strip())
    if not rec:
        return {"found": False, "event_id": event_id,
                "message": "No event with this id."}
    out = KGDB.public(rec, full=True)
    out["found"] = True
    return out


@mcp.tool()
def kg_stats() -> dict:
    """Statistics about the Zizhi Tongjian knowledge graph.

    Computed live from the loaded data: total events, volumes (juan),
    distinct persons and places, the dated-year span, how many events carry
    a resolved Gregorian year (and the method summary), and the most common
    event types.
    """
    years = [r["year"] for r in KGDB.events if r["year"] is not None]
    places = {p for r in KGDB.events for p in r["places"]}
    types = Counter(r["type"] for r in KGDB.events if r["type"])
    juans = {r["juan"] for r in KGDB.events}
    return {
        "total_events": len(KGDB.events),
        "volumes_juan": len(juans),
        "distinct_persons": len(KGDB.by_person),
        "distinct_places": len(places),
        "events_with_gregorian_year": len(years),
        "year_coverage_percent": round(100.0 * len(years) / len(KGDB.events), 1),
        "year_span": {
            "earliest": KGDB.year_display(min(years)),
            "latest": KGDB.year_display(max(years)),
        },
        "top_event_types": types.most_common(12),
        "year_resolution_method": (
            "Era-year labels in event ids are pinned to Gregorian years by "
            "section headers in the annotated chapters (chapter_md) and by "
            "explicit year fields in the KG files; remaining years are "
            "derived by era arithmetic (era start + reign year - 1), with "
            "same-name eras from different dynasties disambiguated by "
            "volume year spans. Unresolvable events keep year=null."
        ),
        "data_source": (
            "Zizhi Tongjian (资治通鉴), Wikisource Hu Sansheng annotated "
            "edition, all 294 juan; events annotated into a knowledge graph "
            "(persons, places, types, cross-references)."
        ),
    }


def main():
    ap = argparse.ArgumentParser(description="Zizhi Tongjian KG MCP server")
    ap.add_argument("--stdio", action="store_true",
                    help="serve over stdio instead of Streamable HTTP")
    args = ap.parse_args()
    if args.stdio:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
