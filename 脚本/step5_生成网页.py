# -*- coding: utf-8 -*-
"""步骤5：生成单文件 06_问答助手.html。
知识库与规则直接内嵌自 03_知识库.json 与 05_规则配置.json，匹配逻辑与 Python 评测脚本完全同口径。"""
import json, pathlib

kb = json.load(open("03_知识库.json", encoding="utf-8"))
cfg = json.load(open("05_规则配置.json", encoding="utf-8"))

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>课程问答助手 · 第3课制作</title>
<style>
:root{--c1:#3757d6;--c2:#eef2ff;--ok:#0f8a4d;--warn:#b45309;--ref:#b91c1c;--bd:#dbe2f0;--tx:#1f2430;--mut:#6b7280}
*{box-sizing:border-box}
body{margin:0;font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;color:var(--tx);background:#f6f8fc}
.wrap{max-width:720px;margin:0 auto;padding:24px 16px 40px}
header{background:linear-gradient(135deg,var(--c1),#6b7ff0);color:#fff;border-radius:14px;padding:22px 20px;margin-bottom:18px}
header h1{margin:0 0 6px;font-size:22px}
header p{margin:0;opacity:.85;font-size:13px}
.card{background:#fff;border:1px solid var(--bd);border-radius:12px;padding:16px;margin-bottom:14px}
.ask{display:flex;gap:10px}
.ask input{flex:1;padding:12px 14px;border:1px solid var(--bd);border-radius:10px;font-size:15px;outline:none}
.ask input:focus{border-color:var(--c1)}
.ask button{padding:12px 22px;border:0;border-radius:10px;background:var(--c1);color:#fff;font-size:15px;cursor:pointer}
.ask button:hover{opacity:.9}
.examples{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.examples button{padding:7px 12px;font-size:13px;border:1px solid var(--bd);background:var(--c2);color:var(--c1);border-radius:999px;cursor:pointer}
.examples button:hover{background:#dde5ff}
.result{margin-top:4px}
.badge{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;margin-bottom:8px}
.badge.answer{background:#e7f6ee;color:var(--ok)}
.badge.refuse{background:#fdeaea;color:var(--ref)}
.badge.tie{background:#fff4e0;color:var(--warn)}
.ans{font-size:15px;line-height:1.7;white-space:pre-wrap}
.meta{margin-top:10px;padding-top:10px;border-top:1px dashed var(--bd);font-size:12.5px;color:var(--mut);line-height:1.9}
.meta b{color:var(--tx)}
.cand{border:1px solid var(--bd);border-radius:10px;padding:12px;margin-top:8px}
footer{font-size:12px;color:var(--mut);text-align:center;margin-top:22px;line-height:1.8}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>📚 课程问答助手</h1>
  <p>《人工智能工具应用实践》课程 FAQ · 越界检测 → 本地匹配 → 阈值拒答</p>
</header>

<div class="card">
  <div class="ask">
    <input id="q" placeholder="输入课程相关问题，例如：课件在哪里下载" onkeydown="if(event.key==='Enter')ask()">
    <button onclick="ask()">提问</button>
  </div>
  <div class="examples" id="ex"></div>
</div>

<div class="card result" id="out" hidden></div>

<footer>基于本地课堂 FAQ，不连接外部大模型<br>知识库 __KB_N__ 条 · 拒答规则 8 条 · 低置信度阈值 __TH__ · 单文件零依赖</footer>
</div>

<script>
const KB = __KB__;
const CFG = __CFG__;
const TH = CFG.match_threshold;
const RULES = CFG.refusal_rules;
const COURSE_TERMS = (RULES.find(r=>r.rule_id==="V08").course_terms_hint||"").split(",").filter(Boolean);

// ---------- 与 Python 评测脚本完全同口径的匹配逻辑 ----------
function norm(s){return s.toLowerCase().replace(/[\s，。？?！!、,\.·（）()\[\]"'「」]/g,"")}
function bigrams(s){const a=new Set();for(let i=0;i<s.length-1;i++)a.add(s.slice(i,i+2));return a}
function containment(qb,cb){if(qb.size===0)return 0;let hit=0;qb.forEach(b=>{if(cb.has(b))hit++});return hit/qb.size}
function tagBonus(qn,item){let b=0;for(const t of item.tags){if(qn.includes(norm(t)))b+=0.05}return Math.min(b,0.1)}

function detectRefusal(qn){
  for(const r of RULES){
    const kw=(r.keywords||[]).find(k=>qn.includes(norm(k)));
    if(!kw)continue;
    if(r.rule_id==="V01"&&(r.exemption||"")){
      const ex=["workbuddy","trae","deepseek","工具","可选","安装","装"];
      if(ex.some(e=>qn.includes(e)))continue;
    }
    if(r.rule_id==="V08"){
      if(qn.includes(norm(kw)))return {r,kw};
      if(qn.length<4&&!COURSE_TERMS.some(t=>qn.includes(norm(t))))return {r,kw:null};
      continue;
    }
    return {r,kw};
  }
  return null;
}

function answer(qRaw){
  const qn=norm(qRaw);
  if(!qn)return {type:"empty"};
  // ① 越界检测（命中即拒答，不进入匹配）
  const ref=detectRefusal(qn);
  if(ref)return {type:"refuse",rule:ref.r.rule_id,category:ref.r.category,kw:ref.kw,msg:ref.r.message};
  // ② 匹配打分
  const qb=bigrams(qn);
  const scored=[];
  for(const it of KB.items){
    const cands=[it.question].concat(it.aliases);
    let best=0,bestCand="";
    for(const c of cands){
      const s=containment(qb,bigrams(norm(c)));
      if(s>best){best=s;bestCand=c}
    }
    const final=Math.min(1,best+tagBonus(qn,it));
    if(final>0)scored.push({it,final,bestCand});
  }
  scored.sort((a,b)=>b.final-a.final);
  if(scored.length===0||scored[0].final<TH)
    return {type:"lowconf",msg:CFG.low_confidence_message,top:scored[0]?scored[0].final:0};
  // ③ 并列最高分
  const top=scored[0].final;
  const ties=scored.filter(s=>s.final===top).slice(0,2);
  if(ties.length>=2)return {type:"tie",cands:ties};
  return {type:"answer",it:scored[0].it,score:top,cand:scored[0].bestCand};
}

// ---------- 界面 ----------
const EX=["课件在哪里下载","PPT 在哪拿","练习资源包怎么拿","我的成绩是多少","能不能帮我写作业","今天天气怎么样"];
const exDiv=document.getElementById("ex");
EX.forEach(t=>{const b=document.createElement("button");b.textContent=t;b.onclick=()=>{document.getElementById("q").value=t;ask()};exDiv.appendChild(b)});

function esc(s){const d=document.createElement("div");d.textContent=s;return d.innerHTML}
function ask(){
  const q=document.getElementById("q").value.trim();
  const out=document.getElementById("out");
  const r=answer(q);
  let h="";
  if(r.type==="empty"){h='<span class="badge refuse">空输入</span><div class="ans">请输入问题后再提问。</div>';}
  else if(r.type==="refuse"){
    h=`<span class="badge refuse">🚫 拒答 · 命中规则 ${r.rule}（${esc(r.category)}${r.kw?"，关键词「"+esc(r.kw)+"」":""}）</div>
       <div class="ans">${esc(r.msg)}</div>`;}
  else if(r.type==="lowconf"){
    h=`<span class="badge refuse">🤷 低置信度拒答（最高得分 ${r.top.toFixed(2)} &lt; 阈值 ${TH}）</div>
       <div class="ans">${esc(r.msg)}</div>`;}
  else if(r.type==="tie"){
    h=`<span class="badge tie">⚠️ 并列最高分（得分 ${r.cands[0].score.toFixed(2)}）· 可能需要人工确认</div>`;
    r.cands.forEach(c=>{h+=`<div class="cand"><div class="ans">${esc(c.it.answer)}</div>
      <div class="meta">条目 <b>${c.it.id}</b> · 得分 <b>${c.final.toFixed(2)}</b> · 命中「${esc(c.bestCand)}」 · 来源：${esc(c.it.source)}</div></div>`;});
  } else {
    h=`<span class="badge answer">✅ 已命中知识条目</span>
       <div class="ans">${esc(r.it.answer)}</div>
       <div class="meta">条目 <b>${r.it.id}</b> · 匹配得分 <b>${r.score.toFixed(2)}</b>（阈值 ${TH}）· 命中问法「<b>${esc(r.cand)}</b>」<br>
       来源：${esc(r.it.source)} · 范围：${esc(r.it.scope)} · 更新：${esc(r.it.updated)}</div>`;
  }
  out.innerHTML=h;out.hidden=false;
}
</script>
</body>
</html>
"""

html = (TEMPLATE
        .replace("__KB__", json.dumps(kb, ensure_ascii=False))
        .replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
        .replace("__KB_N__", str(len(kb["items"])))
        .replace("__TH__", str(cfg["match_threshold"])))

with open("06_问答助手.html", "w", encoding="utf-8") as f:
    f.write(html)
print("OK 06_问答助手.html 生成，大小", len(html.encode("utf-8")), "bytes，知识库", len(kb["items"]), "条")
