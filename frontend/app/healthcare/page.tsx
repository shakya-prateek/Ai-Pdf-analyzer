import { AiToolClient } from "@/components/AiToolClient";

export default function HealthcarePage() {
  return (
    <AiToolClient
      tool="healthcare_report"
      title="Healthcare report explainer"
      subtitle="Paste lab-report text to summarize biomarkers, trends, and clinician follow-up questions. Educational only, not medical advice."
      placeholder="Paste blood, urine, stool, sperm, pap, or other lab-report text here..."
      actionLabel="Analyze report"
      modes={[
        { label: "Biomarker summary", value: "biomarker_summary" },
        { label: "Trend review", value: "trend_review" },
        { label: "Clinician questions", value: "clinician_questions" }
      ]}
    />
  );
}
