"""
祖方族谱核心解析器 — 共用于 Skill A(方族谱)与 Skill B(演化时间轴)

数据源:ysjllsj.TypeID=495 ID 98643~98679
  = 清·张璐《张氏医通》卷十六·祖方(康熙三十四年 1695)
  = 33 个方祖 + 各自嵌入的 [b]变法方[/b] 块

输入:方名(可多别名,如「肾着汤/甘姜苓术汤」)
输出:
  - parse_zugfang_chapter():返回 33 个方祖 + 各自变法方列表(原始 + 索引)
  - find_zudfang_for_formula(name):查询给定方名在哪个祖方的家族里
  - render_family_tree_ascii(...):输出 草案 3 格式(60字摘要 + 详情标志)
  - get_var_method_chinese(...):提取"加减法"(如「理中汤去人参加茯苓」)

性能:解析一次缓存到 ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/references/zugfang/_parsed_cache.json
"""
import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# === 路径配置 ===
ROOT = Path("/Users/applemima1111/.hermes/skills/zhongyishijia-expert-mentor-lineage")
DB_PATH = ROOT / "references/external/zysj.db"
CACHE_PATH = ROOT / "references/zugfang/_parsed_cache.json"

# === ID 范围:ysjllsj.TypeID=495 的卷十六·祖方章 ===
#   98643 章前小序(夫字有字母...一脉相传)
#   98644~98679 33+1 个方祖(桂枝汤/麻黄汤/...金液丹)
ZUGFANG_ID_RANGE = (98643, 98679)


# === 核心解析 ===
def parse_zugfang_chapter(use_cache: bool = True) -> List[Dict]:
    """
    解析卷十六·祖方章,返回 33 个方祖 + 各自变法方。

    每个方祖的格式:
      {
        "祖方ID": 98652,
        "祖方名": "理中汤(玉函金匮名人参汤)",
        "祖方_short_name": "理中汤",
        "变法方": [
          {
            "name": "附子理中汤",
            "source": "(张璐/无标注)",
            "zheng_full": "治下焦虚寒。火不生土。泄泻呕逆。理中汤加熟附子。按方中用参三钱...",
            "zheng_short": "治下焦虚寒,火不生土,泄泻呕逆",
            "method_zh": "理中汤加熟附子",  # 加减法
            "is_zhanglu": False  # 是否标注张璐变法
          },
          ...
        ]
      }
    """
    if use_cache and CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    rows = cur.execute(
        f"""
        SELECT ID, BiaoTi, NeiRong
        FROM zysjllsj
        WHERE TypeID=495 AND ID BETWEEN ? AND ?
        ORDER BY ID
        """,
        ZUGFANG_ID_RANGE,
    ).fetchall()
    conn.close()

    # BiaoTi/BianFang 提取:章前/章末小节跳过
    zudfang_list = []

    # 变法方标签正则
    # 形式:[b]附子理中汤[/b] (出处) 治证。理中汤加熟附子。
    bian_pattern = re.compile(
        r"\[b\]([^\[\]]+?)\[/b\]"           # 变法方名
        r"(?:[\(（]([^\)）]*)[\)）])?"      # 可选出处(局方/玉函/金匮...)
        r"\s*([^\[]+?)"                   # 治证 + 加减法(直到下个 [b] 或章末)
        r"(?=\[b\]|$)",
        re.DOTALL
    )

    # 提取方祖 short_name(去掉 (玉函)/(金匮名...)/ etc 后缀)
    short_name_pat = re.compile(r"^(.+?)\s*[\(（]")

    for id_, bt, nr in rows:
        if not bt:
            continue
        # 跳过章前小序 + 章末张介宾八略总论
        if "祖方" in bt or "八略" in bt or "附张介宾" in bt:
            continue

        # ===== 提取祖方原方组成(第一段主治证,第二段组成)=====
        zudfang_yuanfang = ""
        zudfang_zhengren = ""
        zudfang_zucheng = ""     # 祖方原方组成(第二段)
        zudfang_jianfu = ""
        if nr:
            # 标准化换行符: \r\n -> \n
            nr_norm = nr.replace("\r\n", "\n").replace("\r", "\n")
            # 第一段(到 \n)是原方主治证
            lines_split = nr_norm.split("\n")
            first_segment = lines_split[0].strip() if lines_split else ""
            # 主治通常是 first_segment 第一句
            sentences = re.split(r"(?<=。)", first_segment)
            zudfang_zhengren = sentences[0].strip() if sentences else first_segment
            zudfang_yuanfang = first_segment  # 暂时保留

            # 第二段(组成)+ 第三段(煎服法,可能没有) 合并查找「上X味」
            if len(lines_split) >= 2:
                # 找到含「上X味」的段
                jianfu_idx = None
                for i, l in enumerate(lines_split):
                    if re.search(r"上\S+味", l):
                        jianfu_idx = i
                        break
                if jianfu_idx is not None and jianfu_idx > 0:
                    # lines_split[1:jianfu_idx] = 组成(可能多行)
                    zudfang_zucheng = " ".join(
                        l.strip() for l in lines_split[1:jianfu_idx] if l.strip()
                    )
                    # 煎服法:从「上X味」段后 1-2 个句号内
                    jianfu_text = " ".join(
                        l.strip() for l in lines_split[jianfu_idx:] if l.strip()
                    )
                    # 「上X味」自带 1 个「。」,跳过 — 找下一个「。」作为煎服法结尾
                    # 但按语通常从第 2 个「。」 开始,所以最多 2 个「。」后停
                    juhao_indices = [i for i, c in enumerate(jianfu_text) if c == "。"]
                    if len(juhao_indices) >= 2:
                        # 第 1 个「。」是「上X味。」自己
                        # 第 2 个「。」是煎服法结束(或紧接按语)
                        zudfang_jianfu = jianfu_text[:juhao_indices[1] + 1].strip()
                    elif len(juhao_indices) == 1:
                        # 整段只 1 个「。」(就是「上X味」自己)
                        zudfang_jianfu = jianfu_text[juhao_indices[0] + 1:][:120].strip()
                    else:
                        zudfang_jianfu = jianfu_text[:120]
                else:
                    # 没有「上X味」标记 — 全当原方
                    zudfang_zucheng = " ".join(
                        l.strip() for l in lines_split[1:] if l.strip()
                    )

            # 也整合到 yuanfang (主方+组成,方便全段显示)
            if zudfang_zucheng:
                zudfang_yuanfang = f"{zudfang_zhengren}\n{zudfang_zucheng}"
            if zudfang_jianfu:
                zudfang_yuanfang += f"\n{zudfang_jianfu}"

        # 解析这个方祖段里的 [b]变法方[/b] 块
        bian_list = []
        nr_clean = nr or ""
        for m in bian_pattern.finditer(nr_clean):
            name = m.group(1).strip()
            source = (m.group(2) or "").strip()
            zheng_raw = m.group(3).strip().replace("\r", " ")

            # 切分治证 + 加减法
            # 关键发现:ysjllsj 用 \n (换行) 分隔 "治证段" 和 "加减法段"
            # 例: '治腰以下重着而痛。\n理中汤去人参加茯苓。 肾着者...'
            zheng_raw_clean = zheng_raw.replace("\n", " ")
            # 先按 \n 拆段(单换行是关键分隔)
            raw_lines = zheng_raw.split("\n")
            # 加减法触发词集合(不要依赖 regex 处理中文 + escape)
            # 含「加」「减」「去」「入」「合」「化」「变」「易」「换」
            ADD_MINUS_WORDS = set("加减去入合化变易换")
            # 治证段: 累积不以「X汤加减」「本方加减」开头的段
            zheng_lines = []
            method_line = None
            for ln in raw_lines:
                ln_strip = ln.strip()
                if not ln_strip:
                    continue
                # 检测「X汤 + 加减词」开头
                # 在 1-5 个汉字内找「汤」+ 紧接加减字
                is_method_line = False
                # 找「汤」出现位置
                tang_idx = None
                for i in range(min(len(ln_strip), 12)):  # 至多看前 12 字符
                    if ln_strip[i] == "汤" and i > 0:
                        tang_idx = i
                        break
                if tang_idx is not None:
                    # 检查「汤」之后紧接的字是不是加减词之一
                    next_char_idx = tang_idx + 1
                    if next_char_idx < len(ln_strip):
                        next_char = ln_strip[next_char_idx]
                        if next_char in ADD_MINUS_WORDS:
                            is_method_line = True
                # 「原方」「本方」开头的也归为 method_line
                if ln_strip.startswith("原方") or ln_strip.startswith("本方"):
                    # 检查「原方/本方」后是否紧接加减速词
                    rest = ln_strip[2:].lstrip()  # 跳过"原方"2 字
                    if rest and rest[0] in ADD_MINUS_WORDS:
                        is_method_line = True

                if is_method_line:
                    method_line = ln_strip
                    break
                zheng_lines.append(ln_strip)
                if len(zheng_lines) >= 2:  # 治证通常 1-2 段
                    break
            else:
                # 没 break — 整段都是治证(没有显式加减)
                pass

            zheng_short = " ".join(zheng_lines).replace("\r", "")[:80]
            if not zheng_short:
                # 兜底:用句号分句
                sentences = re.split(r"(?<=。)|(?<=！)|(?<=？)", zheng_raw)
                sentences = [s.strip() for s in sentences if s.strip()]
                zheng_short = sentences[0] if sentences else zheng_raw[:80]

            # 加减法:从 method_line 提取「X汤 + 加减词 + 名词」
            method_zh = ""
            if method_line:
                # 例:「理中汤去人参加茯苓。」「本方去人参、白术。」
                # 用 string 找首个「。」或「;(逗号)」结束
                # 先找到加减词的位置
                if method_line.startswith("原方") or method_line.startswith("本方"):
                    # 「本方去人参、白术」+ 「。」 截止
                    # 简化:取到第一个「。」,内容是「本方/原方 [加减词] ...」
                    end_idx = method_line.find("。")
                    method_zh = method_line[:end_idx].rstrip() if end_idx > 0 else method_line
                    # 裁掉开头的「本方/原方」+ 直接进入加减速
                    method_zh = (
                        (method_line[:2] if method_line.startswith("原方") else method_line[:2])
                        + method_line[2:]
                    )
                    # 简化:「原方去X」->「去X」
                    if method_line.startswith(("本方", "原方")):
                        method_zh = method_line[2:].lstrip()[:80]
                    else:
                        method_zh = method_line[:80]
                else:
                    # 「X汤 + 加减词 ...」句
                    tang_idx = method_line.find("汤")
                    if tang_idx >= 0 and tang_idx < len(method_line) - 2:
                        # 取「汤」之后到第一个「。」之前
                        after_tang = method_line[tang_idx + 1:]
                        end_idx = after_tang.find("。")
                        if end_idx > 0:
                            method_zh = method_line[:tang_idx + 1 + end_idx].rstrip()
                        else:
                            method_zh = method_line[:80]
                    else:
                        method_zh = method_line[:80]
                method_zh = method_zh.strip().rstrip("。,。.")[:80]

            # 没找到 method_line — 加减速法段可能跟治证在同一段
            if not method_zh:
                # 看 zheng_short 后有没有「X汤去/加」类似的短语
                for ln in zheng_lines[1:]:
                    # 在 1-5 个汉字内找「汤」+ 紧接加减字
                    tang_idx = ln.find("汤")
                    if tang_idx > 0 and tang_idx < len(ln) - 2:
                        after = ln[tang_idx + 1]
                        if after in ADD_MINUS_WORDS:
                            end_idx = ln.find("。")
                            method_zh = ln[:end_idx].rstrip() if end_idx > 0 else ln
                            method_zh = method_zh[:80]
                            break

            if not method_zh:
                method_zh = "(治证即变法,无显式加减)"

            # ── 兜底:在 zheng_full 全文搜加减法(更宽松)──
            # 解决「加减法跨段」(本方用术... 在 L1, 加 X 在 L2) 抓不到的问题
            # 也支持「术附汤本方用术X附X加X」这种格式
            if method_zh == "(治证即变法,无显式加减)":
                zf_search = zheng_raw

                # Strategy A: 找「X汤+加减词」短语
                positions = []
                for i in range(len(zf_search) - 1):
                    if zf_search[i] == "汤":
                        after = zf_search[i + 1] if i + 1 < len(zf_search) else ""
                        window = zf_search[i + 1:i + 4]
                        for kw in ADD_MINUS_WORDS:
                            if kw in window:
                                start = i
                                while start > 0 and zf_search[start - 1] not in "。，,。 \n\r":
                                    start -= 1
                                end = zf_search.find("。", i)
                                if end < 0:
                                    end = i + 40
                                candidate = zf_search[start:end].rstrip()
                                if 4 <= len(candidate) <= 60:
                                    positions.append(candidate)
                                break

                # Strategy B: 找「术附汤本方用术X附X加X」这种完整加减段
                # 模式: 「X汤本方」后到「分温三服」/「为散」/「姜、枣汤」/「日三服」前
                bonfang_match = re.search(
                    r"([一-鿿]{2,4}汤)本方用([^)]{4,60}?)(?:分温|为散|姜、枣汤|日三服|上五味|上四味|分三服)",
                    zf_search,
                )
                if bonfang_match:
                    positions.append(bonfang_match.group(0)[:80])

                # Strategy C: 找「加X一两」「去X」/「合X」/「倍X」等纯加减
                # 模式:「去/加/合/倍 + 中药名 + 数字」
                pure_method = re.search(
                    r"([加减合倍]入?[一-鿿A-Za-z·、]{2,12}(?:各)?[一二三四五六七八九十百千万半\d]*[钱两片枚合剂分字个套杯升]?)",
                    zf_search,
                )
                if pure_method:
                    positions.append(pure_method.group(0)[:50])

                if positions:
                    method_zh = max(positions, key=len)[:80]

            # 判断是否张璐自有变法
            is_zhanglu = not source and "按" not in zheng_raw[:30]  # type: ignore[assignment] # noqa

            bian_list.append({
                "name": name,
                "source": source or "(张璐)",  # 无出处按张璐自变法处理
                "zheng_full": zheng_raw,
                "zheng_short": zheng_short[:80],
                "method_zh": method_zh,
                "is_zhanglu": is_zhanglu,
            })

        # 祖方 short_name
        m_short = short_name_pat.match(bt)
        zudfang_short = m_short.group(1).strip() if m_short else bt.strip()

        zudfang_list.append({
            "祖方ID": id_,
            "祖方名": bt,
            "祖方_short_name": zudfang_short,
            "原方": zudfang_yuanfang,         # 祖方原方组成 + 主治第一段
            "原方_主治": zudfang_zhengren,     # 祖方原方主治证
            "原方_组成": zudfang_zucheng,     # 祖方原方组成(单列)
            "原方_煎服法": zudfang_jianfu,   # 祖方原方煎服法
            "变法方": bian_list,
        })

    # 写缓存
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(zudfang_list, ensure_ascii=False, indent=2))
    return zudfang_list


# === 查询入口 ===
def find_zudfang_for_formula(zudfang_list: List[Dict], formula_name: str) -> List[Tuple[Dict, Dict]]:
    """给定方名 → 返回 (祖方, 变法方) 元组列表"""
    hits = []
    fn = formula_name.replace(" ", "")
    # 兼容别名查询
    aliases = []
    if formula_name == "肾着汤" or formula_name == "甘姜苓术汤":
        aliases = ["甘姜苓术汤", "肾着汤"]
    elif formula_name == "理中汤" or formula_name == "人参汤":
        aliases = ["理中汤", "人参汤"]

    for z in zudfang_list:
        for b in z["变法方"]:
            bname_clean = b["name"].replace(" ", "")
            if (
                fn in bname_clean
                or any(a.replace(" ", "") in bname_clean for a in aliases)
                or any(a in bname_clean for a in [formula_name] + aliases)
            ):
                hits.append((z, b))
    # 去重(同一变法方出现多次)
    seen = set()
    uniq = []
    for z, b in hits:
        key = (z["祖方ID"], b["name"])
        if key not in seen:
            seen.add(key)
            uniq.append((z, b))
    return uniq


def get_zudfang_by_id(zudfang_list: List[Dict], id_: int) -> Optional[Dict]:
    for z in zudfang_list:
        if z["祖方ID"] == id_:
            return z
    return None


def get_var_methods_summary(zudfang_list: List[Dict]) -> Dict:
    """统计全书变法方特征(速查)"""
    total_bianfa = sum(len(z["变法方"]) for z in zudfang_list)
    zhanglu_origin = sum(
        1 for z in zudfang_list for b in z["变法方"] if b["is_zhanglu"]
    )
    return {
        "方祖数": len(zudfang_list),
        "变法方总数": total_bianfa,
        "张璐自拟变法方": zhanglu_origin,
        "引用他书变法方": total_bianfa - zhanglu_origin,
        "平均每方祖变法方数": round(total_bianfa / max(len(zudfang_list), 1), 1),
    }


# === CLI 测 ===
if __name__ == "__main__":
    import sys

    zudfang = parse_zugfang_chapter()
    print(f"=== 祖方族谱统计 ===")
    stats = get_var_methods_summary(zudfang)
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()

    # 测试查询
    test = sys.argv[1] if len(sys.argv) > 1 else "甘姜苓术汤"
    print(f"=== 查询:「{test}」 ===")
    hits = find_zudfang_for_formula(zudfang, test)
    if hits:
        for z, b in hits:
            print(f"  📖 祖方:[{z['祖方ID']}] {z['祖方名']}")
            print(f"     └─ 变法方:[{b['name']}] (出处:{b['source']})")
            print(f"        治: {b['zheng_short']}")
            print(f"        法: {b['method_zh']}")
    else:
        print(f"  ❌ 「{test}」不在醫通祖方 33 个方祖谱系中")
        print(f"  → 用 Skill B(evolution_timeline)查跨书演化")
