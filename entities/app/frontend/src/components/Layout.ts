// Shell layout: sidebar nav + content area

import { navigate } from '../router';

function el(tag: string, cls?: string, html?: string): HTMLElement {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

function navLink(label: string, hash: string): HTMLElement {
  const a = el('a', undefined, label) as HTMLAnchorElement;
  a.href = `#/${hash}`;
  a.onclick = (e) => { e.preventDefault(); navigate(hash); };
  const current = window.location.hash.replace(/^#\/?/, '');
  if (current === hash || current.startsWith(hash + '/')) {
    a.className = 'active';
  }
  return a;
}

export function Layout(content: HTMLElement): HTMLElement {
  const layout = el('div', 'layout');

  const sidebar = el('div', 'sidebar');
  sidebar.append(
    el('h1', undefined, 'Entities'),
    navLink('Dashboard', ''),
    navLink('Detect', 'detect'),
    navLink('Review', 'review'),
    navLink('Promote', 'promote'),
    navLink('Build', 'build'),
    navLink('Render', 'render'),
    navLink('Enrich', 'enrich'),
    el('hr'),
    navLink('Entities', 'entities'),
  );

  const main = el('div', 'content');
  main.appendChild(content);

  layout.append(sidebar, main);
  return layout;
}
