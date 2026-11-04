/* Local-model proposals bound to the exact originals in the preserved report. */
(() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
  const sameCondition = (a, b) => Object.keys(b).every(k => a?.[k] === b[k]);
  const isPendingReview = record => ['queued', 'running', 'repairing'].includes(record?.status);
  const savedReview = (records, condition) => {
    const matches = records.filter(r => sameCondition(r.condition, condition));
    return matches.findLast(r => r.result) || matches.at(-1);
  };
  async function readJsonResponse(response) {
    const text = await response.text();
    let result;
    try { result = JSON.parse(text); }
    catch {
      const error = new Error('This address returned a file-server response instead of the local review API. Open the live assessment service to run the model.');
      error.code = 'wrong_service';
      throw error;
    }
    if (!response.ok) throw new Error(result.detail || response.statusText || 'Local review request failed');
    return result;
  }
  function liveReviewURL(dataset, condition, origin = 'http://127.0.0.1:8781') {
    const url = new URL('/' + encodeURIComponent(dataset) + '/index.html', origin);
    for (const [key, value] of Object.entries(condition)) url.searchParams.set(key, value);
    url.hash = 'local-model-review';
    return url.href;
  }
  function decisionSummary(result) {
    const wording = {yes: 'Yes — model proposal', no: 'No — model proposal',
      undetermined: 'Undetermined — further information required'};
    return `<h3>Model decision</h3><div class="decision">${esc(wording[result.fitness])}</div>
      <p><strong>${esc(result.outcome.replaceAll('_', ' '))}</strong></p>
      <h3>Model explanation</h3><pre>${esc(result.explanation)}</pre>`;
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {readJsonResponse, savedReview, sameCondition, liveReviewURL, decisionSummary, isPendingReview};
  }
  if (typeof document === 'undefined') return;
  const embedded = document.querySelector('#data, #dataset');
  if (!embedded) return;
  const data = JSON.parse(embedded.textContent);
  const dataset = window.fitnessReviewDataset;
  const cached = JSON.parse(document.getElementById('fitness-review-cache')?.textContent || '[]');
  const modelNames = ['llama3:8b', 'qwen3.5:4b-q4_K_M'];
  const labels = data.labels || Object.fromEntries(data.targets.flatMap(m => [
    [m, data.names[m] + ' / Original'],
    [m + '__protected_completion', data.names[m] + ' / Allocation only'],
    [m + '__literal_facets', data.names[m] + ' / Literal facets']
  ]));
  const panel = document.createElement('section');
  panel.id = 'local-model-review';
  panel.innerHTML = `
    <style>
      #local-model-review{scroll-margin-top:20px;border-top:3px solid #2a576e}
      #local-model-review .review-controls{display:flex;gap:14px;flex-wrap:wrap;align-items:end}
      #local-model-review label{display:inline-flex;flex-direction:column;gap:6px;font-size:12px}
      #local-model-review button{cursor:pointer;background:#214e68;color:white;padding:10px 16px}
      #local-model-review button:disabled{opacity:.5;cursor:wait}
      #local-model-review pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.7 Segoe UI,Arial,sans-serif}
      #local-model-review .decision{font-size:24px;font-weight:650;margin:12px 0}
      #local-model-review .review-warning{padding:12px;border-left:3px solid #b08232;background:#fbf6eb}
      #local-model-review .review-meta{color:#61748a;font-size:12px}
      #local-model-review .review-check{border-top:1px solid #dce4ed;padding:12px 0}
      #local-model-review blockquote{white-space:pre-wrap;overflow-wrap:anywhere}
    </style>
    <h2>Local-model fitness assessment</h2>
    <p>The original nurse note plus the actual Top-K guideline originals from the selected
    method are sent to the local model. This is a provisional proposal for the selected scope;
    it does not replace clinical review or the production rule result.</p>
    <div class="review-controls">
      <label>Case / module<select id="jr-scope"></select></label>
      <label>Retrieval method / variant<select id="jr-method"></select></label>
      <label>Original evidence<select id="jr-k"><option value="5">Top 5</option><option value="10">Top 10</option></select></label>
      <label>Local decision model<select id="jr-model"></select></label>
      <label>Evidence policy<select id="jr-policy"><option value="strict_topk">Exact Top K only</option>
        <option value="explicit_references">Top K + explicit section references</option></select></label>
      <button id="jr-run">Assess selected evidence</button>
      <button id="jr-all">Assess all methods for this scope</button>
      <button id="jr-retry" hidden>Retry failed assessment</button>
    </div>
    <p><label>Previously generated model decisions<select id="jr-saved"></select></label></p>
    <p><label style="flex-direction:row"><input type="checkbox" id="jr-auto" checked>
      Assess automatically when the selected case, method, Top K or model changes</label></p>
    <p class="review-meta">Yes: requirements supported. No: current restriction supported.
    Undetermined: decisive facts or applicable evidence are missing. A conditional outcome
    retains its conditions. Reference-following is a separate evidence condition and never
    changes the original ranking or retrieval metrics.</p>
    <p id="jr-connection"></p>
    <p><a id="jr-live" target="_blank" rel="noopener">Open live assessment for this exact selection</a>
      · <button id="jr-reconnect">Reconnect local service</button></p>
    <div id="jr-output" aria-live="polite"></div>
    <p><a href="/refinement/index.html#local-model-review">Five-method refinement review</a> ·
      <a href="/ten-methods/index.html#local-model-review">All ten preserved methods</a></p>`;
  const anchor = document.getElementById('cases') || document.getElementById('case-view')?.closest('section');
  if (anchor) anchor.after(panel);
  else document.querySelector('main').append(panel);
  const el = id => document.getElementById('jr-' + id);
  const caseIds = [...new Set(data.queries.map(q => q.case_id))];
  el('scope').innerHTML = caseIds.map(cid => {
    const scopes = data.queries.filter(q => q.case_id === cid);
    return (scopes.length > 1 ? `<option value="CASE:${esc(cid)}">${esc(cid)} / All requested modules</option>` : '') +
      scopes.map(q => `<option value="${esc(q.query_id)}">${esc(q.case_id + ' / ' + q.module)}</option>`).join('');
  }).join('');
  el('method').innerHTML = Object.entries(labels).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('');
  el('model').innerHTML = modelNames.map(m => `<option>${esc(m)}</option>`).join('');
  let revision = 0;
  let connected = false;
  let timer;
  let applying = false;
  let activeReview = null;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const value = () => ({dataset, query_id: el('scope').value, method: el('method').value,
    model: el('model').value, top_k: Number(el('k').value), evidence_mode: el('policy').value});
  const sourceLink = (p, label) => `<a target="_blank" rel="noopener" href="evidence_guide.pdf#page=${p}">${esc(label)}</a>`;
  function render(record) {
    activeReview = record;
    el('retry').hidden = !record || record.status !== 'failed';
    if (!record) {
      el('output').innerHTML = `<p>No saved model decision for this exact selection yet.
        Choose a previously generated decision above, or open the live assessment service.</p>`;
      return;
    }
    const p = record.payload, r = record.result;
    let text = `<p class="review-meta">${esc(record.status)} · ${esc(record.condition.model)} ·
      ${esc(p.assessment_scope.join(', '))} · ${p.guideline_evidence.length} whole originals supplied
      ${record.seconds == null ? '' : ' · ' + record.seconds.toFixed(1) + ' seconds'}</p>`;
    if (record.error) {
      text += `<p class="review-warning">${esc(record.user_message ||
        'The model output failed validation. No fitness decision was accepted. Retry this assessment; the original failed response remains in the audit.')}</p>
        <details><summary>Technical validation details</summary><pre>${esc(record.error)}</pre></details>`;
    }
    if (isPendingReview(record)) text += `<p class="review-warning">${
      record.status === 'queued' ? 'Waiting for the local model worker. Calls run one at a time.' :
      record.status === 'repairing' ? 'The first response had invalid references. One validation repair is running with the same local model, original note and exact retrieved evidence.' :
      'The local model is assessing the original note and supplied evidence. The decision and explanation will appear here automatically.'}</p>`;
    if (record.recovery_note) text += `<p class="review-meta">${esc(record.recovery_note)}</p>`;
    if (r) {
      text += decisionSummary(r);
      if (r.validation_warnings.length) text += `<p class="review-warning">${r.validation_warnings.map(esc).join('<br>')}</p>`;
      text += `<p class="review-meta">Selected patient paragraphs and guideline passages are resolved to
        the actual originals by the application. Their clinical support and conclusion require review.</p>`;
      if (r.missing_information.length) text += '<p><strong>Decisive missing information</strong></p><ul>' +
        r.missing_information.map(x => `<li>${esc(x)}</li>`).join('') + '</ul>';
      text += '<details open><summary>Evidence-to-patient checks</summary>' + r.checks.map(c => `
        <div class="review-check"><strong>${esc(c.finding.replaceAll('_', ' '))}</strong> · ${esc(c.applicability)}
        <p>${esc(c.comment)}</p><p>Patient wording:</p><blockquote>${esc(c.patient_quote || 'Not documented')}</blockquote>
        <p>Guideline wording:</p><blockquote>${esc(c.guideline_quote)}</blockquote>
        <p>${sourceLink(c.pdf_page, c.source_id + ' · Section ' + c.section + ' · PDF ' + c.pdf_page)}</p></div>`).join('') + '</details>';
    }
    const gaps = p.cross_reference_audit.filter(l => l.status !== 'available_units_supplied');
    text += `<details${gaps.length ? ' open' : ''}><summary>Cross-chapter dependency audit · ${gaps.length} unresolved links</summary>`;
    text += p.cross_reference_audit.length ? p.cross_reference_audit.map(l => `<p>${esc(l.from_source_id)} →
      Section ${esc(l.section)}: <strong>${esc(l.status.replaceAll('_', ' '))}</strong>${l.missing_target_ids.length ?
      '<br>Not supplied: ' + esc(l.missing_target_ids.join(', ')) : ''}</p>`).join('') : '<p>No explicit section dependency recorded in these originals.</p>';
    text += '</details><details><summary>Exact model input: original note and all supplied passages</summary>' +
      `<h3>Original nurse note</h3><pre>${esc(p.nurse_note)}</pre>` + p.guideline_evidence.map(s => `
      <h3>Slot ${s.source_slot} · ${esc(s.role)} · ${esc(s.source_id)}</h3>
      <p>${sourceLink(s.pdf_page, 'Section ' + s.section + ' · PDF ' + s.pdf_page)}</p><pre>${esc(s.source_text)}</pre>`).join('') + '</details>';
    text += `<details><summary>Reproducibility record</summary><pre>${esc(JSON.stringify({id: record.id,
      model_digest: record.model_digest, condition: record.condition, payload_sha256: record.payload_sha256,
      prompt_tokens: record.raw_response?.prompt_eval_count, output_tokens: record.raw_response?.eval_count,
      retry_of: record.retry_of, model_calls: record.model_calls,
      attempts: record.attempts?.map(a => ({number: a.number, status: a.status,
        seconds: a.seconds, validation_error: a.validation_error}))}, null, 2))}</pre></details>`;
    if (!r && record.raw_response?.message?.content) text += `<details><summary>Unaccepted model response — audit only</summary>
      <pre>${esc(record.raw_response.message.content)}</pre></details>`;
    el('output').innerHTML = text;
  }
  async function api(path, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(path, {cache: 'no-store', signal: controller.signal,
        ...(body ? {method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(body)} : {})});
      return await readJsonResponse(response);
    } finally { clearTimeout(timeout); }
  }
  async function assess(retryId = null) {
    const seq = ++revision, condition = value();
    const saved = savedReview(cached, condition);
    render(saved);
    if (!connected) { el('live').click(); return; }
    el('run').disabled = true;
    try {
      let record = typeof retryId === 'string' ? await api('/api/reviews/' + retryId + '/retry', {}) :
        await api('/api/reviews', condition);
      while (seq === revision) {
        render(record);
        if (!isPendingReview(record)) {
          const prior = cached.findIndex(r => r.id === record.id);
          if (prior >= 0) cached[prior] = record; else cached.push(record);
          savedOptions();
          break;
        }
        await sleep(1800);
        if (seq !== revision) break;
        record = await api('/api/reviews/' + record.id);
      }
    } catch (error) {
      if (seq === revision) {
        render(savedReview(cached, condition));
        el('connection').textContent = error.message + ' Saved model decisions remain available.';
      }
    } finally {
      if (seq === revision) el('run').disabled = false;
    }
  }
  function changed() {
    ++revision;
    el('run').disabled = false;
    clearTimeout(timer);
    render(savedReview(cached, value()));
    el('live').href = liveReviewURL(dataset, value(), window.fitnessReviewLiveOrigin);
    el('saved').value = savedReview(cached, value())?.id || '';
    if (el('auto').checked && connected) timer = setTimeout(assess, 500);
  }
  function sync() {
    if (applying) return;
    const cid = document.getElementById('case')?.value;
    const module = document.getElementById('module')?.value;
    const scopes = data.queries.filter(q => q.case_id === cid);
    const q = scopes.find(q => q.module === module) || scopes[0];
    if (q) el('scope').value = scopes.length > 1 && (!module || module === 'all') ? 'CASE:' + cid : q.query_id;
    const method = document.getElementById('method')?.value;
    if (method && labels[method]) el('method').value = method;
    const limit = document.getElementById('limit')?.value;
    if (limit) el('k').value = limit;
    changed();
  }
  ['scope', 'method', 'k', 'model', 'policy'].forEach(id => el(id).addEventListener('change', changed));
  ['case', 'method', 'module', 'limit'].forEach(id => document.getElementById(id)?.addEventListener('change', sync));
  el('run').addEventListener('click', assess);
  el('retry').addEventListener('click', () => {
    if (activeReview?.status === 'failed') assess(activeReview.id);
  });
  el('all').addEventListener('click', async () => {
    if (!connected) { el('live').click(); return; }
    el('all').disabled = true;
    try {
      for (const method of Object.keys(labels)) {
        await api('/api/reviews', {...value(), method});
      }
      el('connection').textContent = 'All methods queued for this exact case/module, Top K, model and evidence policy. Calls run one at a time.';
      await assess();
    } catch (error) { el('connection').textContent = error.message; }
    finally { el('all').disabled = false; }
  });
  function savedOptions() {
    el('saved').innerHTML = '<option value="">Select a saved decision and explanation</option>' +
      cached.filter(r => r.condition.dataset === dataset && r.result).map(r =>
        `<option value="${esc(r.id)}">${esc(r.case_id + ' / ' + r.module + ' · ' +
          (labels[r.condition.method] || r.condition.method) + ' · Top ' + r.condition.top_k +
          ' · ' + r.condition.model)}</option>`).join('');
  }
  function selectCondition(condition) {
    if (!condition || condition.dataset !== dataset) return;
    applying = true;
    const q = data.queries.find(q => q.query_id === condition.query_id);
    const cid = q?.case_id || condition.query_id.replace(/^CASE:/, '');
    const mainCase = document.getElementById('case');
    if (mainCase) { mainCase.value = cid; mainCase.dispatchEvent(new Event('change')); }
    const mainMethod = document.getElementById('method');
    if (mainMethod) {
      mainMethod.value = condition.method.split('__')[0];
      mainMethod.dispatchEvent(new Event('change'));
    }
    const mainModule = document.getElementById('module');
    const requestedModule = q?.module || 'all';
    if (mainModule && [...mainModule.options].some(o => o.value === requestedModule)) {
      mainModule.value = requestedModule;
      mainModule.dispatchEvent(new Event('change'));
    }
    const mainLimit = document.getElementById('limit');
    if (mainLimit) { mainLimit.value = condition.top_k; mainLimit.dispatchEvent(new Event('change')); }
    for (const [id, key] of [['scope', 'query_id'], ['method', 'method'], ['k', 'top_k'],
      ['model', 'model'], ['policy', 'evidence_mode']]) el(id).value = condition[key];
    applying = false;
    changed();
  }
  el('saved').addEventListener('change', () => {
    const saved = cached.find(r => r.id === el('saved').value);
    if (saved) selectCondition(saved.condition);
  });
  savedOptions();
  sync();
  const search = new URLSearchParams(location.search);
  if (search.has('query_id')) selectCondition({dataset,
    query_id: search.get('query_id'), method: search.get('method') || el('method').value,
    top_k: Number(search.get('top_k') || 5), model: search.get('model') || el('model').value,
    evidence_mode: search.get('evidence_mode') || 'strict_topk'});
  async function connect() {
    el('connection').textContent = 'Connecting to the local assessment service…';
    try {
      const result = await api('/api/review-models');
      if (result.service !== 'occupational-fitness-evidence-review') {
        throw new Error('This preview does not provide the model review API. Open the live assessment link.');
      }
      connected = true;
      const selectedModel = el('model').value;
      el('model').innerHTML = modelNames.filter(m => result.models.includes(m)).map(m => `<option>${esc(m)}</option>`).join('');
      if (result.models.includes(selectedModel)) el('model').value = selectedModel;
      el('run').textContent = 'Assess selected evidence';
      el('connection').textContent = 'Local Ollama connected. Saved decisions are shown immediately; new conditions are assessed automatically.';
      changed();
    } catch (error) {
      connected = false;
      el('run').textContent = 'Open live assessment';
      el('connection').textContent = error.message + ' Saved decisions and explanations can still be viewed above.';
      render(savedReview(cached, value()));
    }
  }
  el('reconnect').addEventListener('click', connect);
  if (location.protocol === 'file:') {
    el('connection').textContent = 'Offline snapshot: saved model reviews are available. For new local-model calls, run scripts/start_retrieval_review.ps1 and open http://127.0.0.1:8781/';
    el('run').textContent = 'Open live assessment';
  } else {
    connect();
  }
})();
