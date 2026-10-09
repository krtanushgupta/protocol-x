const form = document.querySelector('#analyzeForm');
const input = document.querySelector('#conversation');
const fileInput = document.querySelector('#fileInput');
const errorBox = document.querySelector('#error');
const button = document.querySelector('#analyzeButton');
const cinematicIntro = document.querySelector('#cinematicIntro');

if (cinematicIntro) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) cinematicIntro.remove();
  else {
    cinematicIntro.addEventListener('animationend', (event) => {
      if (event.target === cinematicIntro) cinematicIntro.remove();
    }, { once: true });
    window.setTimeout(() => cinematicIntro.remove(), 1550);
  }
}

input.addEventListener('input', () => {
  document.querySelector('#charCount').textContent = `${input.value.length.toLocaleString()} characters`;
});

fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file) return;
  document.querySelector('#fileName').textContent = file.name;
  errorBox.hidden = true;
  if (!file.name.toLowerCase().endsWith('.txt')) {
    showError('Please choose a WhatsApp-exported .txt file.');
    return;
  }
  if (file.size > 1_000_000) {
    showError('This file is too large to analyze (limit: 1 MB).');
    return;
  }
  try {
    input.value = await file.text();
    input.dispatchEvent(new Event('input'));
  } catch {
    showError('Could not read this file. Please try another .txt export.');
  }
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorBox.hidden = true;
  if (!input.value.trim()) {
    showError('Paste a conversation or upload a WhatsApp .txt file first.');
    return;
  }
  button.disabled = true;
  button.textContent = 'Reading conversation…';
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input.value }),
      signal: AbortSignal.timeout(120_000)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analysis failed. Please try again.');
    render(data);
    document.querySelector('#inputScreen').hidden = true;
    document.querySelector('#resultsScreen').hidden = false;
    window.scrollTo(0, 0);
  } catch (error) {
    const message = error.name === 'TimeoutError'
      ? 'Analysis took too long. Your conversation is still in the text box; try a shorter export or retry.'
      : error instanceof TypeError || error.message === 'Failed to fetch'
      ? 'The UNMISSED analysis server is not reachable. Start UNMISSED with run_unmissed.bat, then try again. Your conversation is still in the text box.'
      : (error.message || 'Could not analyze this conversation. Please try again.');
    showError(message);
  } finally {
    button.disabled = false;
    button.innerHTML = 'Analyze conversation <span aria-hidden="true">→</span>';
  }
});

document.querySelector('#anotherButton').addEventListener('click', () => {
  document.querySelector('#resultsScreen').hidden = true;
  document.querySelector('#inputScreen').hidden = false;
  window.scrollTo(0, 0);
});

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function render(data) {
  const overview = document.querySelector('#overviewList');
  overview.replaceChildren(...data.overview.map((line) => element('li', '', line)));
  const root = document.querySelector('#categories');
  root.replaceChildren();
  const priorities = [['URGENT', '#FF2638'], ['IMPORTANT', '#E5B454'], ['FYI', '#9AA0AA']];
  const topicCounts = new Map();
  let total = 0;

  for (const [priority, color] of priorities) {
    const findings = data.categories[priority] || [];
    total += findings.length;
    const section = element('section', 'priority-section');
    const heading = element('div', 'section-title');
    heading.style.setProperty('--section', color);
    heading.append(
      element('i', 'priority-dot'),
      element('h2', '', priority),
      element('span', 'count', `${findings.length} ${findings.length === 1 ? 'finding' : 'findings'}`)
    );
    section.append(heading);

    if (!findings.length) section.append(element('div', 'empty-category', 'Nothing identified in this priority.'));
    const topics = new Map();
    for (const finding of findings) {
      const topic = finding.topic || 'Announcements & FYI';
      if (!topics.has(topic)) topics.set(topic, []);
      topics.get(topic).push(finding);
      topicCounts.set(topic, (topicCounts.get(topic) || 0) + 1);
    }
    for (const [topic, items] of topics) {
      const group = element('section', 'topic-group');
      group.dataset.topic = topic;
      const isOpen = items.length <= 3;
      if (isOpen) group.classList.add('is-open');
      const toggle = element('button', 'topic-toggle', '');
      toggle.type = 'button';
      const contentId = `topic-content-${priority.toLowerCase()}-${topicCounts.size}`;
      toggle.setAttribute('aria-expanded', String(isOpen));
      toggle.setAttribute('aria-controls', contentId);
      toggle.append(element('span', 'topic-name', topic), element('span', 'topic-count', `${items.length} ${items.length === 1 ? 'item' : 'items'}`), element('span', 'topic-chevron', ''));
      const content = element('div', 'topic-content');
      content.id = contentId;
      content.setAttribute('role', 'region');
      content.setAttribute('aria-label', topic);
      content.inert = !isOpen;
      const inner = element('div', 'topic-content-inner');
      for (const finding of items) inner.append(renderFinding(finding));
      content.append(inner);
      toggle.addEventListener('click', () => {
        const expanded = group.classList.toggle('is-open');
        toggle.setAttribute('aria-expanded', String(expanded));
        content.inert = !expanded;
      });
      group.append(toggle, content);
      section.append(group);
    }
    root.append(section);
  }
  renderTopicTabs(topicCounts, total);
  document.querySelector('#resultCount').textContent = `${data.message_count} messages parsed · ${total} findings`;
}

function renderTopicTabs(topicCounts, total) {
  const nav = document.querySelector('#topicTabs');
  const definitions = [
    ['Register', 'Registrations & Forms'],
    ['Assignments', 'Assignments & Submissions'],
    ['Homework', 'Homework & Doubts'],
    ['Classes', 'Classes & Attendance'],
    ['Deadlines', 'Deadlines & Reminders'],
    ['Announcements', 'Announcements & FYI']
  ];
  nav.replaceChildren();
  const tabs = [['All', 'all', total]];
  for (const [label, topic] of definitions) {
    const count = topicCounts.get(topic) || 0;
    if (count) tabs.push([label, topic, count]);
  }
  for (const [topic, count] of topicCounts) {
    if (!definitions.some(([, knownTopic]) => knownTopic === topic)) tabs.push([topic, topic, count]);
  }
  for (const [label, topic, count] of tabs) {
    const tab = element('button', 'topic-tab', '');
    tab.type = 'button';
    tab.dataset.filterTopic = topic;
    tab.setAttribute('aria-pressed', String(topic === 'all'));
    tab.classList.toggle('is-active', topic === 'all');
    tab.append(element('span', 'topic-tab-label', label), element('span', 'topic-tab-count', String(count)));
    tab.addEventListener('click', () => applyTopicFilter(topic));
    nav.append(tab);
  }
  nav.hidden = tabs.length <= 1;
  applyTopicFilter('all');
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}), { once: true });
}

function applyTopicFilter(topic) {
  document.querySelectorAll('.topic-tab').forEach((tab) => {
    const active = tab.dataset.filterTopic === topic;
    tab.classList.toggle('is-active', active);
    tab.setAttribute('aria-pressed', String(active));
  });
  document.querySelectorAll('.priority-section').forEach((section) => {
    let visibleGroups = 0;
    section.querySelectorAll('.topic-group').forEach((group) => {
      const visible = topic === 'all' || group.dataset.topic === topic;
      group.hidden = !visible;
      if (visible) visibleGroups += 1;
    });
    section.hidden = visibleGroups === 0 && !(topic === 'all' && section.querySelector('.empty-category'));
  });
}

function renderFinding(finding) {
  const card = element('article', 'finding');
  const top = element('div', 'finding-top');
  top.append(element('h3', '', finding.title));
  card.append(top);
  if (finding.kind === 'task') card.append(element('p', 'finding-deadline', `Deadline: ${finding.deadline || 'Not specified'}.`));
  card.append(element('p', '', finding.explanation));

  if (Array.isArray(finding.links) && finding.links.length) {
    const actions = element('div', 'finding-links');
    for (const link of finding.links) {
      try {
        const parsed = new URL(link.url);
        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') continue;
        const anchor = element('a', 'finding-link', link.label || 'Open link ↗');
        anchor.setAttribute('href', link.url);
        anchor.setAttribute('target', '_blank');
        anchor.setAttribute('rel', 'noopener noreferrer');
        actions.append(anchor);
      } catch { /* Invalid URLs are omitted instead of being repaired or guessed. */ }
    }
    if (actions.childElementCount) card.append(actions);
  }

  const sources = element('div', 'sources');
  sources.hidden = true;
  for (const message of finding.sources) {
    const box = element('div', 'source-message');
    const meta = [message.sender, message.timestamp].filter(Boolean).join(' · ');
    box.append(element('span', 'source-meta', meta || 'Source message'), document.createTextNode(message.text));
    sources.append(box);
  }
  const sourceButton = element('button', 'source-toggle', sourceLabel(false, finding.sources.length));
  sourceButton.type = 'button';
  sourceButton.setAttribute('aria-expanded', 'false');
  sourceButton.addEventListener('click', () => {
    sources.hidden = !sources.hidden;
    sourceButton.setAttribute('aria-expanded', String(!sources.hidden));
    sourceButton.textContent = sourceLabel(!sources.hidden, finding.sources.length);
  });
  card.append(sourceButton, sources);
  return card;
}

function sourceLabel(open, count) {
  return `${open ? 'Hide' : 'View'} source message${count > 1 ? 's' : ''} (${count})`;
}
