import "server-only";

import { API_BASE } from "./env";
import type {
  QuestionStatus,
  TInfo,
  TPolicyDoc,
  TQuestion,
  TQuestionClaimResult,
} from "./schema";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`GET ${path} -> ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export function getInfo(): Promise<TInfo> {
  return fetchJson<TInfo>("/info");
}

export function getQuestions(): Promise<TQuestion[]> {
  return fetchJson<TQuestion[]>("/questions");
}

export function getPolicies(): Promise<TPolicyDoc[]> {
  return fetchJson<TPolicyDoc[]>("/policies");
}

export function getResults(
  questionNumber?: number,
): Promise<TQuestionClaimResult[]> {
  const qs =
    questionNumber !== undefined
      ? `?question_number=${encodeURIComponent(questionNumber)}`
      : "";
  return fetchJson<TQuestionClaimResult[]>(`/results${qs}`);
}

export function getResultsForQuestion(
  questionNumber: number,
): Promise<TQuestionClaimResult[]> {
  return getResults(questionNumber);
}

export type Row = {
  question: TQuestion;
  status: QuestionStatus;
};

export async function getQuestionRows(): Promise<Row[]> {
  const [questions, results] = await Promise.all([getQuestions(), getResults()]);
  return questions.map((q) => ({
    question: q,
    status: computeStatus(q, results),
  }));
}

export async function getSources(): Promise<{
  policies: TPolicyDoc[];
  usingSample: boolean;
}> {
  const [policies, info] = await Promise.all([getPolicies(), getInfo()]);
  return { policies, usingSample: info.using_sample };
}

function computeStatus(
  question: TQuestion,
  allResults: TQuestionClaimResult[],
): QuestionStatus {
  const results = allResults.filter(
    (r) => r.question_number === question.number,
  );
  if (results.length === 0) return "unprocessed";
  const hasContradiction = results.some((r) => r.contradictions.length > 0);
  if (hasContradiction) return "contradiction";
  const allMatched = results.every((r) => r.best_match !== null);
  if (allMatched) return "filled";
  return "unmatched";
}
