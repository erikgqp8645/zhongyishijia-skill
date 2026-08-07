# 祖方演化分析(zugfang-evolution)·附属 skill 包

> 本目录是 `zhongyishijia-expert-mentor-lineage` skill 的**附属 skill 包**,包含 2 个可独立调用但共享同一解析器的「方剂族谱分析」工具。
> 
> 数据源:张璐《张氏医通》(清·康熙三十四年 1695,ysjllsj.TypeID=495)卷十六·祖方 — 中国方剂学中**唯一清晰的「方祖-变法方」家族结构**。

---

## 1. 文件清单

| 文件 | 功能 | 共享/独立 |
|---|---|---|
| `zugfang_family_parser.py` | **核心解析器**(共用于 Skill A 和 B) | 共享 |
| `family_tree.py` | **Skill A 输出器** — 方族谱查询 | 独立输出 |
| `evolution_timeline.py` | **Skill B 输出器** — 跨书演化时间轴 | 独立输出 |
| `_parsed_cache.json` | 解析缓存:36 方祖 + 384 变法方(~180KB) | 数据 |
| `README.md` | 本文件 | 说明 |

`zugfang_family_parser.py` 一次性解析 ysjllsj.TypeID=495 ID 98643~98679 的 36 个方祖和 384 个变法方,写入 `_parsed_cache.json`。后续调用直接读缓存。

---

## 2. 2 个 skill 的边界

```
┌─────────────────────────────────────────────────────────────────────┐
│  Skill A:zugfang-family-tree(方族谱)                                   │
│  触发词:「方族谱」「X 是哪个祖方」「X 变法方家族」「医通祖方」         │
│                                                                     │
│  数据源:ysjllsj.TypeID=495(纯《醫通祖方》)                              │
│  答的是:这方跟哪些方是「同家族」+ 在原书里怎么记载(治证 + 加减法)        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ 共享解析器(Skill A 和 B 共用)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Skill B:zugfang-evolution-timeline(跨书演化时间轴)                     │
│  触发词:「X 演化」「X 历代」「X 后世发展」「跨书考证」                │
│                                                                     │
│  数据源(6 源拼接):                                                   │
│   1) ysjllsj.TypeID=495 卷十六·祖方(医疗通结构)                        │
│   2) ysjllsj.TypeID=495 卷六散在应用(身重/湿/腰痛/痿/脚心痛)             │
│   3) query_formula.py 全文检索(31.76 万张卡片)                          │
│   4) books_json/0544 王肯堂《证治准绳类方》(明)                       │
│   5) books_json/0760 尤怡《退思集类方歌注》(清)                       │
│   6) books_json/0721 戴思恭《秘传证治要诀及类方》(明)               │
│  答的是:这方从东汉到现代,有多少种理解/怎么演化                         │
└─────────────────────────────────────────────────────────────────────┘
```

两 skill **共享同一解析器**(`zugfang_family_parser.py`),但**输出侧重点不同**:
- Skill A:**结构**(家族里哪些方、加减法是什么)
- Skill B:**时间**(演化顺序、其他书的注解)

---

## 3. 使用方法

### 3.1 Skill A:方族谱(快速查询)

```bash
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/references/zugfang

# 概览:全部 36 方祖 + 变法方数
python3 family_tree.py

# 查询某方:返回方族谱 ASCII 树 + 加减法速查表
python3 family_tree.py "理中汤"
python3 family_tree.py "甘姜苓术汤"   # 自动别名:肾着汤
python3 family_tree.py "肾着汤"        # 自动别名:甘姜苓术汤

# 详情模式:展开某个变法方的全文
python3 family_tree.py "理中汤" --detail 10
```

### 3.2 Skill B:跨书演化时间轴

```bash
python3 evolution_timeline.py "甘姜苓术汤"
python3 evolution_timeline.py "理中汤"
python3 evolution_timeline.py "桂枝汤"   # 含 26 变法方的大族谱
```

### 3.3 作为 Python API

```python
import sys
sys.path.insert(0, "/Users/applemima1111/.hermes/skills/zhongyishijia-expert-mentor-lineage/references/zugfang")

from zugfang_family_parser import parse_zugfang_chapter, find_zudfang_for_formula
from family_tree import render_family_tree
from evolution_timeline import run_evolution

zudfang = parse_zugfang_chapter()
print(render_family_tree(zudfang, "理中汤"))
print(run_evolution("理中汤"))
```

---

## 4. 输出格式(统一)

无论 Skill A 或 Skill B,输出均采用:
1. **ASCII 树形结构**(方案 3:60 字摘要 + 详情标志 `--detail N`)
2. **Markdown 速查表**(变法方名 / 出处 / 加减法 / 治证)
3. **朝代时间轴**(Skill B 专属,Skill A 不展开)
4. **一句话核心心法**(把多源压缩为一句临床洞察)

---

## 5. 数据来源详解

### 5.1 Primary:`ysjllsj.TypeID=495` 张璐《张氏医通》

**作者**:张璐,清·康熙三十四年(1695)。
**全 536 条** ID 98154~98689,**卷十六·祖方** 在 ID 98643~98679 共 37 条:
- 98643 章前小序「夫字有字母,方有方祖...一脉相传」
- 98644~98679 **36 个方祖** + 各自变法方
- 98680 「卷十六\附张介宾八略总论」

### 5.2 36 方祖列表

```
方祖[ID]                    方祖名                              变法方数
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[98644] 桂枝汤(玉函)        《张氏医通》最丰富的家族            26
[98645] 麻黄汤(玉函)        外感族谱核心                        23
[98648] 小柴胡汤(玉函)      少阳枢机                           15
[98649] 星香汤             中风痰迷                            4
[98650] 术附汤             寒湿痹                              9
[98651] 四逆汤(玉函)        阳虚急救                          13
[98652] 理中汤(玉函金匮名人参汤)  太阴虚寒                    13  ← 含「甘姜苓术汤」
[98653] 半夏泻心汤          痞满                              4
[98654] 局方七气汤         气滞                                9
[98655] 崔氏八味丸          肾气丸变法                         11
[98656] 金匮枳术汤          水饮                                4
[98657] 平胃散              湿困脾胃                           14
[98658] 二陈汤(局方)        痰湿                                27
[98659] 四君子汤(局方)      气虚                                17
[98660] 四物汤(局方)        血虚                                32  ← 最大家族
[98661] 保元汤              阳虚补气                           30
[98662] 生脉散              津气                                5
[98663] 二冬膏              津伤                                4
[98664] 桔梗汤(玉函)        咽痛                                8
[98665] 防己黄汤            风水                                2
[98666] 栀子豉汤(玉函)      虚烦                                9
[98667] 小承气汤(玉函)      腑实                                14
[98668] 抵当汤(玉函)        蓄血                                4
[98669] 凉膈散(局方)        中上焦热                           5
[98670] 备急丸              寒积                                4
[98671] 伊芳尹三黄汤         火热                                18
[98672] 十枣汤(玉函)        悬饮                                2
[98673] 五苓散(玉函)        水湿                                9
[98674] 益元散              暑湿                                3
[98675] 白虎汤(玉函)        阳明热                              11
[98676] 驻车丸              久痢                                4
[98677] 佐金丸              肝肺                                4
[98678] 大补丸              阴虚                                6
[98679] 金液丹              阳脱                                8
```

---

## 6. 精度问题(已知)

| 编号 | 问题 | 状态 |
|---|---|---|
| 1 | 「加减法」字段在某些变法方(尤其是 [7][8][9][13])解析为「理中汤去白术、甘草」等准确措辞,✅ | 已解决 |
| 2 | Skill B 朝代时间轴,东汉+清+现代条目丰富,隋唐宋条目偏少(主要因为 query_formula 全文检索对老方剂不完全) | 已知限制 |
| 3 | 「仲景」出现 3 次(query_formula 对同方多次匹配) | 视觉去重即可 |

---

## 7. 未来扩展

- 加 Skill C:**「跨祖方家族对比」** — 输入 2-3 个方剂名,对比它们在哪几个祖方家族里出现
- 加 Skill D:**「按主治证反查」** — 输入症状「腰以下重着而痛」,反查用哪些方(已经在 query_formula 里)
- 加 Skill E:**「基于祖方的加减法生成」** — 用户给定场景(如「温中汤」+ 「寒湿」),自动建议祖方变法

---

## 8. 注意事项

- `_parsed_cache.json` 是静态缓存,**修改 ysjllsj 不会自动刷新**。如需重新解析,删除此文件即可。
- 本 skill 包只在 zhongyishijia skill 内部使用,不直接对外暴露触发词。如需调用,在 zhongyishijia skill 入口加 trigger vocabulary。
- 「X 是哪个祖方」「X 变法方家族」是触发 Skill A 的信号;「X 演化」「X 后世」「跨书」是触发 Skill B 的信号。
- 共同前缀「X 张璐」「X 医通祖方」通用触发任一 skill,根据用户需求细节判断。
