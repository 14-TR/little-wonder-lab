import lessons from './data/lessons.json';
import { selectLessons, latestLesson } from './catalog.js';
import { illustration, flower, sun } from './illustrations.js';
import { mountInteractive } from './interactions.js';
import { requestMarkup, mountRequest } from './request.js';
import { createProgress, mountProgress } from './progress.js';
import { mountNotebook } from './notebook.js';
import './styles.css';

const app = document.querySelector('#app');
const escape = (value = '') => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const arrow = '<span aria-hidden="true">↗</span>';
const byId = id => lessons.find(lesson => lesson.id === id);
const progress = createProgress(() => window.localStorage, lessons.map(lesson => lesson.id));
let cleanupLesson = () => {};

function shell(content, active = 'explore') {
  app.innerHTML = `<a class="skip-link" href="#main">Skip to content</a>
    <header class="site-header"><a class="brand" href="#explore" aria-label="Little Wonder Lab home"><span class="brand-flower">${flower}</span><span>little wonder<span class="brand-lab">lab.</span></span></a>
      <nav aria-label="Main navigation"><a href="#explore" ${active === 'explore' ? 'aria-current="page"' : ''}>Explore</a><a href="#request" ${active === 'request' ? 'aria-current="page"' : ''}>Suggest a wonder ${arrow}</a></nav>
    </header>
    <main id="main" tabindex="-1">${content}</main>
    <footer class="site-footer"><span class="footer-mark">${flower} Small experiments. Big possibilities.</span><span>Made for curious kids & their grown-ups.</span><span>No accounts. No tracking. Just wonder.</span><span>© 2026 TR Ingram</span></footer>`;
}

function lessonCard(lesson, featured = false) {
  return `<a class="lesson-card ${featured ? 'featured' : 'shelf-card'}" href="#lesson/${escape(lesson.id)}" data-lesson-link="${escape(lesson.id)}">
    <div class="art-wrap ${escape(lesson.kind)}"><span class="folio">FIELD NOTE ${String(lesson.order).padStart(2, '0')}</span>${illustration(lesson.kind)}<span class="art-label">${escape(lesson.kind === 'shadows' ? 'A little light. A big discovery.' : lesson.kind === 'ramps' ? 'Let the good times roll.' : 'Think it. Fold it. Test it.')}</span></div>
    <div class="card-copy"><div class="meta"><span>${escape(lesson.topic)}</span><span>${lesson.duration} min · with a grown-up</span></div><h2>${escape(lesson.title)}</h2><p>${escape(lesson.subtitle)}</p>${progress.read().completed.includes(lesson.id) ? '<span class="explored-note">✓ Explored on this device</span>' : ''}<span class="card-action">${featured ? 'Let’s investigate' : 'Explore this wonder'} <span aria-hidden="true">→</span></span></div></a>`;
}

function renderExplore() {
  document.title = 'Explore · Little Wonder Lab';
  const latest = latestLesson(lessons);
  const publishedLabel = latest ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${latest.published}T00:00:00Z`)) : '';
  shell(`<section class="explore-heading"><div><p class="eyebrow">A FIELD GUIDE TO EVERYDAY WONDERS</p><h1>Follow your <em>what if.</em></h1><p class="intro">Big questions. Little experiments.<br>Discover something wonderful, together.</p></div><aside class="margin-note">${sun}<p>A little screen time.<br>A lot of real-world wonder.</p><span>For curious minds, around age 7</span></aside></section>
    ${latest ? `<div class="latest-note"><span>Latest field note</span><a href="#lesson/${escape(latest.id)}">${escape(latest.title)} <span aria-hidden="true">↗</span></a><time datetime="${escape(latest.published)}">${publishedLabel}</time></div>` : ''}
    <section aria-label="Explore lessons"><div class="catalog-tools"><div class="topic-tabs" aria-label="Filter by topic"><button type="button" data-topic="All" aria-pressed="true">All wonders</button>${[...new Set(lessons.map(l => l.topic))].map(topic => `<button type="button" data-topic="${escape(topic)}" aria-pressed="false">${escape(topic)}</button>`).join('')}</div><div class="search-wrap"><label for="lesson-search" class="sr-only">Search lessons</label><span aria-hidden="true">⌕</span><input type="search" id="lesson-search" placeholder="Find a little wonder" autocomplete="off"></div></div>
    <div class="catalog-caption"><span id="catalog-count" aria-live="polite">${lessons.length} investigations for your next “what if?”</span><div class="catalog-sort"><label class="sr-only" for="lesson-sort">Lesson order</label><select id="lesson-sort"><option value="field">Start here</option><option value="newest">Newest first</option></select></div></div><div id="lesson-catalog" class="lesson-catalog">${selectLessons(lessons).map((lesson, index) => lessonCard(lesson, index === 0)).join('')}</div></section>
    <section class="wonder-strip"><span class="wonder-doodle" aria-hidden="true">?</span><div><h2>The best experiments start with a question.</h2><p>What is your little scientist wondering about?</p></div><a class="text-link" href="#request">Send us a wonder ${arrow}</a></section>`);
  let topic = 'All';
  const search = document.querySelector('#lesson-search');
  const sort = document.querySelector('#lesson-sort');
  function filter() {
    const selected = selectLessons(lessons, { topic, query: search.value, sort: sort.value });
    document.querySelector('#lesson-catalog').innerHTML = selected.length ? selected.map((lesson, index) => lessonCard(lesson, index === 0)).join('') : `<div class="empty-state"><h2>No wonders found. Yet.</h2><p>Try another word or explore all the lessons.</p><button class="button secondary" id="clear-search">Show all wonders</button></div>`;
    document.querySelector('#catalog-count').textContent = `${selected.length} ${selected.length === 1 ? 'investigation' : 'investigations'} to explore`;
    document.querySelector('#clear-search')?.addEventListener('click', () => { search.value = ''; topic = 'All'; updateTabs(); filter(); search.focus(); });
  }
  function updateTabs() { document.querySelectorAll('[data-topic]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.topic === topic))); }
  search.addEventListener('input', filter);
  sort.addEventListener('change', filter);
  document.querySelectorAll('[data-topic]').forEach(button => button.addEventListener('click', () => { topic = button.dataset.topic; updateTabs(); filter(); }));
}

function renderLesson(lesson) {
  document.title = `${lesson.title} · Little Wonder Lab`;
  shell(`<a class="back-link" href="#explore"><span aria-hidden="true">←</span> Back to explore</a>
    <article class="lesson-page"><header class="lesson-heading"><div><p class="eyebrow">FIELD NOTE ${String(lesson.order).padStart(2, '0')} <span> / </span> ${escape(lesson.topic)} <span> / </span> ${lesson.duration} MINUTES</p><h1>${escape(lesson.title)}</h1><p class="lesson-question">${escape(lesson.question)}</p><p class="together-note">You + a grown-up + a little curiosity.</p><button class="print-button" id="print-lesson" type="button">Print this field note <span aria-hidden="true">↗</span></button></div><div class="lesson-cover ${escape(lesson.kind)}">${illustration(lesson.kind)}</div></header>
    <div id="interactive-slot"></div>
    <div class="notebook-body"><div class="investigation"><section class="prediction"><p class="eyebrow">01 / WONDER FIRST</p><h2>What do you think?</h2><p>${escape(lesson.prediction)}</p><p class="small-note">Say your guess out loud. It’s okay if it changes!</p></section>
    <section class="hands-on"><p class="eyebrow">02 / OFF THE SCREEN</p><h2>Try it in your world</h2><ol class="experiment-steps">${lesson.steps.map((step, index) => `<li><span class="step-number">${index + 1}</span><div><h3>${escape(step.title.replace(/^\d+\.\s*/, ''))}</h3><p>${escape(step.body)}</p></div></li>`).join('')}</ol><div class="step-controls"><button type="button" class="button secondary" id="previous-step">Previous step</button><span id="step-status" role="status"></span><button type="button" class="button" id="next-step">Next step</button></div></section>
    <section class="discovery"><p class="eyebrow">03 / AHA!</p><h2>Here’s the little big idea</h2><p class="idea">${escape(lesson.idea)}</p><p>${escape(lesson.explanation)}</p></section>
    <section class="challenge"><span class="challenge-star" aria-hidden="true">✳</span><div><h2>One more “what if?”</h2><p>${escape(lesson.challenge)}</p></div></section></div>
    <aside class="field-kit"><section><p class="eyebrow">YOUR EXPLORER KIT</p><h2>Gather your things</h2><ul class="materials">${lesson.materials.map(item => `<li>${escape(item)}</li>`).join('')}</ul><p class="safety"><strong>Grown-up check</strong>${escape(lesson.safety)}</p></section>
    <section class="word-collection"><p class="eyebrow">WORDS TO COLLECT</p><dl>${lesson.vocabulary.map(item => `<dt>${escape(item.word)}</dt><dd>${escape(item.meaning)}</dd>`).join('')}</dl></section></aside></div>
    <details class="grown-up"><summary>A little help for grown-ups <span aria-hidden="true">+</span></summary><div><p>${escape(lesson.parentNote)}</p>${lesson.prerequisites.length ? `<p><strong>A helpful earlier wonder:</strong> ${lesson.prerequisites.map(id => `<a href="#lesson/${escape(id)}">${escape(byId(id)?.title || id)}</a>`).join(', ')}. No lessons are locked; explore in any order.</p>` : ''}<h3>Where the science comes from</h3><ul>${lesson.sources.map(source => `<li><a href="${escape(source.url)}" target="_blank" rel="noopener noreferrer">${escape(source.title)} <span class="sr-only">(opens in a new tab)</span> ↗</a></li>`).join('')}</ul></div></details>
    <section class="print-notes"><h2>Our field notes</h2><p>I predicted…</p><p>I noticed…</p><p>Now I wonder…</p></section><div id="completion-slot"></div>
    <div class="lesson-end"><a class="text-link" href="#explore">Find your next wonder <span aria-hidden="true">→</span></a><span>Wonder is better together.</span></div></article>`);
  mountInteractive(lesson.kind, document.querySelector('#interactive-slot'));
  mountProgress(document.querySelector('#completion-slot'), progress, lesson.id);
  cleanupLesson = mountNotebook(document.querySelector('.lesson-page'));
}

function route() {
  const hash = window.location.hash || '#explore';
  if (hash === '#main') { document.querySelector('#main')?.focus(); return; }
  cleanupLesson();
  if (hash.startsWith('#lesson/')) {
    const lesson = byId(hash.slice('#lesson/'.length));
    if (lesson) renderLesson(lesson);
    else { document.title = 'Wonder not found · Little Wonder Lab'; shell(`<section class="empty-state"><p class="eyebrow">A LITTLE DETOUR</p><h1>That wonder isn’t here.</h1><p>There are more discoveries waiting in your notebook.</p><a class="button" href="#explore">Back to explore</a></section>`); }
  } else if (hash === '#request') {
    document.title = 'Suggest a wonder · Little Wonder Lab';
    shell(requestMarkup, 'request');
    mountRequest(document.querySelector('#main'));
  } else renderExplore();
  window.scrollTo(0, 0);
  if (window.location.hash) document.querySelector('#main')?.focus({ preventScroll: true });
}
window.addEventListener('hashchange', route);
route();
