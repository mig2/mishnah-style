// Card for a single entity proposal in the review view

import { patchDecision } from '../api';
import type { Proposal } from '../types';

const HE_MAP: Record<string, string> = {
  'א':'a','ב':'b','ג':'g','ד':'d','ה':'h','ו':'v','ז':'z','ח':'ch','ט':'t',
  'י':'y','כ':'k','ך':'k','ל':'l','מ':'m','ם':'m','נ':'n','ן':'n','ס':'s',
  'ע':'a','פ':'p','ף':'f','צ':'tz','ץ':'tz','ק':'k','ר':'r','ש':'sh','ת':'t',
};

function hebrewToSlug(he: string): string {
  const s = he.replace(/[\u0591-\u05C7]/g, '');
  let out = '';
  for (const c of s) {
    if (HE_MAP[c]) out += HE_MAP[c];
    else if (c === ' ' || c === '-') out += '-';
  }
  return out.replace(/-+/g, '-').replace(/(.)\1+/g, '$1$1').replace(/^-|-$/g, '').toLowerCase();
}

const TYPES: Record<string, string[]> = {
  person: ['tanna', 'amora', 'biblical', 'named-layperson', 'collective'],
  place: ['settlement', 'region', 'temple_structure', 'water_feature', 'legal_domain'],
  plant: ['species', 'genus_or_group', 'folk_category', 'product', 'plant_part'],
};

function el(tag: string, cls?: string, html?: string): HTMLElement {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

export function ProposalCard(
  norm: string,
  proposal: Proposal,
  slug: string,
  onUpdate?: () => void,
): HTMLElement {
  const card = el('div', 'card');
  card.dataset.norm = norm;

  // Badge + forms
  const badge = el('span', `badge ${proposal.kind}`, proposal.kind);
  const forms = el('div', 'forms he', proposal.forms.join(' · '));
  const refs = el('div', 'refs',
    `${proposal.refs.length} appearance(s): ${proposal.refs.slice(0, 8).join(', ')}${proposal.refs.length > 8 ? '…' : ''}`);

  card.append(badge, forms, refs);

  // Input row
  const row = el('div', 'row');

  const slugInput = document.createElement('input');
  slugInput.placeholder = 'slug';
  slugInput.value = proposal.suggested_slug || hebrewToSlug(proposal.forms[0]) || '';

  const enInput = document.createElement('input');
  enInput.placeholder = proposal.kind === 'plant' ? 'en_common' : 'english';

  const typeSelect = document.createElement('select');
  for (const t of (TYPES[proposal.kind] || [])) {
    const opt = document.createElement('option');
    opt.value = t;
    opt.textContent = t;
    typeSelect.append(opt);
  }

  const acceptBtn = el('button', 'success', '✓ accept') as HTMLButtonElement;
  const rejectBtn = el('button', 'danger', '✗ reject') as HTMLButtonElement;

  acceptBtn.onclick = async () => {
    if (card.classList.contains('accept')) {
      card.classList.remove('accept');
      await patchDecision(slug, 'undo', norm, {});
    } else {
      card.classList.remove('reject');
      card.classList.add('accept');
      const data: Record<string, unknown> = {
        kind: proposal.kind,
        slug: slugInput.value.trim(),
        variants: proposal.forms,
        refs: proposal.refs,
      };
      if (proposal.kind === 'plant') {
        data.term_type = typeSelect.value;
        data.term = { he: proposal.forms[0], en_common: enInput.value.trim() || undefined };
      } else {
        data.type = typeSelect.value;
        data.names = { he: proposal.forms[0], en: enInput.value.trim() || undefined };
      }
      await patchDecision(slug, 'accept', norm, data);
    }
    onUpdate?.();
  };

  rejectBtn.onclick = async () => {
    if (card.classList.contains('reject')) {
      card.classList.remove('reject');
      await patchDecision(slug, 'undo', norm, {});
    } else {
      card.classList.remove('accept');
      card.classList.add('reject');
      await patchDecision(slug, 'reject', norm, {
        form: proposal.forms[0], kind: proposal.kind, scope: 'global',
      });
    }
    onUpdate?.();
  };

  row.append(slugInput, enInput, typeSelect, acceptBtn, rejectBtn);
  card.append(row);
  return card;
}
