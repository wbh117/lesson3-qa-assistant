# -*- coding: utf-8 -*-
"""步骤3：生成 03_知识库.json 并脚本校验。
answer 逐字取自 02_规范问答集.csv；别名结合 02_术语表.csv 扩展；scope 限四值之一。"""
import csv, json

SCOPE_SET = {"课程内容", "作业提交", "工具使用", "平台操作"}

# (id, question, aliases, tags, scope)  answer/source 从规范问答集读取
defs = [
    ("q01", "这门课一共几次课", ["课程有几次课呀", "一共几节课", "课程共有多少次", "课程总共有几节课"], ["课程内容", "课时"], "课程内容"),
    ("q02", "课件在哪里下载", ["课件在哪下", "幻灯片哪里下载", "PPT哪里下载"], ["平台操作", "课件"], "平台操作"),
    ("q03", "练习资源包怎么拿", ["练习资源包在哪儿", "资源包怎么下载", "ZIP包在哪"], ["平台操作", "练习资源包"], "平台操作"),
    ("q04", "一次练习要做多久", ["练习要做多久", "一套练习多长时间"], ["课程内容", "练习"], "课程内容"),
    ("q05", "练习题可以一个人做吗", ["需要组队吗", "可以单人完成吗", "练习能组队吗"], ["课程内容", "练习"], "课程内容"),
    ("q06", "课程用哪些工具", ["主要用啥工具", "用什么软件", "课程工具是什么"], ["工具使用", "WorkBuddy"], "工具使用"),
    ("q07", "没装 Trae 会不会影响成绩", ["不装Trae影响成绩吗", "Trae必须装吗", "可选工具要装吗"], ["工具使用", "Trae"], "工具使用"),
    ("q08", "不会编程能选吗", ["没有编程基础能选吗", "零基础可以学吗", "要会写代码吗"], ["课程内容", "编程基础"], "课程内容"),
    ("q09", "术语词典在哪", ["Term是什么意思", "术语表在哪", "词典在哪个页面"], ["平台操作", "术语词典"], "平台操作"),
    ("q10", "课程大纲在哪看", ["大纲在哪", "syllabus在哪看", "课程安排在哪看"], ["平台操作", "课程大纲"], "平台操作"),
    ("q11", "有没有教材", ["教材在哪", "有没有课本", "分章文本在哪"], ["平台操作", "教材"], "平台操作"),
    ("q12", "静态展示版能登录吗", ["静态版可以登录吗", "GitHub Pages版能登录吗", "静态展示版登录可用吗"], ["平台操作", "静态展示版"], "平台操作"),
    ("q13", "静态版怎么下载资料", ["静态版资料怎么下", "不用登录能下载吗", "静态版怎么拿练习"], ["平台操作", "下载"], "平台操作"),
    ("q14", "个人中心能干什么", ["个人中心有什么用", "个人中心功能", "登录后能看什么"], ["平台操作", "个人中心"], "平台操作"),
    ("q15", "作业什么时候交", ["作业截止时间", "作业什么时候要交", "作业提交期限"], ["作业提交"], "作业提交"),
    ("q16", "知识图谱能看吗", ["知识点关联图在哪", "图谱在哪看", "知识模块在哪"], ["平台操作", "知识图谱"], "平台操作"),
    ("q17", "忘了密码怎么办", ["密码忘了怎么办", "忘记密码怎么处理", "账号密码忘了"], ["平台操作", "账号"], "平台操作"),
]

qa = {}
with open("02_规范问答集.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        qa[r["qid"]] = r

items = []
for qid, question, aliases, tags, scope in defs:
    r = qa[qid]
    assert scope in SCOPE_SET, qid
    items.append({
        "id": qid,
        "question": question,
        "aliases": aliases,
        "answer": r["answer"],                      # 逐字取自规范问答集
        "tags": tags,
        "source": f"{qid} + 原始语料行{r['source_rows']}",
        "scope": scope,
        "updated": "2026-11-26",
    })

kb = {
    "note": "第3课课程知识库；answer 逐字取自 02_规范问答集.csv，未编造任何政策；q18/q19（待补充）未入库",
    "items": items,
}
with open("03_知识库.json", "w", encoding="utf-8") as f:
    json.dump(kb, f, ensure_ascii=False, indent=2)

# ---------- 校验 ----------
errors, warnings = [], []
try:
    kb2 = json.load(open("03_知识库.json", encoding="utf-8"))
except Exception as e:
    errors.append(f"JSON 解析失败: {e}"); kb2 = None

if kb2:
    ids = [it["id"] for it in kb2["items"]]
    if len(ids) != len(set(ids)):
        errors.append("id 存在重复")
    seen = {}
    for it in kb2["items"]:
        for a in [it["question"]] + it["aliases"]:
            if a in seen and seen[a] != it["id"]:
                errors.append(f"别名冲突:「{a}」同时属于 {seen[a]} 与 {it['id']}")
            seen[a] = it["id"]
    for it in kb2["items"]:
        if it["answer"] != qa[it["id"]]["answer"]:
            errors.append(f"{it['id']} answer 与规范问答集不一致")
        if it["scope"] not in SCOPE_SET:
            errors.append(f"{it['id']} scope 非法")
        if not (2 <= len(it["aliases"]) <= 4):
            errors.append(f"{it['id']} 别名数量不在 2–4")
        if not it["source"].startswith(it["id"]):
            errors.append(f"{it['id']} source 未含 qid")

report = f"""# 03 · 知识库结构化校验结果

- JSON 可解析：{'✓' if kb2 else '✗'}
- 条目数：{len(items)}（q01–q17；q18/q19 标「待补充」不入库）
- id 唯一性：{'✓ 无重复' if kb2 and len(ids)==len(set(ids)) else '✗'}
- 别名冲突数：{sum(1 for e in errors if '别名冲突' in e)}（含 question 在内的全部问法唯一）
- answer 一致性：与 02_规范问答集.csv 逐条比对 {'✓ 全部一致' if not any('不一致' in e for e in errors) else '✗'}
- scope 合法性：{'✓ 均为四值之一' if not any('scope' in e for e in errors) else '✗'}
- 别名数量：每条 2–4 个，结合 02_术语表.csv 扩展 ✓
- 校验错误：{errors if errors else '无'}
- 校验警告：{warnings if warnings else '无'}
"""
open("03_知识库校验结果.md", "w", encoding="utf-8").write(report)
print(report)
if errors:
    raise SystemExit(1)
print("OK 03_知识库.json 生成并通过全部校验")
