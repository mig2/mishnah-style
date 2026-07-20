// Detect: trigger detection, show progress

import { Layout } from '../components/Layout';
import { listMasechot, startDetect, getDetectStatus } from '../api';

function el(tag: string, cls?: string, html?: string): HTMLElement {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

export function DetectView(): HTMLElement {
  const content = el('div');
  content.append(el('h2', undefined, 'Run Detection'));

  const form = el('div', 'card');

  // Mode
  const modeRow = el('div', 'row');
  modeRow.append(el('span', undefined, 'Mode:'));
  const modeSelect = document.createElement('select');
  for (const m of ['bold', 'llm']) {
    const o = document.createElement('option');
    o.value = m; o.textContent = m;
    modeSelect.append(o);
  }
  modeRow.append(modeSelect);
  form.append(modeRow);

  // Masechet
  const masRow = el('div', 'row');
  masRow.append(el('span', undefined, 'Masechet:'));
  const masSelect = document.createElement('select');
  const allOpt = document.createElement('option');
  allOpt.value = ''; allOpt.textContent = '(all)';
  masSelect.append(allOpt);
  masRow.append(masSelect);
  form.append(masRow);

  // Backend (for LLM mode)
  const backendRow = el('div', 'row');
  backendRow.append(el('span', undefined, 'Backend:'));
  const backendSelect = document.createElement('select');
  for (const b of ['claude-code', 'anthropic', 'ollama']) {
    const o = document.createElement('option');
    o.value = b; o.textContent = b;
    backendSelect.append(o);
  }
  backendRow.append(backendSelect);
  form.append(backendRow);

  // Run button
  const runBtn = el('button', 'primary mt', 'Run Detection') as HTMLButtonElement;
  form.append(runBtn);
  content.append(form);

  // Log area
  const logArea = el('div', 'mt');
  content.append(logArea);

  // Load masechot
  listMasechot().then(list => {
    for (const m of list) {
      const o = document.createElement('option');
      o.value = m.slug; o.textContent = m.slug;
      masSelect.append(o);
    }
  });

  // Run
  runBtn.onclick = async () => {
    runBtn.disabled = true;
    runBtn.textContent = 'Starting...';
    logArea.innerHTML = '';

    const log = el('div', 'log');
    logArea.append(log);

    try {
      const { job_id } = await startDetect(
        modeSelect.value,
        masSelect.value || undefined,
        modeSelect.value === 'llm' ? backendSelect.value : undefined,
      );

      // Poll for progress
      const poll = setInterval(async () => {
        try {
          const status = await getDetectStatus(job_id);
          log.textContent = status.progress.join('\n');
          log.scrollTop = log.scrollHeight;

          if (status.status !== 'running') {
            clearInterval(poll);
            runBtn.disabled = false;
            runBtn.textContent = 'Run Detection';

            if (status.status === 'done') {
              log.textContent += '\n\n✓ Detection complete';
            } else {
              log.textContent += '\n\n✗ Detection failed';
            }
          }
        } catch {
          // ignore poll errors
        }
      }, 2000);
    } catch (e: unknown) {
      runBtn.disabled = false;
      runBtn.textContent = 'Run Detection';
      logArea.innerHTML = `<div class="card" style="color:var(--red)">Error: ${(e as Error).message}</div>`;
    }
  };

  return Layout(content);
}
