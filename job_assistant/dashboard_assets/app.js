'use strict';
const $ = id => document.getElementById(id);
let state = {profiles: [], records: [], statuses: []}, active = '', dirty = false, notesDirty = false, template = {};
const eligibilityLabel = value => ({eligible_by_declared_country:'Country allowed', review_needed:'Check eligibility', ineligible:'Ineligible'}[value] || value);
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
  button.disabled = true; message('Working…');
  try { await fn(); } catch (e) { message(e.message, true); } finally { button.disabled = false; }
}
function guard() { return !(dirty || notesDirty) || window.confirm('You have an undownloaded draft or unsaved notes. Continue and discard those edits?'); }
function option(select, value, text) { const o = node('option', text); o.value = value; select.append(o); }
async function refresh() {
  state = await request('/api/state');
  const selected = new Set([...$('profile-options').querySelectorAll('input:checked')].map(i => i.value));
  const filter = $('filter-profile').value;
  $('profile-options').replaceChildren(node('legend', 'Compare these CV profiles'));
  $('filter-profile').replaceChildren(); option($('filter-profile'), '', 'All profiles');
  for (const p of state.profiles) {
    const label = node('label'), input = node('input'); input.type = 'checkbox'; input.value = p.id; input.checked = selected.size ? selected.has(p.id) : true;
    label.append(input, document.createTextNode(p.name + (p.label ? ' / ' + p.label : ''))); $('profile-options').append(label);
    option($('filter-profile'), p.hash, p.name + (p.label ? ' / ' + p.label : ''));
  }
  $('filter-profile').value = filter;
  const stage = $('stage').value; $('stage').replaceChildren(); option($('stage'), '', 'All stages');
  for (const s of state.statuses) option($('stage'), s, s[0].toUpperCase() + s.slice(1)); $('stage').value = stage;
  $('profile-count').textContent = state.profiles.length;
  $('job-count').textContent = new Set(state.records.map(r => r.id)).size;
  $('shortlist-count').textContent = state.records.filter(r => r.status === 'shortlisted').length;
  $('applied-count').textContent = state.records.filter(r => ['applied', 'interview'].includes(r.status)).length;
  render();
}
function render() {
  const q = $('search').value.toLowerCase(), minimum = Number($('salary').value || 0);
  const rows = state.records.filter(r => {
    const a = r.assessment, j = r.job, pay = a.compensation.monthly_usd_minimum;
    return (!q || (j.title + ' ' + j.company + ' ' + j.description).toLowerCase().includes(q)) &&
      (!$('filter-profile').value || a.profile_hash === $('filter-profile').value) &&
      (!$('eligibility').value || a.eligibility === $('eligibility').value) &&
      (!$('stage').value || r.status === $('stage').value) &&
      (pay == null ? $('unknown-pay').checked : pay >= minimum);
  });
  if (!rows.some(r => key(r) === active)) { active = rows.length ? key(rows[0]) : ''; dirty = false; }
  $('result-count').textContent = rows.length + ' CV–job matches'; $('jobs').replaceChildren();
  if (!rows.length) $('jobs').append(node('p', 'No matches to show. Import jobs or adjust your filters.', 'empty'));
  for (const r of rows) {
    const a = r.assessment, j = r.job, card = node('button', undefined, 'job-card' + (key(r) === active ? ' active' : ''));
    card.dataset.matchKey = key(r); card.type = 'button'; card.setAttribute('aria-pressed', String(key(r) === active));
    const top = node('div', undefined, 'card-top'); top.append(node('span', j.company), node('span', a.score + '/100', 'score'));
    const bottom = node('div', undefined, 'card-bottom'); bottom.append(node('span', eligibilityLabel(a.eligibility), 'badge ' + a.eligibility), node('span', r.status));
    card.append(top, node('h3', j.title), node('div', j.location || j.workplace, 'muted'), node('div', a.candidate, 'muted'), bottom);
    card.onclick = () => { if (!guard()) return; active = key(r); dirty = false; notesDirty = false; render(); }; $('jobs').append(card);
  }
  detail(rows.find(r => key(r) === active));
}
function detail(r) {
  const box = $('detail'); box.replaceChildren();
  if (!r) { const empty = node('div', undefined, 'empty'); empty.append(node('span', '↗'), node('h3', 'Your next move starts here'), node('p', 'Add a CV and import postings, or explore the synthetic demo.')); box.append(empty); return; }
  const a = r.assessment, j = r.job;
  box.append(node('span', a.score + '/100 · Keyword baseline', 'badge'), node('h2', j.title), node('p', j.company + ' · ' + a.candidate, 'subtitle'));
  const link = node('a', 'View original posting ↗'); link.href = j.source_url || j.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; box.append(link);
  const facts = node('div', undefined, 'facts');
  for (const [label, value] of [['Work arrangement', j.workplace + ' · ' + (j.location || 'Location not supplied')], ['Eligibility', eligibilityLabel(a.eligibility)], ['Monthly USD minimum', a.compensation.monthly_usd_minimum == null ? 'Unknown / not converted' : '$' + Math.round(a.compensation.monthly_usd_minimum).toLocaleString()], ['Salary details', j.salary || [j.currency, j.salary_min, j.salary_max ? '– ' + j.salary_max : '', j.salary_period].filter(Boolean).join(' ') || 'Not supplied']]) {
    const fact = node('div'); fact.append(node('span', label), node('strong', value)); facts.append(fact);
  } box.append(facts, node('p', a.compensation.note, 'muted'));
  for (const warning of a.warnings) box.append(node('p', warning, 'warning'));
  box.append(node('h3', 'Why this CV matches'));
  if (!a.matches.length) box.append(node('p', 'No matching skills backed by the supplied CV.', 'muted'));
  for (const m of a.matches) { const e = node('div', undefined, 'evidence'); e.append(node('strong', m.skill), node('p', m.candidate_quote), node('small', 'CV evidence: ' + m.evidence_id), node('p', 'Posting: ' + m.job_quote)); box.append(e); }
  if (a.unverified_profile_skills.length) box.append(node('p', 'Skills listed without CV evidence: ' + a.unverified_profile_skills.join(', '), 'warning'));
  const desc = node('details'), summary = node('summary', 'Read job description'); desc.append(summary, node('p', j.description, 'description')); box.append(desc);
  box.append(node('h3', 'Prepare your application'));
  const draft = node('textarea'); draft.value = a.cover_letter || ''; draft.placeholder = 'Add your own verified application draft here.'; draft.setAttribute('aria-label', 'Editable cover letter'); draft.oninput = () => { dirty = true; }; box.append(draft);
  box.append(node('p', 'Review every claim. Draft edits stay in this tab until downloaded; tracking notes are saved separately.', 'muted'));
  const download = node('button', 'Download draft', 'secondary'); download.onclick = () => { const blob = new Blob([draft.value], {type:'text/plain;charset=utf-8'}), url = URL.createObjectURL(blob), anchor = node('a'); anchor.href = url; anchor.download = 'application-draft.txt'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); dirty = false; message('Draft downloaded. Review it before using.'); }; box.append(download);
  box.append(node('h3', 'Track this application'));
  const stage = node('select'); stage.setAttribute('aria-label', 'Application stage'); for (const s of state.statuses) option(stage, s, s); stage.value = r.status;
  const notes = node('textarea', undefined, 'notes'); notes.value = r.notes; notes.placeholder = 'Interview dates, follow-ups, or next steps…'; notes.setAttribute('aria-label', 'Application notes'); notes.oninput = () => { notesDirty = true; }; stage.onchange = () => { notesDirty = true; };
  const save = node('button', 'Save stage & notes'); save.onclick = () => action(save, async () => { await request('/api/status', {job_id:r.id, profile_hash:a.profile_hash, status:stage.value, notes:notes.value}); r.status = stage.value; r.notes = notes.value; notesDirty = false; $('shortlist-count').textContent = state.records.filter(x => x.status === 'shortlisted').length; $('applied-count').textContent = state.records.filter(x => ['applied','interview'].includes(x.status)).length; for (const card of $('jobs').children) { if (card.dataset.matchKey === key(r)) card.querySelector('.card-bottom').lastChild.textContent = r.status; } message('Application tracking saved locally.'); });
  box.append(stage, notes, save);
}
for (const id of ['search','filter-profile','eligibility','stage','salary','unknown-pay']) $(id).addEventListener('change', () => { if (guard()) { dirty = false; notesDirty = false; render(); } });
$('demo').onclick = () => { if (guard()) action($('demo'), async () => { dirty = false; const r = await request('/api/demo', {}); await refresh(); message('Synthetic demo loaded: ' + r.unique_jobs + ' opportunities. These are not real vacancies.'); }); };
$('profile-form').onsubmit = e => { e.preventDefault(); if (!guard()) return; action(e.submitter, async () => { const form = new FormData(e.target); const split = id => $(id).value.split(',').map(x => x.trim()).filter(Boolean); const data = {...template, name:$('candidate-name').value, profile_label:$('candidate-label').value, base_country:$('country').value.toUpperCase(), target_roles:split('roles'), skills:split('skills'), target_monthly_usd:Number($('target-pay').value), remote_only:$('remote-only').checked, open_to_relocation:$('relocation').checked, evidence:$('evidence').value.trim() ? [{id:'supplied_cv',text:$('evidence').value}] : [], resume_path:''}; form.set('profile', JSON.stringify(data)); await request('/api/profile', form); dirty = false; await refresh(); message('CV profile saved privately. Import jobs to compare it.'); }); };
$('import-form').onsubmit = e => { e.preventDefault(); if (!guard()) return; action(e.submitter, async () => { const form = new FormData(e.target); form.set('profiles', JSON.stringify([...$('profile-options').querySelectorAll('input:checked')].map(i => i.value))); const r = await request('/api/import', form); dirty = false; await refresh(); message('Ranked ' + r.unique_jobs + ' jobs across ' + r.candidate_assessments + ' CV matches. ' + r.duplicates_skipped + ' duplicates skipped; ' + r.jobs_outside_cap + ' beyond the 100-job cap.' + (r.source_warnings.length ? ' Import warnings: ' + r.source_warnings.join('; ') : '')); }); };
window.addEventListener('beforeunload', e => { if (dirty || notesDirty) { e.preventDefault(); e.returnValue = ''; } });
(async () => { try { template = await request('/api/template'); $('roles').value = template.target_roles.join(', '); $('skills').value = template.skills.join(', '); await refresh(); } catch(e) { message(e.message, true); } })();
