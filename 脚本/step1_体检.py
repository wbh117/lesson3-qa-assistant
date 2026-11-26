# -*- coding: utf-8 -*-
"""步骤1：语料体检脚本。只读原始语料，不修改原文件。"""
import csv, re, sys, difflib
from itertools import combinations

SRC = "素材包/01_FAQ原始语料.csv"

rows = []
with open(SRC, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append({"行号": int(r["行号"]), "问题": r["问题"].strip(), "答案": r["答案"].strip(), "备注": r["备注"].strip()})

# ---------- 统计1：总行数 ----------
total = len(rows)

# ---------- 统计2：完全相同问题 ----------
def norm(s):
    return re.sub(r"[\s，。？?！!、,\.·（）()\[\]\"'「」]", "", s).lower()

exact_groups = {}
for r in rows:
    exact_groups.setdefault(norm(r["问题"]), []).append(r["行号"])
exact_dups = {k: v for k, v in exact_groups.items() if len(v) > 1}
n_exact_dup_rows = sum(len(v) for v in exact_dups.values())

# ---------- 统计3：语义近似问题对（规范化后相似度>=0.7 的不同问题对） ----------
pairs = []
for a, b in combinations(rows, 2):
    qa, qb = norm(a["问题"]), norm(b["问题"])
    if qa == qb:
        continue
    ratio = difflib.SequenceMatcher(None, qa, qb).ratio()
    if ratio >= 0.55:
        pairs.append((a["行号"], b["行号"], a["问题"], b["问题"], round(ratio, 2)))
# 人工核验备注中已声明的重复也纳入
declared = [(1,2),(1,3),(2,3),(4,5),(6,9),(7,12),(13,14),(21,22)]
declared_set = {(x,y) for x,y,_ ,_,_ in pairs} | {(y,x) for x,y,_,_,_ in pairs}
for x, y in declared:
    if (x,y) not in declared_set and (y,x) not in declared_set:
        px = next(r for r in rows if r["行号"]==x)["问题"]
        py = next(r for r in rows if r["行号"]==y)["问题"]
        pairs.append((x, y, px, py, "备注声明"))
pairs.sort()

# ---------- 统计4：空答案行号 ----------
empty_ans = [r["行号"] for r in rows if not r["答案"]]

# ---------- 统计5：错别字/口语化行号 ----------
typo_rows = [r["行号"] for r in rows if ("错别字" in r["备注"]) or ("口语化" in r["备注"])]
# 额外自动探测常见错别字模式（备注未标注的）
auto_typo = []
for r in rows:
    if "意恩" in r["问题"] or ("意思" not in r["问题"] and re.search(r"意[恩思]$", r["问题"])):
        if r["行号"] not in typo_rows:
            auto_typo.append(r["行号"])

# ---------- 统计6：含「已停用/过期」标记行号 ----------
expired = [r["行号"] for r in rows if ("已停用" in r["问题"] or "已停用" in r["备注"] or "过期" in r["备注"] or "过期条目" in r["备注"])]

# 越界示例行
outscope = [r["行号"] for r in rows if "越界" in r["备注"]]

# ---------- 输出报告 ----------
lines = []
lines.append("# 01 · 语料体检报告\n")
lines.append("> 数据来源：`素材包/01_FAQ原始语料.csv`（30 条课堂虚构课程 FAQ）。本报告由脚本 `脚本/step1_体检.py` 自动生成，只读原文件、未做任何修改。\n")
lines.append("## 一、统计表（6 项）\n")
lines.append("| # | 统计项 | 结果 | 说明 |")
lines.append("|---|---|---|---|")
lines.append(f"| 1 | 总行数 | {total} | 含表头外全部 30 条数据行 |")
lines.append(f"| 2 | 完全相同问题数 | {n_exact_dup_rows} 行（{len(exact_dups)} 组） | 规范化（去标点/空格/大小写）后完全一致的行 |")
lines.append(f"| 3 | 语义近似问题对 | {len(pairs)} 对 | 脚本相似度≥0.55 或备注声明的语义重复，详见明细表 |")
lines.append(f"| 4 | 空答案行号 | {empty_ans if empty_ans else '无'} | 共 {len(empty_ans)} 行 |")
lines.append(f"| 5 | 错别字/口语化行号 | {sorted(set(typo_rows+auto_typo)) if (typo_rows or auto_typo) else '无'} | 备注标注 {sorted(set(typo_rows))}，自动探测补充 {auto_typo} |")
lines.append(f"| 6 | 含「已停用/过期」标记行号 | {expired if expired else '无'} | 共 {len(expired)} 行，另检出越界示例行 {outscope}（不进入知识库） |")
lines.append("")
lines.append("## 二、问题明细表\n")
lines.append("| 行号 | 原文（问题） | 问题类型 | 建议处理 |")
lines.append("|---|---|---|---|")
sugg = {}
for r in rows:
    ln = r["行号"]; q = r["问题"]; note = r["备注"]; act = "保留"
    if not r["答案"]:
        act = "答案为空 → 依据已有语料补全；信息不足则标「待补充」，严禁编造"
    elif "错别字" in note:
        act = "修正错别字后与语义相同条目合并"
    elif "口语化" in note:
        act = "保留规范问法，口语问法转为别名"
    elif "过期" in note or "已停用" in q:
        act = "删除（过期条目）"
    elif "越界" in note:
        act = "不进入知识库（越界示例，由拒答规则处理）"
    elif "重复" in note:
        act = "与被重复行合并，保留规范答案"
    sugg[ln] = (q, note, act)
    lines.append(f"| {ln} | {q} | {note if note else '正常'} | {act} |")
lines.append("")
lines.append("## 三、语义近似问题对明细\n")
lines.append("| 行号对 | 问题A | 问题B | 依据 |")
lines.append("|---|---|---|---|")
for x, y, px, py, ratio in pairs:
    lines.append(f"| {x}–{y} | {px} | {py} | {ratio} |")
lines.append("")
lines.append("## 四、完全相同问题组（规范化后）\n")
if exact_dups:
    for k, v in exact_dups.items():
        lines.append(f"- 组「{k}」：行号 {v}")
else:
    lines.append("- 无（无完全一致字符串重复；重复均为语义级，见第三节）")
lines.append("")
lines.append("## 五、体检结论与清洗指引\n")
lines.append(f"- 30 条语料中：可保留并结构化约 24 条（含 {len(pairs)} 组合并、2 处错别字修正）；")
lines.append("- 空答案 2 行（行 11、27）：只能依据已有语料补全，信息不足标「待补充」，不编造政策；")
lines.append("- 过期 1 行（行 28）：删除；越界示例 2 行（行 29、30）：转为拒答规则的样例，不入知识库。\n")

with open("01_语料体检报告.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("OK 01_语料体检报告.md 生成")
print("统计：", total, "| 完全相同行:", n_exact_dup_rows, "| 近似对:", len(pairs), "| 空答案:", empty_ans, "| 错别字/口语化:", sorted(set(typo_rows+auto_typo)), "| 过期:", expired, "| 越界示例:", outscope)
