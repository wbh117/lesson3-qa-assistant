# -*- coding: utf-8 -*-
"""步骤6/7：评测跑分脚本。匹配逻辑与 06_问答助手.html 内嵌 JS 完全同口径。
用法：python3 脚本/step6_评测.py [输出前缀]  （默认输出 08_评测结果.csv / 07_评测报告.md）"""
import csv, json, re, sys

TAG = sys.argv[1] if len(sys.argv) > 1 else ""   # 修订前评测传 "_pre"
OUT_CSV = f"08_评测结果{TAG}.csv"
OUT_MD = f"07_评测报告{TAG}.md"

kb = json.load(open("03_知识库.json", encoding="utf-8"))
cfg = json.load(open("05_规则配置.json", encoding="utf-8"))
TH = cfg["match_threshold"]
RULES = cfg["refusal_rules"]
V08 = next(r for r in RULES if r["rule_id"] == "V08")
COURSE_TERMS = [t for t in V08.get("course_terms_hint", "").split(",") if t]

def norm(s):
    return re.sub(r"[\s，。？?！!、,\.·（）()\[\]\"'「」]", "", s).lower()

def bigrams(s):
    return {s[i:i+2] for i in range(len(s) - 1)}

def containment(qb, cb):
    if not qb:
        return 0.0
    return len(qb & cb) / len(qb)

def tag_bonus(qn, item):
    b = 0.0
    for t in item["tags"]:
        if norm(t) in qn:
            b += 0.05
    return min(b, 0.1)

def detect_refusal(qn):
    for r in RULES:
        kw = next((k for k in r.get("keywords", []) if norm(k) in qn), None)
        if not kw:
            continue
        if r["rule_id"] == "V01":
            ex = ["workbuddy", "trae", "deepseek", "工具", "可选", "安装", "装"]
            if any(e in qn for e in ex):
                continue
        if r["rule_id"] == "V08":
            if kw:
                return r, kw
            if len(qn) < 4 and not any(norm(t) in qn for t in COURSE_TERMS):
                return r, None
            continue
        return r, kw
    return None, None

def answer(q_raw):
    qn = norm(q_raw)
    if not qn:
        return {"type": "empty"}
    r, kw = detect_refusal(qn)
    if r:
        return {"type": "refuse", "rule": r["rule_id"], "kw": kw}
    qb = bigrams(qn)
    scored = []
    for it in kb["items"]:
        best, cand = 0.0, ""
        for c in [it["question"]] + it["aliases"]:
            s = containment(qb, bigrams(norm(c)))
            if s > best:
                best, cand = s, c
        final = min(1.0, best + tag_bonus(qn, it))
        if final > 0:
            scored.append((final, it, cand))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] < TH:
        return {"type": "lowconf", "top": scored[0][0] if scored else 0.0}
    top = scored[0][0]
    ties = [x for x in scored if x[0] == top][:2]
    if len(ties) >= 2:
        return {"type": "tie", "cands": ties}
    return {"type": "answer", "it": scored[0][1], "score": top, "cand": scored[0][2]}

# ---------- 跑 20 题 ----------
rows = list(csv.DictReader(open("素材包/04_评测集.csv", encoding="utf-8-sig")))
out, n_ans_ok, n_ref_ok, n_ans, n_ref, errors = [], 0, 0, 0, 0, []
for r in rows:
    no = r["题号"]; q = r["问题"]; exp = r["期望处理"]; exp_id = r["期望条目id"]
    res = answer(q)
    if exp == "应答":
        n_ans += 1
        ok = res["type"] == "answer" and res["it"]["id"] == exp_id
        err_type = "" if ok else ("低置信度误拒" if res["type"] in ("lowconf", "empty")
                                  else ("命中错误条目" if res["type"] == "answer" else f"被{res.get('rule')}误拒答"))
        n_ans_ok += ok
    else:
        n_ref += 1
        ok = res["type"] == "refuse"
        err_type = "" if ok else f"未拒答（{res['type']}，命中{res['it']['id'] if res['type']=='answer' else ''}）"
        n_ref_ok += ok
    actual_id = res["it"]["id"] if res["type"] == "answer" else (res.get("rule") if res["type"] == "refuse" else "拒答(低置信度)")
    out.append([no, q, exp, exp_id or "—", res["type"], actual_id,
                f"{res['score']:.2f}" if res["type"] == "answer" else ("0.00" if res["type"] != "tie" else "并列"),
                "正确" if ok else "错误", err_type])
    if not ok:
        errors.append((no, q, exp, err_type))

with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["题号", "问题", "期望处理", "期望条目id", "实际处理", "实际条目id", "匹配得分", "是否正确", "错误类型"])
    w.writerows(out)

total_ok = n_ans_ok + n_ref_ok
total = n_ans + n_ref
md = f"""# 07 · 评测报告{TAG}

> 评测集：`素材包/04_评测集.csv`（20 题 = 16 应答 + 4 拒答）。跑分由 `脚本/step6_评测.py` 实跑输出，匹配逻辑与 `06_问答助手.html` 内嵌 JS 完全同口径，未手工填写任何数字。

## 一、核心指标（均由脚本计算）

| 指标 | 分子/分母 | 百分比 |
|---|---|---|
| 应答准确率 | {n_ans_ok}/{n_ans} | {n_ans_ok/n_ans*100:.1f}% |
| 拒答正确率 | {n_ref_ok}/{n_ref} | {n_ref_ok/n_ref*100:.1f}% |
| 总体正确率 | {total_ok}/{total} | {total_ok/total*100:.1f}% |

## 二、错题分类与原因分析

"""
if errors:
    md += "| 题号 | 问题 | 期望 | 错误类型与原因 |\n|---|---|---|---|\n"
    for no, q, exp, et in errors:
        md += f"| {no} | {q} | {exp} | {et} |\n"
else:
    md += "本轮无错题。\n"
md += f"\n## 三、逐题结果\n\n见 `{OUT_CSV}`（20 行数据 + 1 行表头，9 列）。\n"
open(OUT_MD, "w", encoding="utf-8").write(md)

print(f"应答 {n_ans_ok}/{n_ans} | 拒答 {n_ref_ok}/{n_ref} | 总体 {total_ok}/{total}")
for no, q, exp, et in errors:
    print(f"  错题 {no}: {q} → {et}")
print("输出:", OUT_CSV, OUT_MD)
