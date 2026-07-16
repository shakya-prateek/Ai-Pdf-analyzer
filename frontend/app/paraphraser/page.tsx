import { AiToolClient } from "@/components/AiToolClient";

export default function ParaphraserPage() {
  return (
    <AiToolClient
      tool="paraphrase"
      title="Paraphraser"
      subtitle="Rewrite, correct, or translate text while keeping the meaning intact."
      placeholder="Type or paste your text here..."
      actionLabel="Generate"
      showLanguage
      modes={[
        { label: "Paraphrase", value: "simple" },
        { label: "Academic", value: "academic" },
        { label: "Shorter", value: "shorter" },
        { label: "Correct", value: "correct" },
        { label: "Translate", value: "translate" }
      ]}
    />
  );
}
