// Review: the core proposal review view

import { Layout } from '../components/Layout';
import { ProposalCard } from '../components/ProposalCard';
import { listProposals, getProposals } from '../api';
import { navigate } from '../router';
import type { ProposalsFile } from '../types';

function el(tag: string, cls?: string, html?: string): HTMLElement {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

function ReviewSelector(): HTMLElement {
  const content = el('div');
  content.append(el('h2', undefined, 'Review Proposals'));
  content.append(el('p', 'refs', 'Select a masechet to review:'));

  const list = el('div', 'mt');
  list.innerHTML = 'Loading...';
  content.append(list);

  listProposals().then(proposals => {
    list.innerHTML = '';
    if (proposals.length === 0) {
      list.append(el('p', 'refs', 'No proposals found. Run detection first.'));
      return;
    }
    for (const p of proposals) {
      const card = el('div', 'card');
      const row = el('div', 'row');
      row.append(
        el('strong', undefined, p.slug),
        el('span', 'badge', p.mode || '?'),
        el('span', 'refs', `${p.counts.new ?? '?'} new, ${p.counts.known ?? '?'} known`),
      );
      const btn = el('button', 'primary', 'Review') as HTMLButtonElement;
      btn.onclick = () => navigate(`review/${p.slug}`);
      row.append(btn);
      card.append(row);
      list.append(card);
    }
  });

  return content;
}

function ReviewMasechet(slug: string): HTMLElement {
  const content = el('div');
  content.append(el('h2', undefined, `Review: ${slug}`));

  const stats = el('div', 'refs mb');
  content.append(stats);

  const filterRow = el('div', 'row mb');
  const kindFilter = document.createElement('select');
  for (const k of ['all', 'person', 'place', 'plant']) {
    const o = document.createElement('option');
    o.value = k; o.textContent = k;
    kindFilter.append(o);
  }
  filterRow.append(el('span', undefined, 'Filter:'), kindFilter);
  content.append(filterRow);

  const proposalBox = el('div');
  proposalBox.innerHTML = 'Loading...';
  content.append(proposalBox);

  const ambiguousBox = el('div', 'mt');
  content.append(ambiguousBox);

  let data: ProposalsFile | null = null;

  function renderProposals() {
    if (!data) return;
    proposalBox.innerHTML = '';

    const entries = Object.entries(data.proposals);
    const filter = kindFilter.value;
    const filtered = filter === 'all' ? entries : entries.filter(([, p]) => p.kind === filter);

    stats.textContent = `${filtered.length} proposals (${entries.length} total), ${data.run.counts.known ?? 0} known`;

    if (filtered.length === 0) {
      proposalBox.append(el('p', 'refs', 'No proposals to review.'));
      return;
    }

    for (const [norm, proposal] of filtered) {
      proposalBox.append(ProposalCard(norm, proposal, slug));
    }

    // Ambiguous
    if (data.ambiguous && data.ambiguous.length > 0) {
      ambiguousBox.innerHTML = '';
      ambiguousBox.append(el('h3', 'mt', `Ambiguous (${data.ambiguous.length})`));
      for (const a of data.ambiguous) {
        const card = el('div', 'card');
        card.append(
          el('span', `badge ${a.kind}`, a.kind),
          el('div', 'forms he', a.form),
          el('div', 'refs', `Candidates: ${a.candidates.join(', ')}`),
        );
        ambiguousBox.append(card);
      }
    }
  }

  kindFilter.onchange = renderProposals;

  getProposals(slug).then(d => {
    data = d;
    renderProposals();
  }).catch(e => {
    proposalBox.innerHTML = `<div class="card" style="color:var(--red)">Error: ${(e as Error).message}</div>`;
  });

  return content;
}

export function ReviewView(params: string[]): HTMLElement {
  const slug = params[0];
  if (slug) {
    return Layout(ReviewMasechet(slug));
  }
  return Layout(ReviewSelector());
}
