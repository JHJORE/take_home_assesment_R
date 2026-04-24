// TypeScript mirror of the Pydantic entities in
// `backend/src/readily/domain/entities.py`. Hand-synced; there is no generator
// in the repo yet. If you rename a field in the backend, update it here too.

export type TClaimMetadata = {
  topic_keywords: string[];
  entity_refs: string[];
};

export type TClaim = {
  claim: string;
  source_text: string;
  page: number | null;
  metadata: TClaimMetadata;
};

export type TQuestionMetadata = {
  lob: string[];
  reference: string;
  question_topics: string[];
};

export type TQuestion = {
  number: number;
  text: string;
  reference: string;
  claims: TClaim[];
  candidate_codes: string[];
  metadata: TQuestionMetadata;
};

export type TPolicyMeta = {
  code: string;
  file_path: string;
  title: string | null;
  applicable_to: string[];
  document_topics: string[];
  entity_refs: string[];
};

export type TPolicySection = {
  heading: string;
  page: number;
  metadata: TClaimMetadata;
  claims: TClaim[];
};

export type TPolicyDoc = {
  meta: TPolicyMeta;
  sections: TPolicySection[];
};

export type TMatchRecord = {
  policy_code: string;
  policy_claim: TClaim;
  section: string | null;
  rationale: string;
  confidence: number | null;
  policy_file_path: string;
  policy_title: string;
};

export type TQuestionClaimResult = {
  question_number: number;
  question_claim: TClaim;
  best_match: TMatchRecord | null;
  contradictions: TMatchRecord[];
};

export type TInfo = {
  ready: boolean;
  using_sample: boolean;
  has_questions: boolean;
  has_policies: boolean;
  has_results: boolean;
};

export type QuestionStatus =
  | "filled"
  | "contradiction"
  | "unmatched"
  | "unprocessed";
