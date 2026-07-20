// Entity browser: search/filter, detail view

import { Layout } from '../components/Layout';
import { listEntities, getEntity } from '../api';
import { navigate } from '../router';

function el(tag: string, cls?: string, html?: string): HTMLElement {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

export function EntitiesView(): HTMLElement {
  const content = el('div');
  content.append(el('h2', undefined, 'Entities'));

  const filterRow = el('div', 'row mb');
  const kindFilter = document.createElement('select');
  for (const k of ['', 'person', 'place', 'plant']) {
    const o = document.createElement('option');
    o.value = k; o.textContent = k || 'all';
    kindFilter.append(o);
  }
  const searchInput = document.createElement('input');
  searchInput.placeholder = 'Search...';
  filterRow.append(kindFilter, searchInput);
  content.append(filterRow);

  const tableBox = el('div');
  content.append(tableBox);

  let debounce: ReturnType<typeof setTimeout>;

  async function load() {
    const kind = kindFilter.value || undefined;
    const search = searchInput.value.trim() || undefined;
    try {
      const entities = await listEntities(kind, search);
      tableBox.innerHTML = '';

      if (entities.length === 0) {
        tableBox.append(el('p', 'refs', 'No entities found.'));
        return;
      }

      const table = document.createElement('table');
      const thead = el('tr');
      for (const h of ['Kind', 'Hebrew', 'English', 'Type', 'Appearances']) {
        thead.append(el('th', undefined, h));
      }
      table.append(thead);

      for (const e of entities) {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => navigate(`entities/${e.kind}/${e.slug}`);
        tr.append(
          el('td', undefined, `<span class="badge ${e.kind}">${e.kind}</span>`),
          el('td', 'he', e.he),
          el('td', undefined, e.en || '—'),
          el('td', undefined, e.type || '—'),
          el('td', undefined, String(e.appearance_count)),
        );
        table.append(tr);
      }

      tableBox.append(table);
    } catch (e: unknown) {
      tableBox.innerHTML = `<div class="card" style="color:var(--red)">Error: ${(e as Error).message}</div>`;
    }
  }

  kindFilter.onchange = load;
  searchInput.oninput = () => {
    clearTimeout(debounce);
    debounce = setTimeout(load, 300);
  };

  load();
  return Layout(content);
}

export function EntityDetailView(kind: string, slug: string): HTMLElement {
  const content = el('div');
  const back = el('a', undefined, '← Back to entities');
  back.setAttribute('href', '#/entities');
  content.append(back);
  content.append(el('h2', undefined, `${kind} / ${slug}`));

  const detail = el('div', 'card');
  detail.innerHTML = 'Loading...';
  content.append(detail);

  getEntity(kind, slug).then(doc => {
    detail.innerHTML = '';
    const pre = document.createElement('pre');
    pre.style.whiteSpace = 'pre-wrap';
    pre.style.fontFamily = 'monospace';
    pre.style.fontSize = '0.85rem';
    pre.textContent = JSON.stringify(doc, null, 2);
    detail.append(pre);
  }).catch(e => {
    detail.innerHTML = `<span style="color:var(--red)">Error: ${(e as Error).message}</span>`;
  });

  return Layout(content);
}
