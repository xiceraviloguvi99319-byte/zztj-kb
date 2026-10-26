# zztj-kb · 《资治通鉴》开放知识图谱

> Open knowledge graph of *Zizhi Tongjian* (《资治通鉴》): an event-annotated, machine-readable corpus of 1,400 years of Chinese history.

《资治通鉴》是北宋司马光主编的编年体通史，294 卷，起周威烈王二十三年（前 403），至后周世宗显德六年（959），贯穿 16 朝。本项目逐卷进行实体标注与事件抽取，构建开放、可检索的历史事件知识图谱，供文史研究与数字人文使用。

*Zizhi Tongjian*, compiled under Sima Guang (Northern Song), is the great chronological general history of China: 294 volumes covering 403 BCE – 959 CE. This project annotates every volume — named entities plus structured historical events — into an open, machine-readable knowledge graph for research and digital humanities.

## 进展 / Progress

| 指标 / Metric | 数值 / Value |
|---|---|
| 全书卷数 / Total volumes | 294 |
| 已完成 / Completed | 294 |
| 事件总数 / Events extracted | 27,141 |
| 底本 / Source text | 维基文库胡三省音注校刊本 |
| 状态 / Status | 全书标注完成（2026-10-21）/ Annotation complete (2026-10-21) |

详细进度见 [`stats.json`](stats.json)。

## 目录 / Layout

```
zztj-kb/
├── README.md                 本文件
├── LICENSE                   MIT（代码）/ CC-BY-4.0（数据）
├── stats.json                实时进度统计
├── docs/
│   ├── annotation-spec.md    实体标注规范 v1.0（19 类实体符号）
│   └── methodology.md        流水线方法说明
├── data/
│   └── sample/               示例事件数据（5 卷）
├── kg/
│   ├── events/               全 294 卷事件数据（27,141 条；含 parts146 补注）
│   ├── entities/             实体索引
│   └── relations/            实体关系索引
└── chapter_md/               逐卷标注后的 Markdown 全文（294 卷）
```

## 事件数据格式 / Event schema

每卷一个 JSON，示例见 [`data/sample/`](data/sample/)：

```json
{
  "volume": "001",
  "year_label": "威烈王二十三年",
  "events": [
    {
      "id": "001-W23-01",
      "type": "政治/分封",
      "desc": "周威烈王命晋大夫魏斯、赵籍、韩虔为诸侯（三家分晋合法化）",
      "人物": ["魏斯", "赵籍", "韩虔"],
      "related_lunzans": ["臣光论礼：名分之坏"]
    }
  ]
}
```

事件类型覆盖军事、政治、经济、刑罚等；人物、地点、邦国、官职、年号等 19 类实体见 [标注规范](docs/annotation-spec.md)。

## 方法 / Methodology

详见 [docs/methodology.md](docs/methodology.md)：底本清洗 → 胡注校勘处理 → 19 类实体标注 → 事件抽取（编年排序）→ 人工抽检。标注规范由史记知识图谱方法论迁移而来。

## 许可 / License

- 代码与文档：MIT
- 事件数据：CC-BY-4.0（使用请注明出处）

## 基础设施 / Infrastructure

本项目已向 [BlueServers](https://blueservers.com) 申请免费服务器支持（审核中）。

*This project is applying for free hosting support from BlueServers (under review).*

## 联系 / Contact

通过 GitHub Issues 联系。欢迎校勘指正与合作。
