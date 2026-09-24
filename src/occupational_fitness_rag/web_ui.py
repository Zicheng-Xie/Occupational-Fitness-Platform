"""Small browser client for text-file assessments."""

ASSESSMENT_UI = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>职业适任评估</title>
  <style>
    :root{color-scheme:light;--bg:#f4f7f6;--card:#fff;--ink:#18221f;--muted:#65716d;--line:#dfe7e3;--green:#176b52;--soft:#edf6f2;--amber:#8a5b12;--red:#a33b35;--shadow:0 12px 35px rgba(22,45,36,.07)}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}button,input{font:inherit}button{cursor:pointer}.shell{max-width:980px;margin:auto;padding:52px 24px 70px}.top{margin-bottom:30px}.eyebrow{color:var(--green);font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}h1{font-size:36px;line-height:1.2;margin:8px 0 10px;letter-spacing:-.04em}.lead{color:var(--muted);margin:0;max-width:650px}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}.input-card{padding:28px}.drop{display:grid;place-items:center;text-align:center;min-height:220px;border:1.5px dashed #adc1b8;border-radius:14px;background:#fbfdfc;padding:28px;transition:.2s}.drop.drag{border-color:var(--green);background:var(--soft)}.drop strong{font-size:18px}.drop p{color:var(--muted);margin:5px 0 20px}.pick{display:inline-block;background:var(--ink);color:white;border:0;border-radius:10px;padding:10px 18px}.file-meta{margin-top:14px;color:var(--green);font-weight:600}.actions{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-top:18px}.case-id{display:flex;align-items:center;gap:9px;color:var(--muted);font-size:13px}.case-id input{width:190px;border:1px solid var(--line);border-radius:9px;padding:9px 11px;color:var(--ink)}.run{border:0;border-radius:10px;padding:11px 22px;background:var(--green);color:white;font-weight:700}.run:disabled{opacity:.45;cursor:not-allowed}.status{margin:18px 2px 0;color:var(--muted);min-height:24px}.status.error{color:var(--red)}.results{margin-top:24px}.summary{padding:26px 28px;display:grid;grid-template-columns:1fr auto;gap:22px;align-items:start}.label{font-size:12px;color:var(--muted);font-weight:650}.verdict{font-size:27px;font-weight:750;letter-spacing:-.03em;margin:5px 0 8px}.outcome{color:var(--muted)}.pill{border-radius:99px;padding:7px 12px;font-size:12px;font-weight:750;background:var(--soft);color:var(--green)}.pill.red{background:#fbecea;color:var(--red)}.pill.amber{background:#fff4df;color:var(--amber)}.section{margin-top:18px;padding:24px 28px}.section h2{font-size:17px;margin:0 0 16px}.reason{padding:14px 0;border-top:1px solid var(--line)}.reason:first-of-type{border-top:0}.reason strong{font-size:13px}.reason p{margin:3px 0 0;color:#46524e}.quote{margin:12px 0 0;padding:13px 16px;border-left:3px solid #82ad9c;background:#f6faf8;border-radius:0 9px 9px 0;white-space:pre-wrap}.quote-meta{font-size:12px;color:var(--muted);margin-top:7px}.empty{color:var(--muted);font-size:14px}.notice{margin-top:18px;color:var(--muted);font-size:12px}.raw summary{cursor:pointer;color:var(--muted);font-size:13px}.raw pre{overflow:auto;background:#17201d;color:#dce8e3;border-radius:10px;padding:16px;font:12px/1.6 ui-monospace,monospace;max-height:360px}.hidden{display:none!important}@media(max-width:640px){.shell{padding:28px 14px 48px}h1{font-size:29px}.input-card,.summary,.section{padding:20px}.actions,.summary{display:block}.case-id{margin-bottom:14px}.run{width:100%}.pill{display:inline-block;margin-top:14px}}
  </style>
</head>
<body><main class="shell">
  <header class="top"><div class="eyebrow">Occupational Fitness</div><h1>职业适任评估</h1><p class="lead">上传一份 TXT 记录，系统会提取可追溯事实，并清晰呈现评估结论与逐字原文依据。</p></header>
  <section class="card input-card" aria-labelledby="upload-title">
    <div class="drop" id="drop"><div><strong id="upload-title">拖放 TXT 文件到这里</strong><p>文件仅提交到当前评估服务，最大 100 KB</p><label class="pick" for="file">选择文件</label><input class="hidden" id="file" type="file" accept=".txt,text/plain"><div class="file-meta" id="file-meta"></div></div></div>
    <div class="actions"><label class="case-id">案例编号 <input id="case-id" maxlength="100" placeholder="自动取自文件名"></label><button class="run" id="run" disabled>开始评估</button></div>
    <div class="status" id="status" role="status" aria-live="polite"></div>
  </section>
  <div class="results hidden" id="results">
    <section class="card summary"><div><div class="label">评估结论</div><div class="verdict" id="verdict"></div><div class="outcome" id="outcome"></div></div><span class="pill" id="pill"></span></section>
    <section class="card section"><h2>判断依据</h2><div id="reasons"></div></section>
    <section class="card section"><h2>病例原文引用</h2><div id="case-quotes"></div></section>
    <section class="card section"><h2>指南原文引用</h2><div id="guide-quotes"></div></section>
    <section class="card section raw"><details><summary>查看完整技术数据（JSON）</summary><pre id="raw"></pre></details></section>
    <p class="notice">本结果为临床审核草稿，不构成最终驾驶许可或雇佣决定。</p>
  </div>
</main>
<script>
const $=id=>document.getElementById(id), fileInput=$('file'), drop=$('drop'), run=$('run'); let selectedFile=null;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function selectFile(file){if(!file)return;if(!file.name.toLowerCase().endsWith('.txt'))return fail('请选择 .txt 文件。');if(file.size>100000)return fail('文件超过 100 KB，无法提交。');selectedFile=file;$('file-meta').textContent=`${file.name} · ${(file.size/1024).toFixed(1)} KB`;$('case-id').value=(file.name.replace(/\.txt$/i,'').replace(/[^A-Za-z0-9_.-]/g,'-').slice(0,100)||'CASE-001');run.disabled=false;$('status').textContent='';}
function fail(message){$('status').textContent=message;$('status').className='status error'}
fileInput.addEventListener('change',e=>selectFile(e.target.files[0]));
['dragenter','dragover'].forEach(name=>drop.addEventListener(name,e=>{e.preventDefault();drop.classList.add('drag')}));
['dragleave','drop'].forEach(name=>drop.addEventListener(name,e=>{e.preventDefault();drop.classList.remove('drag')}));
drop.addEventListener('drop',e=>selectFile(e.dataTransfer.files[0]));
const outcomeLabels={meets_unconditional_standard:'符合无条件标准',may_meet_conditional_standard:'可能符合有条件标准，需进一步审核',temporarily_unfit:'暂时不适合驾驶',does_not_meet_standard:'不符合标准',insufficient_information:'信息不足，暂无法完成评估'};
function classification(r){if(r.has_red_flag)return['发现红旗风险','RED FLAG','red'];if(r.assessment_outcome==='insufficient_information'||r.missing_information?.length)return['需要补充信息','NEEDS MORE INFORMATION','amber'];return['未发现红旗风险','NO RED FLAG',''];}
function quoteBlock(text,meta=''){return `<blockquote class="quote">${esc(text)}</blockquote>${meta?`<div class="quote-meta">${esc(meta)}</div>`:''}`}
function render(data){const r=data.rule_result,[verdict,pill,kind]=classification(r);$('verdict').textContent=verdict;$('outcome').textContent=outcomeLabels[r.assessment_outcome]||r.outcome_label||r.assessment_outcome;$('pill').textContent=pill;$('pill').className=`pill ${kind}`;
  const rules=r.red_flags?.length?r.red_flags:(r.triggered_rules||[]);$('reasons').innerHTML=rules.length?rules.map(x=>`<div class="reason"><strong>${esc(x.rule_id)}</strong><p>${esc(x.reason)}</p></div>`).join(''):'<p class="empty">没有触发确定性规则。</p>';
  const seen=new Set(),caseQuotes=[];for(const rule of rules){for(const q of rule.source_evidence||[]){if(!seen.has(q)){seen.add(q);caseQuotes.push(quoteBlock(q,`病例记录 · ${rule.rule_id}`))}}}if(!caseQuotes.length){for(const [field,fact] of Object.entries(data.structured_case.facts||{})){for(const e of fact.evidence||[]){if(!seen.has(e.quote)){seen.add(e.quote);caseQuotes.push(quoteBlock(e.quote,`病例记录第 ${e.line_start||'?'} 行 · ${field}`))}}}}$('case-quotes').innerHTML=caseQuotes.join('')||'<p class="empty">没有可核验的病例原文引用。</p>';
  const citations=[];for(const item of data.evidence_pack.evidence_items||[]){for(const c of item.citations||[]){if(!seen.has('guide:'+c.source_id)){seen.add('guide:'+c.source_id);citations.push(quoteBlock(c.source_text||c.evidence_text,`${c.document_id} · 第 ${c.printed_page} 页 · ${c.section} 节`))}}}$('guide-quotes').innerHTML=citations.join('')||'<p class="empty">当前结论没有关联的指南原文。</p>';
  $('raw').textContent=JSON.stringify(data,null,2);$('results').classList.remove('hidden');$('results').scrollIntoView({behavior:'smooth',block:'start'});
}
run.addEventListener('click',async()=>{if(!selectedFile)return;run.disabled=true;$('status').className='status';$('status').textContent='正在分析文本并核对原文依据…';$('results').classList.add('hidden');try{const text=await selectedFile.text();if(!text.trim())throw new Error('TXT 文件为空。');const response=await fetch('/assess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case_id:$('case-id').value.trim()||'CASE-001',text})});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'评估请求失败。');render(data);$('status').textContent='评估完成。'}catch(error){fail(error.message||'无法完成评估。')}finally{run.disabled=false}});
</script></body></html>'''
