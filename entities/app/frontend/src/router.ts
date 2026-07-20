// Simple hash-based router

type ViewFn = (params: string[]) => HTMLElement;

interface Route {
  pattern: RegExp;
  view: ViewFn;
}

const routes: Route[] = [];
let appEl: HTMLElement;

export function addRoute(pattern: RegExp, view: ViewFn) {
  routes.push({ pattern, view });
}

export function navigate(hash: string) {
  window.location.hash = hash;
}

export function initRouter(el: HTMLElement) {
  appEl = el;
  window.addEventListener('hashchange', render);
  render();
}

function render() {
  const hash = window.location.hash.replace(/^#\/?/, '');

  for (const route of routes) {
    const match = hash.match(route.pattern);
    if (match) {
      const params = match.slice(1);
      appEl.innerHTML = '';
      appEl.appendChild(route.view(params));
      return;
    }
  }

  // Default: first route (dashboard)
  if (routes.length > 0) {
    appEl.innerHTML = '';
    appEl.appendChild(routes[0].view([]));
  }
}
