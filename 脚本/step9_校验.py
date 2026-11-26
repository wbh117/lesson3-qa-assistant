# -*- coding: utf-8 -*-
"""步骤9：自检校验。校验文件树、JSON 可解析、评测结果 21 行（表头+20 题）、评分表 6 项。"""
import csv, json, os

ok, fail = [], []
def check(name, cond, detail=""):
    (ok if cond else fail).append(f"{'✓' if cond else '✗'} {name} {detail}")

need = ["01_语料体检报告.md","02_规范问答集.csv","03_知识库.json","03_知识库校验结果.md",
        "04_拒答规则.md","05_规则配置.json","06_问答助手.html","07_评测报告.md",
        "07_评测报告_修订前.md","08_评测结果.csv","08_评测结果_修订前.csv",
        "09_维护与对接说明.md","10_制作说明.md","自评得分表.md"]
for f in need:
    check(f"文件存在 {f}", os.path.exists(f))

for jf in ["03_知识库.json","05_规则配置.json","素材包/05_知识库模板.json"]:
    try:
        json.load(open(jf, encoding="utf-8")); check(f"JSON 可解析 {jf}", True)
    except Exception as e:
        check(f"JSON 可解析 {jf}", False, str(e))

rows = list(csv.reader(open("08_评测结果.csv", encoding="utf-8-sig")))
check("评测结果 21 行（表头+20 题）", len(rows) == 21, f"实际 {len(rows)} 行")
check("评测结果 9 列", all(len(r) == 9 for r in rows), "")
check("20 题全部正确", all(r[7] == "正确" for r in rows[1:]))

html = open("06_问答助手.html", encoding="utf-8").read()
check("问答页零外部依赖（无 http/https 资源引用）", ("src=\"http" not in html and "href=\"http" not in html))
check("问答页含来源显示", "来源" in html and "source" in html)
check("问答页含拒答与阈值", "拒答" in html and "0.35" in html)
check("问答页含 6 个示例问题按钮", html.count("EX=[") == 1 and "今天天气怎么样" in html)
check("问答页含底部声明", "不连接外部大模型" in html)

kb = json.load(open("03_知识库.json", encoding="utf-8"))
ids = [i["id"] for i in kb["items"]]
check("知识库 id 唯一", len(ids) == len(set(ids)), f"{len(ids)} 条")

cfg = json.load(open("05_规则配置.json", encoding="utf-8"))
check("拒答规则 8 条", len(cfg["refusal_rules"]) == 8)
check("阈值 0.35", cfg["match_threshold"] == 0.35)

score = list(csv.reader(open("素材包/07_评分表.csv", encoding="utf-8-sig")))
check("评分表 6 个评价项目", len(score) - 1 == 6, f"实际 {len(score)-1} 项")

print("\n".join(ok))
if fail:
    print("\n".join(fail)); raise SystemExit(1)
print(f"\n全部通过：{len(ok)} 项校验 ✓")
