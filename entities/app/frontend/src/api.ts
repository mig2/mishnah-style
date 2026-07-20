// Typed fetch wrapper for all backend endpoints

import type {
  DecisionsFile, EntitySummary, JobStatus, PipelineStatus,
  ProposalSummary, ProposalsFile, PromoteResult,
} from './types';

const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

// --- Pipeline ---

export const getPipelineStatus = () => get<PipelineStatus>('/pipeline/status');

export const startDetect = (mode: string, masechet?: string, backend?: string) =>
  post<{ job_id: string }>('/pipeline/detect', { mode, masechet, backend });

export const getDetectStatus = (jobId: string) =>
  get<JobStatus>(`/pipeline/detect/${jobId}`);

export const triggerPromote = (source: string) =>
  post<PromoteResult>('/pipeline/promote', { source });

export const triggerBuild = () => post<{ path: string; counts: Record<string, number> }>('/pipeline/build');

export const triggerRender = () => post<{ pages_written: number; path: string }>('/pipeline/render');

export const triggerEnrich = (masechet?: string) =>
  post<{ pages: number; marks: Record<string, number> }>('/pipeline/enrich', { masechet });

export const triggerValidate = () =>
  post<{ passed: boolean; files_ok: number; files_bad: number; errors: unknown[] }>('/pipeline/validate');

// --- Proposals ---

export const listProposals = () => get<ProposalSummary[]>('/proposals/');

export const getProposals = (slug: string) => get<ProposalsFile>(`/proposals/${slug}`);

export const getDecisions = (slug: string) => get<DecisionsFile>(`/proposals/decisions/${slug}`);

export const saveDecisions = (slug: string, decisions: DecisionsFile) =>
  put<{ saved: boolean }>(`/proposals/decisions/${slug}`, decisions);

export const patchDecision = (slug: string, action: string, norm: string, data: unknown) =>
  patch<{ updated: boolean }>(`/proposals/decisions/${slug}`, { action, norm, data });

// --- Entities ---

export const listEntities = (kind?: string, search?: string) => {
  const params = new URLSearchParams();
  if (kind) params.set('kind', kind);
  if (search) params.set('search', search);
  const q = params.toString();
  return get<EntitySummary[]>(`/entities/${q ? '?' + q : ''}`);
};

export const getEntity = (kind: string, slug: string) =>
  get<Record<string, unknown>>(`/entities/${kind}/${slug}`);

export const listMasechot = () => get<{ slug: string }[]>('/entities/masechot');
