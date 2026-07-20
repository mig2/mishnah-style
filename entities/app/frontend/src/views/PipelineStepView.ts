// Generic view for simple pipeline steps: promote, build, render, enrich, validate

import { Layout } from '../components/Layout';
import { triggerPromote, triggerBuild, triggerRender, triggerEnrich, triggerValidate, listProposals } from '../api';

function el(tag: string, cls?: string, html?: string): HTMLElement {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

function simpleView(title: string, description: string, action: () => Promise<unknown>): HTMLElement {
  const content = el('div');
  content.append(el('h2', undefined, title));
  content.append(el('p', 'refs mb', description));

  const resultArea = el('div');
  const btn = el('button', 'primary', `Run ${title}`) as HTMLButtonElement;

  btn.onclick = async () => {
    btn.disabled = true;
    btn.textContent = 'Running...';
    resultArea.innerHTML = '';
    try {
      const result = await action();
      resultArea.innerHTML = '';
      const pre = el('div', 'card');
      pre.append(el('div', undefined, '✓ Complete'));
      pre.append(el('pre', undefined, JSON.stringify(result, null, 2)));
      resultArea.append(pre);
    } catch (e: unknown) {
      resultArea.innerHTML = `<div class="card" style="color:var(--red)">Error: ${(e as Error).message}</div>`;
    }
    btn.disabled = false;
    btn.textContent = `Run ${title}`;
  };

  content.append(btn, resultArea);
  return content;
}

export function PromoteView(): HTMLElement {
  const content = el('div');
  content.append(el('h2', undefined, 'Promote'));
  content.append(el('p', 'refs mb', 'Apply reviewed decisions: create entity stubs, add rejections and rules.'));

  const selectRow = el('div', 'row mb');
  selectRow.append(el('span', undefined, 'Source:'));
  const sourceSelect = document.createElement('select');
  selectRow.append(sourceSelect);
  content.append(selectRow);

  const resultArea = el('div');
  const btn = el('button', 'primary', 'Promote') as HTMLButtonElement;

  btn.onclick = async () => {
    const source = sourceSelect.value;
    if (!source) return;
    btn.disabled = true;
    btn.textContent = 'Promoting...';
    resultArea.innerHTML = '';
    try {
      const result = await triggerPromote(source);
      resultArea.innerHTML = '';
      const card = el('div', 'card');
      card.append(
        el('div', undefined, '✓ Promote complete'),
        el('div', 'refs', `Created: ${result.created.join(', ') || 'none'}`),
        el('div', 'refs', `Skipped: ${result.skipped.join(', ') || 'none'}`),
        el('div', 'refs', `Rejections added: ${result.rejections_added}`),
        el('div', 'refs', `Rules added: ${result.rules_added}`),
      );
      resultArea.append(card);
    } catch (e: unknown) {
      resultArea.innerHTML = `<div class="card" style="color:var(--red)">Error: ${(e as Error).message}</div>`;
    }
    btn.disabled = false;
    btn.textContent = 'Promote';
  };

  content.append(btn, resultArea);

  // Load decision files to populate source dropdown
  listProposals().then(proposals => {
    for (const p of proposals) {
      const o = document.createElement('option');
      o.value = p.slug; o.textContent = p.slug;
      sourceSelect.append(o);
    }
  });

  return Layout(content);
}

export function BuildView(): HTMLElement {
  return Layout(simpleView('Build', 'Compile entity YAML into knowledge.db.', triggerBuild));
}

export function RenderView(): HTMLElement {
  return Layout(simpleView('Render', 'Generate static entity pages, who\'s-who, map, and gallery.', triggerRender));
}

export function EnrichView(): HTMLElement {
  return Layout(simpleView('Enrich', 'Weave entity overlay into masechet copies.', () => triggerEnrich()));
}

export function ValidateView(): HTMLElement {
  return Layout(simpleView('Validate', 'Run schema validation on all entity YAML files.', triggerValidate));
}
