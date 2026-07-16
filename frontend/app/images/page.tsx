import { AiToolClient } from "@/components/AiToolClient";

export default function ImagesPage() {
  return (
    <AiToolClient
      tool="image_prompt"
      title="Images"
      subtitle="Convert a rough visual idea into a polished image-generation prompt."
      placeholder="Describe the image you want to create..."
      actionLabel="Create prompt"
      modes={[
        { label: "Studio", value: "studio" },
        { label: "Product", value: "product" },
        { label: "Illustration", value: "illustration" },
        { label: "Presentation", value: "presentation" }
      ]}
    />
  );
}
