import { notFound } from "next/navigation";

import { getQuestions, getResults, getSources } from "@/lib/api";
import { PolicyPanel } from "@/components/PolicyPanel";
import { UploadGate } from "@/components/UploadGate";

export default async function QuestionPage({
  params,
}: {
  params: Promise<{ number: string }>;
}) {
  const { number: raw } = await params;
  const number = Number.parseInt(raw, 10);
  if (!Number.isFinite(number)) notFound();

  const [questions, results, sources] = await Promise.all([
    getQuestions(),
    getResults(number),
    getSources(),
  ]);

  const question = questions.find((q) => q.number === number);
  if (!question) notFound();

  return (
    <>
      <UploadGate />
      <PolicyPanel
        question={question}
        results={results}
        policies={sources.policies}
      />
    </>
  );
}
