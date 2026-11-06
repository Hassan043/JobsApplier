'use strict';
const $ = id => document.getElementById(id);
let working = false, detailTab = 'overview';
let state = {profiles: [], records: [], statuses: []}, active = '', dirty = false, notesDirty = false, template = {}, editing = null;
const eligibilityLabel = value => ({eligible_by_declared_country:'Country allowed', review_needed:'Check eligibility', ineligible:'Ineligible'}[value] || value);
const score = a => a.ai_status === 'completed' ? a.ai_score : a.score;
const matchingOptions = () => ({provider:$('ai-provider').value, ai:$('use-ai').checked, consent:$('use-ai').checked, model:$('ai-model').value.trim(), max_jobs:Number($('max-jobs').value), max_ai_calls:Number($('ai-budget').value)});
const selectedProfiles = () => [...$('profile-options').querySelectorAll('input:checked')].map(i => i.value);
const splitValues = id => $(id).value.split(',').map(x => x.trim()).filter(Boolean);
const runSummary = r => `Ranked ${r.unique_jobs} jobs / ${r.candidate_assessments} CV matches. ${r.duplicates_skipped} duplicates skipped; ${r.jobs_outside_cap} beyond cap. AI calls: ${r.ai_calls}; failures: ${r.ai_failures}.` + (r.source_warnings.length ? ' Source notes: ' + r.source_warnings.join('; ') : '');
const key = r => r.id + ':' + r.assessment.profile_hash;
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
async function request(path, body) {
  const headers = {'X-Dashboard-Token': document.querySelector('meta[name=dashboard-token]').content};
  if (body && !(body instanceof FormData)) { body = JSON.stringify(body); headers['Content-Type'] = 'application/json'; }
  const response = await fetch(path, {method: body ? 'POST' : 'GET', headers, body});
  const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Request failed'); return result;
}
async function action(button, fn) {
  if (working) { message('A task is already running. Please wait for its bounded requests to finish.'); return; }
  working = true; const buttons = [...document.querySelectorAll('button,input,select,textarea')].map(b => [b,b.disabled]); for (const [b] of buttons) b.disabled = true; message('Working… Live sources can take up to 15s each; AI requests have individual timeouts.');
  try { await fn(); } catch (e) { message(e.message, true); } finally { working = false; for (const [b, disabled] of buttons) b.disabled = disabled; }
}
function guard() { return !(dirty || notesDirty) || window.confirm('You have an undownloaded draft or unsaved notes. Continue and discard those edits?'); }
function option(select, value, text) { const o = node('option', text); o.value = value; select.append(o); }
async function refresh() {
  state = await request('/api/state');
  const selected = new Set([...$('profile-options').querySelectorAll('input:checked')].map(i => i.value));
  const hasActiveSelection = state.profiles.some(p => !p.archived && selected.has(p.id));
  const filter = $('filter-profile').value;
  $('profile-options').replaceChildren(node('legend', 'Compare these CV profiles'));
  $('filter-profile').replaceChildren(); option($('filter-profile'), '', 'Current profiles');
  const edit = $('edit-profile').value; $('edit-profile').replaceChildren(); option($('edit-profile'), '', 'Create a new profile');
  for (const p of state.profiles) {
    const label = node('label', undefined, 'check'), input = node('input'); input.type = 'checkbox'; input.value = p.id; input.checked = !p.archived && (hasActiveSelection ? selected.has(p.id) : true); input.disabled = p.archived;
    label.append(input, document.createTextNode(p.name + (p.label ? ' / ' + p.label : '') + (p.archived ? ' (previous revision)' : ''))); $('profile-options').append(label);
    option($('filter-profile'), p.hash, p.name + (p.label ? ' / ' + p.label : '') + (p.archived ? ' (previous revision)' : ''));
    if (!p.archived) option($('edit-profile'), p.id, p.name + (p.label ? ' / ' + p.label : ''));
  }
  $('edit-profile').value = edit;
  $('ai-availability').textContent = 'Ollama: start the local server and use an installed model such as qwen3:4b. No API key required. ' + (state.ai_configured ? 'Server API key configured. Matching requires the optional AI dependency and an explicit model.' : 'Hosted OpenAI needs OPENAI_API_KEY and requirements-ai.txt.');
  if (!$('ai-model').value) $('ai-model').value = $('ai-provider').value === 'ollama' ? 'qwen3:4b' : (state.default_model || '');
  $('filter-profile').value = filter;
  const stage = $('stage').value; $('stage').replaceChildren(); option($('stage'), '', 'All stages');
  for (const s of state.statuses) option($('stage'), s, s[0].toUpperCase() + s.slice(1)); $('stage').value = stage;
  $('profile-count').textContent = state.profiles.filter(p => !p.archived).length;
  $('job-count').textContent = new Set(state.records.map(r => r.id)).size;
  $('shortlist-count').textContent = state.records.filter(r => r.status === 'shortlisted').length;
  $('applied-count').textContent = state.records.filter(r => ['applied', 'interview'].includes(r.status)).length;
  render();
}
function render() {
  const q = $('search').value.toLowerCase(), minimum = Number($('salary').value || 0);
  const currentProfiles = new Set(state.profiles.filter(p => !p.archived).map(p => p.hash));
  const rows = state.records.filter(r => {
    const a = r.assessment, j = r.job, pay = a.compensation.monthly_usd_minimum;
    return (!q || (j.title + ' ' + j.company + ' ' + j.description).toLowerCase().includes(q)) &&
      ($('filter-profile').value ? a.profile_hash === $('filter-profile').value : currentProfiles.has(a.profile_hash)) &&
      (!$('eligibility').value || a.eligibility === $('eligibility').value) &&
      (!$('stage').value || r.status === $('stage').value) &&
      (pay == null ? $('unknown-pay').checked : pay >= minimum);
  });
  rows.sort((x,y) => { if (x.assessment.eligibility === 'ineligible' && y.assessment.eligibility !== 'ineligible') return 1; if (y.assessment.eligibility === 'ineligible' && x.assessment.eligibility !== 'ineligible') return -1; if ($('sort').value === 'salary') return (y.assessment.compensation.monthly_usd_minimum ?? -1) - (x.assessment.compensation.monthly_usd_minimum ?? -1); if ($('sort').value === 'company') return x.job.company.localeCompare(y.job.company); return score(y.assessment) - score(x.assessment); });
  if (!rows.some(r => key(r) === active)) { active = rows.length ? key(rows[0]) : ''; dirty = false; }
  $('result-count').textContent = rows.length + ' CV–job matches'; $('jobs').replaceChildren();
  if (!rows.length) $('jobs').append(node('p', 'No matches to show. Import jobs or adjust your filters.', 'empty'));
  for (const r of rows) {
    const a = r.assessment, j = r.job, card = node('button', undefined, 'job-card' + (key(r) === active ? ' active' : ''));
    card.dataset.matchKey = key(r); card.type = 'button'; card.setAttribute('aria-pressed', String(key(r) === active));
    const top = node('div', undefined, 'card-top');
    const scoreBox = node('span', score(a) + '/100', 'score'); scoreBox.append(node('small', a.ai_status === 'completed' ? 'AI fit' : 'keyword fit'));
    top.append(node('span', j.company.split(/\s+/).map(x => x[0]).join('').slice(0,2).toUpperCase(), 'company-mark'), node('span', j.company, 'company-name'), scoreBox);
    const bottom = node('div', undefined, 'card-bottom'); bottom.append(node('span', eligibilityLabel(a.eligibility), 'badge ' + a.eligibility), node('span', r.status));
    const pay = a.compensation.monthly_usd_minimum;
    card.append(top, node('h3', j.title), node('div', j.location || j.workplace, 'muted'), node('div', pay == null ? (j.salary || 'Pay not confirmed') : '$' + Math.round(pay).toLocaleString() + '+ / month', 'card-pay'), node('div', a.candidate, 'card-candidate'), bottom);
    card.onclick = () => { if (!guard()) return; active = key(r); detailTab = 'overview'; dirty = false; notesDirty = false; render(); }; $('jobs').append(card);
  }
  detail(rows.find(r => key(r) === active));
}
function detail(r) {
  const box = $('detail'); box.replaceChildren();
  if (!r) { const empty = node('div', undefined, 'empty'); empty.append(node('span', '↗'), node('h3', 'Your next move starts here'), node('p', 'Add a CV and import postings, or explore the synthetic demo.')); box.append(empty); return; }
  const a = r.assessment, j = r.job;
  const heading = node('div', undefined, 'job-heading'), overview = node('section', undefined, 'detail-section'), application = node('section', undefined, 'detail-section');
  heading.append(node('span', score(a) + '/100 · ' + (a.ai_status === 'completed' ? 'AI evidence fit' : 'Keyword baseline'), 'badge'), node('h2', j.title), node('p', j.company + ' · ' + a.candidate, 'subtitle'));
  if (a.ai_status !== 'not_requested') overview.append(node('p', 'AI status: ' + a.ai_status + (a.ai_provider ? ' (' + a.ai_provider + ')' : '') + ' · Keyword baseline: ' + a.score + '/100', 'muted'));
  const currentHashes = new Set(state.profiles.filter(p => !p.archived).map(p => p.hash));
  const peers = state.records.filter(x => x.id === r.id && currentHashes.has(x.assessment.profile_hash));
  if (peers.length > 1) { const best = Math.max(...peers.map(x => x.assessment.score)); const names = peers.filter(x => x.assessment.score === best).map(x => x.assessment.candidate); overview.append(node('p', 'Top CV by keyword evidence: ' + names.join(' / ') + (names.length > 1 ? ' (tie)' : '') + '. Compare the evidence before choosing.', 'muted')); }
  const link = node('a', 'View original posting ↗'); link.href = j.source_url || j.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; heading.append(link);
  const facts = node('div', undefined, 'facts');
  for (const [label, value] of [['Work arrangement', j.workplace + ' · ' + (j.location || 'Location not supplied')], ['Eligibility', eligibilityLabel(a.eligibility)], ['Monthly USD minimum', a.compensation.monthly_usd_minimum == null ? 'Unknown / not converted' : '$' + Math.round(a.compensation.monthly_usd_minimum).toLocaleString()], ['Salary details', j.salary || [j.currency, j.salary_min, j.salary_max ? '– ' + j.salary_max : '', j.salary_period].filter(Boolean).join(' ') || 'Not supplied']]) {
    const fact = node('div'); fact.append(node('span', label), node('strong', value)); facts.append(fact);
  } overview.append(facts, node('p', a.compensation.note, 'muted'));
  for (const warning of a.warnings) overview.append(node('p', warning, 'warning'));
  overview.append(node('h3', 'Why this CV matches'));
  const evidenceMatches = a.ai_status === 'completed' ? a.ai_matches : a.matches;
  if (!evidenceMatches.length) overview.append(node('p', 'No matching skills backed by the supplied CV.', 'muted'));
  const grouped = new Map();
  for (const m of evidenceMatches) { const identity = JSON.stringify([m.evidence_id,m.candidate_quote,m.job_quote]); if (!grouped.has(identity)) grouped.set(identity, {match:m,skills:[]}); grouped.get(identity).skills.push(m.skill); }
  for (const {match:m,skills} of grouped.values()) { const e = node('div', undefined, 'evidence'), tags = node('div'); for (const skill of [...new Set(skills)]) tags.append(node('span',skill,'badge')); e.append(tags, node('p',m.candidate_quote), node('small','CV evidence: ' + m.evidence_id), node('p','Posting: ' + m.job_quote)); overview.append(e); }
  if (a.ai_status === 'completed' && a.missing_requirements.length) { overview.append(node('h3', 'Posting requirements without demonstrated evidence')); for (const excerpt of a.missing_requirements) overview.append(node('p', excerpt, 'warning')); }
  if (a.unverified_profile_skills.length) overview.append(node('p', 'Skills listed without CV evidence: ' + a.unverified_profile_skills.join(', '), 'warning'));
  const desc = node('details'), summary = node('summary', 'Read job description'); desc.append(summary, node('p', j.description, 'description')); overview.append(desc);
  application.append(node('h3', 'Prepare your application'));
  const draft = node('textarea'); draft.value = r.draft ? r.draft.text : (a.cover_letter || ''); draft.placeholder = 'Add your own verified application draft here.'; draft.setAttribute('aria-label', 'Editable cover letter'); draft.oninput = () => { dirty = true; }; application.append(draft);
  application.append(node('p', 'Review every claim. Save a draft to resume later, or download it for manual use. Each save preserves an earlier revision.', 'muted'));
  const saveDraft = node('button', 'Save draft'); saveDraft.onclick = () => action(saveDraft, async () => { const result = await request('/api/draft', {job_id:r.id, profile_hash:a.profile_hash, text:draft.value}); r.draft = {text:draft.value, revision:result.revision}; dirty = false; message('Draft revision saved privately.'); }); application.append(saveDraft);
  if (r.draft) application.append(node('p', 'Saved draft revision ' + r.draft.revision, 'muted'));
  const download = node('button', 'Download draft', 'secondary'); download.onclick = () => { const blob = new Blob([draft.value], {type:'text/plain;charset=utf-8'}), url = URL.createObjectURL(blob), anchor = node('a'); anchor.href = url; anchor.download = 'application-draft.txt'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); dirty = false; message('Draft downloaded. Review it before using.'); }; application.append(download);
  application.append(node('h3', 'Track this application'));
  const stage = node('select'); stage.setAttribute('aria-label', 'Application stage'); for (const s of state.statuses) option(stage, s, s); stage.value = r.status;
  const notes = node('textarea', undefined, 'notes'); notes.value = r.notes; notes.placeholder = 'Interview dates, follow-ups, or next steps…'; notes.setAttribute('aria-label', 'Application notes'); notes.oninput = () => { notesDirty = true; }; stage.onchange = () => { notesDirty = true; };
  const save = node('button', 'Save stage & notes'); save.onclick = () => action(save, async () => { await request('/api/status', {job_id:r.id, profile_hash:a.profile_hash, status:stage.value, notes:notes.value}); r.status = stage.value; r.notes = notes.value; notesDirty = false; $('shortlist-count').textContent = state.records.filter(x => x.status === 'shortlisted').length; $('applied-count').textContent = state.records.filter(x => ['applied','interview'].includes(x.status)).length; for (const card of $('jobs').children) { if (card.dataset.matchKey === key(r)) card.querySelector('.card-bottom').lastChild.textContent = r.status; } message('Application tracking saved locally.'); });
  application.append(stage, notes, save);
  const tabs = node('div', undefined, 'detail-tabs'); tabs.setAttribute('role','tablist'); tabs.setAttribute('aria-label','Job detail sections');
  const panels = {overview, application};
  function selectTab(name) { detailTab = name; for (const [id,panel] of Object.entries(panels)) panel.hidden = id !== name; for (const button of tabs.children) { const selected = button.dataset.tab === name; button.setAttribute('aria-selected',String(selected)); button.tabIndex = selected ? 0 : -1; } }
  for (const [id,label] of [['overview','Match overview'],['application','Application & tracking']]) {
    const button = node('button',label); button.type = 'button'; button.dataset.tab = id; button.id = 'tab-' + id; button.setAttribute('role','tab'); button.setAttribute('aria-controls','panel-' + id);
    panels[id].id = 'panel-' + id; panels[id].setAttribute('role','tabpanel'); panels[id].setAttribute('aria-labelledby',button.id);
    button.onclick = () => selectTab(id); button.onkeydown = e => { if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); const next = id === 'overview' ? 'application' : 'overview'; selectTab(next); [...tabs.children].find(b => b.dataset.tab === next).focus(); } }; tabs.append(button);
  }
  box.append(heading,tabs,overview,application); selectTab(detailTab);

}
for (const id of ['search','filter-profile','eligibility','stage','salary','unknown-pay','sort']) $(id).addEventListener('change', () => { if (guard()) { dirty = false; notesDirty = false; render(); } });
$('demo').onclick = () => { if (guard()) action($('demo'), async () => { dirty = false; const r = await request('/api/demo', {}); await refresh(); message('Synthetic demo loaded: ' + r.unique_jobs + ' opportunities. These are not real vacancies.'); }); };
$('profile-form').onsubmit = e => { e.preventDefault(); if (!guard()) return; action(e.submitter, async () => { const form = new FormData(e.target); const split = id => $(id).value.split(',').map(x => x.trim()).filter(Boolean); const data = {...(editing ? editing.data : template), name:$('candidate-name').value, profile_label:$('candidate-label').value, base_country:$('country').value.toUpperCase(), target_roles:split('roles'), skills:split('skills'), target_monthly_usd:Number($('target-pay').value), remote_only:$('remote-only').checked, open_to_relocation:$('relocation').checked, evidence:editing && $('evidence').value === editing.text ? editing.data.evidence : ($('evidence').value.trim() ? [{id:'supplied_cv',text:$('evidence').value}] : []), resume_path:''}; if (editing && form.get('cv') && form.get('cv').name) data.evidence = []; form.set('profile', JSON.stringify(data)); if (editing) form.set('previous', editing.id); await request('/api/profile', form); dirty = false; await refresh(); editing = null; $('edit-profile').value = ''; message('CV profile saved privately. Previous versions and tracking history are retained. Import or reassess jobs to use this revision.'); }); };
$('import-form').onsubmit = e => { e.preventDefault(); if (!guard()) return; action(e.submitter, async () => { const form = new FormData(e.target); form.set('profiles', JSON.stringify(selectedProfiles())); form.set('options', JSON.stringify(matchingOptions())); const r = await request('/api/import', form); dirty = false; notesDirty = false; await refresh(); $('use-ai').checked = false; message(runSummary(r)); }); };
$('collect-form').onsubmit = e => { e.preventDefault(); if (!guard()) return; action(e.submitter, async () => { const feeds = ['remotive','arbeitnow'].filter(x => $('feed-' + x).checked); const r = await request('/api/collect', {profiles:selectedProfiles(), feeds, greenhouse:splitValues('greenhouse'), lever:splitValues('lever'), queries:splitValues('queries'), options:matchingOptions()}); dirty = false; notesDirty = false; await refresh(); $('use-ai').checked = false; message(runSummary(r)); }); };
$('reassess').onclick = () => { if (!guard()) return; action($('reassess'), async () => { const r = await request('/api/reassess', {profiles:selectedProfiles(), options:matchingOptions()}); dirty = false; notesDirty = false; await refresh(); $('use-ai').checked = false; message(runSummary(r)); }); };
$('load-profile').onclick = () => action($('load-profile'), async () => {
  const id = $('edit-profile').value;
  const data = id ? await request('/api/profile-detail', {id}) : template;
  const text = (data.evidence || []).map(x => x.text).join('\n\n');
  editing = id ? {id, data, text} : null;
  $('candidate-name').value = id ? data.name : ''; $('candidate-label').value = data.profile_label || ''; $('country').value = data.base_country || 'PK';
  $('roles').value = (data.target_roles || []).join(', '); $('skills').value = (data.skills || []).join(', '); $('target-pay').value = data.target_monthly_usd || 2000;
  $('remote-only').checked = data.remote_only || false; $('relocation').checked = data.open_to_relocation !== false; $('evidence').value = text;
  $('profile-form').querySelector('input[type=file]').value = '';
  message(id ? 'Profile loaded. Saving creates a new revision; previous tracking remains available.' : 'Ready to create a new profile.');
});
$('ai-provider').onchange = () => { $('ai-model').value = $('ai-provider').value === 'ollama' ? 'qwen3:4b' : (state.default_model || ''); };
window.addEventListener('beforeunload', e => { if (dirty || notesDirty) { e.preventDefault(); e.returnValue = ''; } });
(async () => { try { template = await request('/api/template'); $('roles').value = template.target_roles.join(', '); $('skills').value = template.skills.join(', '); await refresh(); } catch(e) { message(e.message, true); } })();

const settings = $('settings-dialog');
for (const button of document.querySelectorAll('[data-panel]')) button.onclick = () => {
  for (const panel of settings.querySelectorAll('.setup > details')) { panel.classList.remove('active-panel'); panel.open = false; }
  const panel = $(button.dataset.panel); panel.classList.add('active-panel'); panel.open = true;
  $('settings-title').textContent = {'profile-panel':'CV profiles', 'import-panel':'Import & match postings', 'source-panel':'Sources & AI'}[panel.id];
  settings.showModal();
};
$('close-settings').onclick = () => settings.close();
if (window.matchMedia('(max-width:700px)').matches) document.querySelector('.filter-panel').open = false;
