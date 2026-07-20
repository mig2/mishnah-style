// Dashboard: pipeline status overview

import { Layout } from '../components/Layout';
import { getPipelineStatus } from '../api';
import { navigate } from '../router';

function el(tag: string, cls?: string, html?: string): HTMLElement {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

function statusCard(title: string, value: string, detail?: string): HTMLElement {
  const card = el('div', 'status-card');
  card.append(el('h3', undefined, title));
  card.append(el('div', 'value', value));
  if (detail) card.append(el('div', 'refs', detail));
  return card;
}

export function DashboardView(): HTMLElement {
  const content = el('div');
  content.append(el('h2', undefined, 'Pipeline Dashboard'));

  const grid = el('div', 'status-grid');
  grid.innerHTML = '<div class="status-card"><div class="value">Loading...</div></div>';
  content.append(grid);

  const actions = el('div', 'mt');
  actions.append(el('h3', undefined, 'Quick Actions'));
  const btnRow = el('div', 'row mt');

  for (const [label, hash] of [
    ['Detect', 'detect'], ['Review', 'review'], ['Promote', 'promote'],
    ['Build', 'build'], ['Render', 'render'], ['Enrich', 'enrich'],
  ] as const) {
    const btn = el('button', undefined, label) as HTMLButtonElement;
    btn.onclick = () => navigate(hash);
    btnRow.append(btn);
  }
  actions.append(btnRow);
  content.append(actions);

  // Load status
  getPipelineStatus().then(s => {
    grid.innerHTML = '';
    const total = s.entities.people + s.entities.places + s.entities.plants;
    grid.append(
      statusCard('Proposals', String(s.detect.proposal_files.length),
        s.detect.last_modified ? `Last: ${new Date(s.detect.last_modified).toLocaleDateString()}` : undefined),
      statusCard('Decisions', String(s.decisions.files.length),
        s.decisions.last_modified ? `Last: ${new Date(s.decisions.last_modified).toLocaleDateString()}` : undefined),
      statusCard('People', String(s.entities.people)),
      statusCard('Places', String(s.entities.places)),
      statusCard('Plants', String(s.entities.plants)),
      statusCard('Total Entities', String(total)),
      statusCard('Knowledge DB', s.knowledge_db.exists ? '✓' : '—',
        s.knowledge_db.last_modified ? `Built: ${new Date(s.knowledge_db.last_modified).toLocaleDateString()}` : undefined),
      statusCard('Site Pages', String(s.site.page_count)),
    );
  }).catch(e => {
    grid.innerHTML = `<div class="card" style="color:var(--red)">Error loading status: ${e.message}</div>`;
  });

  return Layout(content);
}
