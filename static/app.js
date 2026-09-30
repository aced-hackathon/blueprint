"use strict";
const icons = {
  compass:'<circle cx="12" cy="12" r="9"/><path d="m16 8-2.5 5.5L8 16l2.5-5.5z"/>',
  shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8.5 11.5 2.5 2.5 4.5-5"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
  home:'<path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-8h6v8"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1"/>',
  flask:'<path d="M9 3h6M10 3v7l-5 8a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-8V3M8 15h8"/>',
  chart:'<path d="M4 4v16h16M8 16v-4M12 16V7M16 16v-6"/>',
  book:'<path d="M12 5v15M3 4c3-1 6-1 9 1 3-2 6-2 9-1v15c-3-1-6-1-9 1-3-2-6-2-9-1z"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  chevron:'<path d="m9 5 7 7-7 7"/>',
  play:'<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 11h18M8 15h3M8 18h6"/>',
  eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12"/><circle cx="12" cy="12" r="3"/>',
  wallet:'<rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 7V5l14-3v4M16 11h5v5h-5z"/>',
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.info}</svg>`;
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = cents => new Intl.NumberFormat('en-BE',{style:'currency',currency:'EUR',minimumFractionDigits:2,maximumFractionDigits:2}).format(cents/100);
const kg = value => `${Number(value).toFixed(2)} kg CO₂e`;
const dateLabel = value => new Date(value+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});
let state, currentView='journey', busy=false, toastTimer;
let payloadTab='request';
document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML=icon(el.dataset.icon));

function toast(message){ const el=document.getElementById('toast'); el.textContent=message;el.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('visible'),4500); }
async function refresh(){
  const response=await fetch('/api/state',{cache:'no-store'});
  if(!response.ok)throw new Error('Your demo session could not be loaded. Reload this page to reconnect.');
  state=await response.json();
  document.getElementById('customer-select').value=state.customer.id;
  document.getElementById('demo-date').textContent=dateLabel(state.today);
  document.getElementById('profile-button').textContent=state.customer.initials;
  render();
}
async function request(path, data={},message){
  if(busy)return false;busy=true;
  document.querySelectorAll('main button, main input, main select, .demo-toolbar button, .demo-toolbar select').forEach(el=>el.disabled=true);
  try{
    const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify(data)});
    const result=await response.json();if(!response.ok)throw new Error(result.error);
    await refresh();if(message)toast(message);return true;
  }catch(error){toast(error.message);if(state)render();return false;}
  finally{busy=false;document.querySelectorAll('.demo-toolbar button, .demo-toolbar select').forEach(el=>el.disabled=false);}
}
const act=(name,data={},message)=>request('/api/action/'+name,data,message);
function navigate(view){if(busy)return;currentView=view;render();document.querySelector('main').focus({preventScroll:true});}
function heading(eyebrow,title,description,note=''){return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${description}</p></div>${note?`<span class="heading-note">${icon('lock')}${note}</span>`:''}</div>`;}
function evidenceRows(){
  if(!state.evidence.length)return `<p class="empty-note">${state.goal.suppressed?'Moving signals are suppressed after your correction.':'No relevant signals are available under your current permissions.'}</p>`;
  return state.evidence.map(f=>{
    let title,copy;
    if(f.kind==='category_trend'){title='A change in home spending';copy=`${money(f.recent_cents)} in September, compared with a ${money(f.baseline_cents)} monthly average.`;}
    else if(f.event==='lower_carbon_guide_view'){title='Explored lower-carbon ideas';copy=`Opened the guide ${f.count} times. This does not confirm a personal goal.`;}
    else if(f.event==='bike_route_preview'){title='Previewed a bike route';copy=`Opened ${f.count} illustrative route previews. Actual journeys are unknown.`;}
    else{title='A little rental research';copy=`You opened the rental guide ${f.count} ${f.count===1?'time':'times'} this month.`;}
    return `<div class="evidence-row"><span class="icon-tile">${icon(f.kind==='category_trend'?'chart':'book')}</span><div><strong>${title}</strong><p>${copy}</p></div><span class="evidence-date">${f.kind==='category_trend'?'6 months':'September'}</span></div>`;
  }).join('');
}
function hero(){
  const {goal,policy}=state;
  if(state.climate.scenario){
    const top=state.recommendations[0];
    const active=policy.decision==='SUGGEST' && top;
    return `<section class="card next-step-card climate-hero"><div class="hero-top"><div class="hero-topline"><span class="eyebrow">A PRACTICAL POSSIBILITY</span><span class="status-pill">${active?'GOAL UNCONFIRMED':'NO PERMITTED SIGNAL'}</span></div><div class="hero-icon">${icon('compass')}</div><h2>${active?'Try two bike commutes a week.':'Your choices set the direction.'}</h2><p>${active?`Under your fictional trip assumptions, that could avoid about <strong>${kg(top.monthly_kg_co2e_avoided)} per four-week month</strong> of direct car emissions. Explore the route and a second grocery-trip option before deciding.`:'With guide activity turned off, there is no basis for a personal lower-carbon suggestion.'}</p></div><div class="hero-body"><div class="signal-preview">${icon('info')}<div><strong>A possible interest, not a stated goal.</strong>Guide visits can mean many things. Routes and travel modes here are illustrative settings, not bank-inferred facts.</div></div><div class="button-row"><button class="button primary" data-nav="climate" ${active?'':'disabled'}>Compare two practical changes</button><button class="button secondary" data-nav="privacy">Why was this suggested?</button></div><div class="hero-foot">${icon('shield')}No actual trip or merchant is booked.</div></div></section>`;
  }
  let title,copy,status,buttons,symbol='home';
  if(goal.status==='completed'){
    title='A good start to your next chapter.';copy='Your deposit preparation is complete. Your estimates and checklist are ready whenever you need them.';status='PREPARATION COMPLETE';symbol='check';buttons=`<button class="button primary" data-nav="task">View your preparation</button>`;
  }else if(goal.status==='dismissed'){
    title='Thanks for clearing that up.';copy='Researching for a friend makes sense. We’ve withdrawn the moving hypothesis and stopped further moving suggestions.';status='CORRECTION SAVED';symbol='check';buttons=`<button class="button secondary" data-nav="privacy">Review your preferences</button>`;
  }else if(policy.decision==='DEFER'){
    title='Your plan can wait.';copy=`Everything is saved. Your in-app reminder is set for ${dateLabel(goal.reminder_date)}. Until then, there’s nothing you need to do.`;status='SAVED FOR LATER';symbol='clock';buttons=`<button class="button primary" data-action="resume">Continue my plan now</button>`;
  }else if(policy.decision==='HELP_NOW'){
    title=state.notification.due?'Ready when you are.':'Let’s make room for your move.';copy='A new place comes with a few moving parts. Start with a rental deposit estimate and see what your month could look like.';status='GOAL CONFIRMED';buttons=`<button class="button primary" data-nav="task">${icon('wallet')}Prepare my rental deposit</button>${goal.status==='confirmed'?'<button class="button secondary" data-action="defer">Remind me in 7 days</button>':'<button class="button secondary" data-action="resume">Resume my plan</button>'}`;
  }else if(policy.decision==='ASK'){
    title='A deposit plan worth a look.';copy=`If a move is on your horizon, a two-month deposit at the example rent would be <strong>${money(state.finance.deposit_cents)}</strong>. Your projected balance after that and other example costs is <strong>${money(state.finance.forecast_cents)}</strong>. Does this plan fit your situation?`;status='POSSIBLE GOAL · YOUR DECISION';buttons=`<button class="button primary" data-action="confirm">Yes, make this my moving plan</button><button class="button secondary" data-action="dismiss">I’m researching for a friend</button>`;
  }else{
    title='A little space. No assumptions.';copy='There isn’t enough permitted evidence to suggest a next step. You can review your preferences whenever you like.';status='NO ACTION NEEDED';symbol='shield';buttons=`<button class="button secondary" data-nav="privacy">Manage my preferences</button>`;
  }
  return `<section class="card next-step-card"><div class="hero-top"><div class="hero-topline"><span class="eyebrow">YOUR NEXT STEP</span><span class="status-pill">${status}</span></div><div class="hero-icon">${icon(symbol)}</div><h2>${title}</h2><p>${copy}</p></div><div class="hero-body"><div class="signal-preview">${icon('info')}<div><strong>${goal.status==='unconfirmed'?'A possibility, never an assumption.':'You stay in control.'}</strong>${goal.status==='unconfirmed'?'Spending and browsing can mean different things. Your answer comes first.':'Your choices decide when we help and what information we use.'}</div></div><div class="button-row">${buttons}</div><div class="hero-foot">${icon('lock')}No account changes or payments will be made.</div></div></section>`;
}
function finance(){
  const f=state.finance;const max=Math.max(...f.months.map(m=>Math.max(m.income_cents,m.outflow_cents)),1);
  return `<section class="card card-pad finance-card"><div class="card-heading"><h3>Your month, at a glance</h3><span class="account-label">EUR</span></div><div class="overline">AVAILABLE BALANCE</div><div class="balance">${money(f.balance_cents)}</div><div class="balance-label">Synthetic current account</div><div class="finance-metrics"><div><span class="metric-label">September income</span><span class="metric-value income">+ ${money(f.income_cents)}</span></div><div><span class="metric-label">September spending</span><span class="metric-value">${money(f.outflow_cents)}</span></div></div><div class="mini-chart" role="img" aria-label="Six months of income and spending from April to September">${f.months.map(m=>`<div class="chart-column"><div class="chart-bar" data-height="${Math.round(m.income_cents/max*100)}" title="Income ${money(m.income_cents)}"></div><div class="chart-bar spending" data-height="${Math.round(m.outflow_cents/max*100)}" title="Spending ${money(m.outflow_cents)}"></div><span>${new Date(m.month+'-15T12:00:00').toLocaleDateString('en',{month:'short'})}</span></div>`).join('')}</div><div class="chart-caption"><span>April — September 2026</span><span><span class="legend"><i></i>In</span>&nbsp;&nbsp;<span class="legend"><i class="pale"></i>Out</span></span></div></section>`;
}
function suggestionFlow(){
  const interpretation=state.analysis.response;
  const facts=state.evidence.length?`${state.evidence.length} permitted observations`:'No permitted observations';
  const signal=state.evidence_strength==='none'?'None':`${state.evidence_strength} · intention unconfirmed`;
  const explanation=interpretation?.customer_need||'No interpretation for this state.';
  const why=interpretation?.possible_whys?.[0]||'Motivation unknown.';
  const action=state.recommendations[0]?.title||'No suggestion due now';
  return `<div class="flow-grid" aria-label="How this suggestion was formed"><div><span>01 · DETERMINISTIC FACTS</span><strong>${esc(facts)}</strong></div><div><span>02 · SIGNALS</span><strong>${esc(signal)}</strong></div><div><span>03 · LLM INTERPRETATION</span><strong>${esc(explanation)}</strong><small>${esc(state.analysis.mode)}</small></div><div><span>04 · POSSIBLE WHY</span><strong>${esc(why)}</strong><small>Hypothesis only</small></div><div><span>05 · ACTION</span><strong>${esc(action)}</strong></div></div>`;
}
function recommendationCards(){
  if(!state.recommendations.length)return `<div class="card card-pad"><p class="empty-note">No suggestion is due under the current state and permissions.</p></div>`;
  if(state.climate.scenario){
    return `<div class="recommendation-grid">${state.recommendations.map((option,i)=>`<article class="card card-pad suggestion-card ${i===0?'featured':''}"><div class="card-heading"><span class="eyebrow">${i===0?'LARGEST EXAMPLE CHANGE':'ANOTHER PRACTICAL OPTION'}</span><span class="status-pill">ILLUSTRATIVE</span></div><h3>${esc(option.title)}</h3><p>${esc(option.description)}</p><div class="saving">${kg(option.monthly_kg_co2e_avoided)}<span>direct car emissions per four-week month</span></div><p class="fine-print">${esc(option.condition)}</p><button class="button ${i===0?'primary':'secondary'} small" data-nav="climate">Compare assumptions</button></article>`).join('')}</div>`;
  }
  const deposit=state.finance.deposit_cents,remain=state.finance.forecast_cents;
  return `<article class="card card-pad suggestion-card moving-suggestion"><div class="card-heading"><span class="eyebrow">THE USEFUL CHANGE</span><span class="status-pill">${state.goal.status==='unconfirmed'?'IF YOU ARE MOVING':'GOAL CONFIRMED'}</span></div><div class="moving-suggestion-grid"><div><h3>Set aside a rental deposit before other moving costs.</h3><p>Start with a ${money(deposit)} deposit estimate. With your current example income, spending and moving costs, the projected balance is ${money(remain)}. Adjust the assumptions before acting.</p><p class="fine-print">A planning scenario, not an offer or a claim that you are moving.</p></div><div class="suggestion-number"><span>EXAMPLE DEPOSIT</span><strong>${money(deposit)}</strong><small>2 months × ${money(state.goal.rent_cents)} rent</small></div></div><div class="button-row">${state.goal.status==='unconfirmed'?'<button class="button primary small" data-action="confirm">Make this my plan</button>':`<button class="button primary small" data-nav="task">Open the deposit planner</button>`}<button class="button secondary small" data-nav="privacy">Review evidence & assumptions</button></div></article>`;
}
function askBox(){
  if(!state.analysis.request)return '';
  const live=state.analysis.mode.startsWith('OpenAI API');
  return `<section class="card card-pad ask-card"><div class="card-heading"><div><span class="eyebrow">CURIOUS ABOUT THE SUGGESTION?</span><h3>Ask for more context.</h3></div><span class="status-pill">${live?'OPENAI API':'SCRIPTED FALLBACK'}</span></div><p>${live?'Your question and the displayed structured context will be sent to OpenAI. Please keep personal secrets in the separate private space.':'A live API answer is unavailable. You can still see a clearly labeled scripted explanation.'}</p><form id="ask-form"><label for="ask-input" class="sr-only">Question about this suggestion</label><input id="ask-input" name="question" maxlength="300" minlength="5" required placeholder="Why this option? What assumptions could change it?"><button class="button primary small" type="submit">${live?'Ask OpenAI':'Ask about this option'}</button></form><div id="ask-result" role="status" aria-live="polite"></div></section>`;
}
function journey(){
 return `${heading('A LITTLE CLARITY FOR WHAT’S NEXT',`Good morning, ${esc(state.customer.name.split(' ')[0])}.`,'Life moves forward. Let’s find your next step together.','Personalization, on your terms')}
 ${state.notification.due?`<div class="notice">${icon('clock')}<span><strong>In-app reminder preview</strong><br>${esc(state.notification.text)}</span></div>`:''}
 <div class="journey-grid">${hero()}${finance()}</div>
 <div class="section-title"><h3>From evidence to a practical change</h3><span>Every step can be checked</span></div>
 ${suggestionFlow()}
 <div class="section-title"><h3>Suggested changes</h3><span>Based on synthetic assumptions</span></div>
 ${recommendationCards()}
 ${askBox()}
 <div class="lower-grid"><section class="card"><div class="card-pad"><div class="card-heading"><h3>Why this came up</h3><span class="status-pill">${state.evidence_strength.toUpperCase()} EVIDENCE</span></div><div class="evidence-list">${evidenceRows()}</div></div><button class="card-link" data-nav="privacy">See the evidence & what was shared${icon('chevron')}</button></section><section class="card privacy-teaser">${icon('shield')}<h3>A personal question doesn’t need your entire history.</h3><p>Choose the signals you’re comfortable sharing. Explore the separate synthetic conversation sandbox.</p><button class="text-button" data-nav="private">Explore your private space ${icon('chevron')}</button></section></div>`;
}
function privacy(){return `${heading('TRANSPARENCY BY DESIGN','A clear view of your boundaries.','See what informs a suggestion, and choose what stays out.')}
 <div class="notice">${icon('info')}<span><strong>${esc(state.analysis.mode)}.</strong> The structured context below is the actual interpretation input. When OpenAI is active, it is sent from this backend; a fallback is labeled explicitly.</span></div>
 <div class="privacy-layout"><section class="card card-pad"><div class="card-heading"><h3>Your personalization choices</h3>${icon('shield')}</div><label class="permission-row"><span><strong>Spending trends</strong><p>Use monthly category totals to notice changes over time. Raw transactions stay out of the adapter request.</p></span><input type="checkbox" class="switch" id="permission-trends" ${state.permissions.trends?'checked':''} aria-label="Allow spending trends"></label><label class="permission-row"><span><strong>Relevant app activity</strong><p>Use relevant guide and route-preview counts to form a tentative signal.</p></span><input type="checkbox" class="switch" id="permission-activity" ${state.permissions.activity?'checked':''} aria-label="Allow app activity"></label><p class="fine-print">Changes apply immediately to the next analysis. Revoked facts are recomputed out of the payload. An explicitly confirmed goal stays available for your task. Withdrawal cannot undo information already transmitted.</p></section>
 <section class="card card-pad"><div class="card-heading"><h3>The evidence, with context</h3><span class="status-pill">${state.evidence_strength.toUpperCase()}</span></div><div class="evidence-list">${evidenceRows()}</div><p class="fine-print">Strength is an uncalibrated rule: two permitted signals = medium; one = low. Neither establishes an intention. A correction overrides the pattern.</p><div class="decision-banner"><span class="decision-code">${state.policy.decision}</span><p>${esc(state.policy.reason)}</p></div></section></div>
 <section class="card payload-card"><div class="card-pad"><div class="card-heading"><h3>Exactly what the adapter sees</h3><span class="account-label">${state.analysis.latency_ms} ms · interpretation</span></div><p class="fine-print">Purpose: ${esc(state.analysis.request?.purpose||"no analysis due")}. Request and response captures exist in page memory; they are not saved in SQLite. Remote processing is possible when OpenAI is active.</p><div class="field-chips"><span class="chip">Aggregate facts</span><span class="chip">Goal status</span><span class="chip">Fixed action IDs</span><span class="chip excluded">No customer identity</span><span class="chip excluded">No transaction rows</span><span class="chip excluded">No private transcript</span></div></div><div class="payload-tabs"><button class="${payloadTab==='request'?'active':''}" data-payload="request">Structured model context</button><button class="${payloadTab==='response'?'active':''}" data-payload="response">Validated proposal</button><button class="${payloadTab==='policy'?'active':''}" data-payload="policy">Backend decision</button></div><pre id="payload-code">${esc(JSON.stringify(payloadTab==='policy'?state.policy:state.analysis[payloadTab],null,2))}</pre></section>
 <section class="card card-pad journal"><div class="card-heading"><h3>Your choices, recorded</h3><span class="account-label">Shared banking workflow</span></div>${state.history.length?state.history.map(h=>`<div class="journal-item"><span>${dateLabel(h.date)}</span><p>${esc(h.detail)}</p></div>`).join(''):'<p class="empty-note">No decisions yet. Your explicit choices will appear here.</p>'}</section>`;}
function forecast(){const f=state.finance,g=state.goal;return `<section class="card card-pad forecast-card"><span class="eyebrow">YOUR CASH-FLOW PREVIEW</span><h2>A little perspective.</h2><p class="fine-print">One month ahead, based on September’s totals and your saved estimates.</p><div class="forecast-lines"><div class="forecast-line"><span>Available now</span><strong>${money(f.balance_cents)}</strong></div><div class="forecast-line"><span>Expected income</span><strong>+ ${money(f.income_cents)}</strong></div><div class="forecast-line"><span>Usual monthly spending</span><strong>− ${money(f.outflow_cents)}</strong></div><div class="forecast-line"><span>Rental deposit · ${g.deposit_months} months</span><strong>− ${money(f.deposit_cents)}</strong></div><div class="forecast-line"><span>Moving costs</span><strong>− ${money(g.moving_cents)}</strong></div></div><div class="forecast-result"><span class="overline">ESTIMATED REMAINING BALANCE</span><div class="balance ${f.forecast_cents<0?'negative':''}">${money(f.forecast_cents)}</div><p class="fine-print">${f.forecast_cents<0?'This estimate leaves a shortfall. Revisit the assumptions before proceeding.':'An estimate to help you plan, not a guarantee or financial recommendation.'}</p></div></section>`;}
function task(){
 if(state.goal.status==='completed')return `${heading('A STEP FORWARD','You’re a little more prepared.','A plan you can come back to, with no bank actions taken.')}<section class="card receipt"><div class="hero-icon">${icon('check')}</div><span class="eyebrow">MOCK TASK COMPLETE</span><h2>Your rental deposit plan is ready.</h2><p>You reviewed the budget, prepared the document checklist and checked the estimate. No deposit account was opened and no money was transferred.</p><div class="receipt-summary"><div class="forecast-line"><span>Planned deposit</span><strong>${money(state.finance.deposit_cents)}</strong></div></div><div class="receipt-ref">Saved to ${esc(state.customer.name)}’s synthetic goal</div><button class="button primary" data-nav="journey">Back to your next step</button></section>`;
 if(state.goal.status==='deferred')return `${heading('SAVED FOR LATER','Your plan is paused.','Resume it when you want to continue.')}<button class="button primary" data-action="resume">Resume my plan</button>`;
 if(state.goal.status!=='confirmed')return `${heading('YOUR DEPOSIT PLAN','Let’s start with your goal.','Confirm that you’re planning a move before preparing a deposit.')}<button class="button primary" data-nav="journey">Back to your next step</button>`;
 return `<button class="text-button back-button" data-nav="journey">Back to your next step</button>${heading('MOCK TASK · RENTAL DEPOSIT','Your new place. A clearer plan.','Adjust the estimates, then prepare your next step. Nothing here moves money.')}
 <div class="task-layout"><section class="card card-pad"><div class="card-heading"><h3>Make the numbers yours</h3>${icon('home')}</div><form id="budget-form"><div class="form-grid"><label class="form-field">Monthly rent (€)<input name="rent" type="number" min="100" max="10000" step="0.01" value="${state.goal.rent_cents/100}" required><small>Estimate · €100–€10,000</small></label><label class="form-field">Deposit size<select name="months">${[1,2,3].map(n=>`<option value="${n}" ${state.goal.deposit_months===n?'selected':''}>${n} ${n===1?'month':'months'} of rent</option>`).join('')}</select><small>Scenario assumption, not a legal rule</small></label><label class="form-field full">Estimated moving costs (€)<input name="moving" type="number" min="0" max="5000" step="0.01" value="${state.goal.moving_cents/100}" required><small>Transport, supplies and other one-off costs</small></label></div><button class="button primary budget-submit" type="submit">Update my preview</button></form><p class="fine-print">September spending includes the existing rent. This simple preview assumes it stays unchanged and excludes overlapping rent, fees and unexpected expenses.</p></section>${forecast()}</div>
 <section class="card card-pad journal"><div class="card-heading"><h3>Three small steps to be ready</h3><span class="account-label">${state.goal.checklist.length} of 3 complete</span></div><div class="checklist">${[['budget','Review the deposit estimate','Check the rent, deposit size and one-off moving costs.'],['documents','Prepare your document checklist','Identify the ID and lease information you would need. Do not upload any documents here.'],['review','Check your remaining balance','Review the assumptions and acknowledge that this is a simulation.']].map(([id,title,copy])=>`<label class="check-row"><input type="checkbox" data-check="${id}" ${state.goal.checklist.includes(id)?'checked':''}><span><strong>${title}</strong><small>${copy}</small></span></label>`).join('')}</div><div class="button-row"><button class="button primary" data-action="complete" ${state.goal.checklist.length<3?'disabled':''}>${icon('check')}Complete mock preparation</button><button class="button secondary" data-action="defer">Save for later</button></div></section>`;
}
function climateDetail(){
  const scenario=state.climate.scenario;
  if(!scenario)return `${heading('NO SCENARIO','No travel comparison is available.','Choose Noah in the demo selector to explore the synthetic climate scenario.')}`;
  return `<button class="text-button back-button" data-nav="journey">Back to suggestions</button>${heading('CALCULATED OPTIONS','A smaller trip, on your terms.','Two changes based on fictional travel settings. Pick one to save as an idea, if either fits.')}
  <div class="notice warning">${icon('info')}<span><strong>Illustrative comparison.</strong> Payment records did not establish where you travel, how you travel, or why. Distances and ${scenario.car_g_per_km} g/km for a car are fictional scenario inputs. Routes, local shop availability and safety are not verified.</span></div>
  <div class="recommendation-grid">${state.recommendations.map(option=>`<section class="card card-pad option-detail"><span class="eyebrow">${esc(option.route_kind)}</span><h2>${esc(option.title)}</h2><p>${esc(option.description)}</p><div class="saving">${kg(option.monthly_kg_co2e_avoided)}<span>estimated direct car emissions avoided / four weeks</span></div><div class="formula"><strong>How code calculated it</strong><p>${esc(option.calculation)} = ${kg(option.monthly_kg_co2e_avoided)}</p></div><p class="fine-print">${esc(option.condition)}</p><button class="button ${state.climate.selected_option===option.id?'secondary':'primary'} small" data-save-climate="${option.id}">${state.climate.selected_option===option.id?'Saved as an idea':'Save this idea'}</button></section>`).join('')}</div>
  <section class="card card-pad journal"><h3>Where this context comes from</h3><p class="fine-print">Published research shows that a food’s origin alone is a weak guide to its total climate impact. This demo estimates only travel changes; it does not calculate food production emissions, merchant prices or a real route.</p><p><a href="https://ourworldindata.org/faqs-environmental-impacts-food" target="_blank" rel="noreferrer noopener">Food and transport context</a> · <a href="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025" target="_blank" rel="noreferrer noopener">Transport factor reference</a></p><p class="fine-print">The 160 g/km coefficient is a round demo assumption, not a published figure from either link. Ask about the suggestion on the main page to discuss its uncertainty with OpenAI when configured.</p></section>`;
}
function privateSpace(){return `${heading('A SEPARATE SPACE','Some things are yours to keep.','Explore a boundary before you decide what to share.')}
 <div class="notice warning">${icon('lock')}<span><strong>Private mode unavailable.</strong> No verified on-device model is configured. Below is an isolated, scripted demonstration with fictional text. It is not a live confidential AI conversation.</span></div>
 <iframe id="private-frame" class="private-frame" src="/private.html" sandbox="allow-scripts" title="Synthetic private conversation sandbox"></iframe>
 <p class="fine-print">Demo runs on this developer-operated computer. Local administrators, browser extensions, screen recording or a compromised device may inspect content. Clearing a session is not forensic erasure. No personal-device inference guarantee has been demonstrated.</p>`;}
function render(){
  if(!state)return;
  const main=document.getElementById('content');
  main.innerHTML=({journey,privacy,task,climate:climateDetail,private:privateSpace}[currentView]||journey)();
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.toggle('active',el.dataset.view===((currentView==='task'||currentView==='climate')?'journey':currentView)));
  document.getElementById('breadcrumb-view').textContent=({journey:'Your next step',privacy:'Privacy & evidence',private:'Private space',task:'Rental deposit preparation',climate:'Lower-carbon comparisons'})[currentView];
  // CSSOM avoids inline style attributes in templates; CSP blocks untrusted inline styles.
  main.querySelectorAll('[data-height]').forEach(el=>el.style.height=el.dataset.height+'%');
  main.querySelectorAll('[data-nav]').forEach(el=>el.onclick=()=>navigate(el.dataset.nav));
  main.querySelectorAll('[data-action]').forEach(el=>el.onclick=()=>act(el.dataset.action,{},({confirm:'Your moving goal is confirmed.',dismiss:'Correction saved. Moving suggestions are now suppressed.',defer:'Plan saved. No reminder will appear before the chosen date.',resume:'Your plan is ready to continue.',complete:'Mock preparation complete. No money moved.'})[el.dataset.action]));
  main.querySelectorAll('[data-save-climate]').forEach(el=>el.onclick=()=>act('save-climate',{option_id:el.dataset.saveClimate},'Saved as a fictional idea. No trip or purchase was booked.'));
  main.querySelectorAll('[data-payload]').forEach(el=>el.onclick=()=>{payloadTab=el.dataset.payload;render();});
  main.querySelectorAll('.switch').forEach(el=>el.onchange=()=>act('permissions',{trends:document.getElementById('permission-trends').checked,activity:document.getElementById('permission-activity').checked},'Your permissions have been applied to the next analysis.'));
  const form=document.getElementById('budget-form');
  if(form)form.onsubmit=event=>{event.preventDefault();const data=new FormData(form);act('budget',{rent_cents:Math.round(Number(data.get('rent'))*100),deposit_months:Number(data.get('months')),moving_cents:Math.round(Number(data.get('moving'))*100)},'Preview updated. Review the checklist for these new estimates.');};
  main.querySelectorAll('[data-check]').forEach(el=>el.onchange=()=>act('checklist',{items:[...main.querySelectorAll('[data-check]:checked')].map(x=>x.dataset.check)}));
  const askForm=document.getElementById('ask-form');
  if(askForm)askForm.onsubmit=async event=>{
    event.preventDefault();const input=askForm.querySelector('#ask-input');const result=main.querySelector('#ask-result');
    const question=input.value.trim();if(question.length<5||question.length>300)return;
    const button=askForm.querySelector('button');button.disabled=true;result.textContent='Checking the suggestion…';
    try{
      const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify({question})});
      const answer=await response.json();if(!response.ok)throw Error(answer.error||'The answer is unavailable.');
      result.innerHTML=`<div class="answer"><span class="eyebrow">${esc(answer.mode)}</span><p>${esc(answer.answer)}</p><small>${esc(answer.uncertainty)}</small></div>`;
      input.value='';
    }catch(error){result.textContent=error.message;}
    finally{button.disabled=false;}
  };
}
document.querySelectorAll('[data-view]').forEach(el=>el.onclick=()=>navigate(el.dataset.view));
document.querySelector('.brand').onclick=e=>{e.preventDefault();navigate('journey');};
document.getElementById('customer-select').onchange=async event=>{currentView='journey';await request('/api/demo/select',{customer_id:event.target.value},'Switched synthetic demo customer.');};
document.getElementById('profile-button').onclick=()=>document.getElementById('customer-select').focus();
document.getElementById('reset-button').onclick=()=>{currentView='journey';request('/api/demo/reset',{},'This customer’s scenario has been reset.');};
document.getElementById('advance-button').onclick=()=>request('/api/demo/advance',{},'Demo clock advanced by seven days.');
document.getElementById('guide-button').onclick=()=>document.getElementById('guide-dialog').showModal();
document.getElementById('close-guide').onclick=document.getElementById('start-guide').onclick=()=>document.getElementById('guide-dialog').close();
window.addEventListener('message',async event=>{
  const frame=document.getElementById('private-frame');
  if(!frame||event.source!==frame.contentWindow||event.origin!=='null')return;
  // The sandbox may export one fixed enum, never its transcript or arbitrary text.
  if(JSON.stringify(event.data)!==JSON.stringify({type:'APPROVE_MOVING_GOAL'}))return;
  if(busy)return;
  const result=await act('share',{statement:'I am planning to move next month.',purpose:'moving_goal_assistance'},'Only the approved moving statement was shared.');
  if(result)navigate('journey');
});
refresh().catch(error=>{document.getElementById('content').innerHTML=`<div class="error-state"><h2>The workspace couldn’t open.</h2><p>${esc(error.message)}</p><button class="button primary" id="retry-button">Try again</button></div>`;document.getElementById('retry-button').onclick=()=>location.reload();});
