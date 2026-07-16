import { AiToolClient } from "@/components/AiToolClient";

export default function HumanizerPage() {
  return (
    <AiToolClient
      tool="humanize"
      title="Human tone"
      subtitle="Polish stiff or robotic text into clear, professional writing."
      placeholder="Type or paste your text here..."
      actionLabel="Humanize text"
      modes={[
        { label: "Original", value: "original" },
        { label: "Professional", value: "professional" },
        { label: "Warm", value: "warm" }
      ]}
    />
  );
}
