import { AiToolClient } from "@/components/AiToolClient";

export default function ChatsPage() {
  return (
    <AiToolClient
      tool="chat"
      title="Welcome to Chat AI"
      subtitle="Ask for quick help with writing, planning, explanations, and summaries."
      placeholder="Ask whatever you want"
      actionLabel="Send"
      chatMode
    />
  );
}
