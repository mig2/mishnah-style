// Mirrors backend Pydantic models

export interface PipelineStatus {
  detect: { proposal_files: string[]; last_modified: string | null };
  decisions: { files: string[]; last_modified: string | null };
  entities: { people: number; places: number; plants: number };
  knowledge_db: { exists: boolean; last_modified: string | null };
  site: { exists: boolean; page_count: number };
  validation: { last_run: string | null; passed: boolean | null };
}

export interface ProposalSummary {
  slug: string;
  mode: string | null;
  counts: Record<string, number>;
  modified: string | null;
}

export interface Proposal {
  kind: string;
  forms: string[];
  refs: string[];
  suggested_slug: string | null;
}

export interface Detected {
  form: string;
  kind: string;
  status: string;
  slug?: string;
  proposal?: string;
  candidates?: string[];
}

export interface MishnaDetected {
  ref: string;
  detected: Detected[];
}

export interface ProposalsFile {
  run: { mode: string; counts: Record<string, number>; partial?: boolean };
  mishnayot: MishnaDetected[];
  proposals: Record<string, Proposal>;
  ambiguous: { ref: string; form: string; kind: string; candidates: string[] }[];
}

export interface DecisionsFile {
  accept: Record<string, AcceptDecision> | AcceptDecision[];
  reject: Record<string, RejectDecision> | RejectDecision[];
  rules: Record<string, RuleDecision> | RuleDecision[];
}

export interface AcceptDecision {
  kind: string;
  slug: string;
  variants: string[];
  refs: string[];
  type?: string;
  term_type?: string;
  names?: { he?: string; en?: string };
  term?: { he?: string; en_common?: string };
}

export interface RejectDecision {
  form: string;
  kind: string;
  scope: string;
  ref?: string;
}

export interface RuleDecision {
  form: string;
  kind: string;
  resolve: string;
  scope: string;
  masechet?: string;
  ref?: string;
}

export interface EntitySummary {
  slug: string;
  kind: string;
  he: string;
  en: string;
  type: string;
  appearance_count: number;
}

export interface JobStatus {
  status: 'running' | 'done' | 'error';
  progress: string[];
  result: Record<string, unknown> | null;
}

export interface PromoteResult {
  created: string[];
  skipped: string[];
  rejections_added: number;
  rules_added: number;
}
