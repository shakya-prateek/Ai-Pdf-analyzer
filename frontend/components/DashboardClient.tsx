import Link from "next/link";
import {
  BrandIcon,
  FileIcon,
  FilesIcon,
  MessageIcon,
  SearchIcon,
  UploadIcon
} from "./Icons";

const tools = [
  {
    label: "Write",
    title: "Documents",
    description: "Upload PDFs, manage your library, and keep sources ready for analysis.",
    href: "/documents",
    tone: "blue",
    icon: FilesIcon
  },
  {
    label: "Research",
    title: "Investigator",
    description: "Ask grounded questions across your uploaded PDFs with page citations.",
    href: "/investigator",
    tone: "teal",
    icon: SearchIcon
  },
  {
    label: "Chat",
    title: "Chats",
    description: "Use a general AI assistant for quick writing and planning help.",
    href: "/chats",
    tone: "purple",
    icon: MessageIcon
  },
  {
    label: "Humanize",
    title: "Humanizer",
    description: "Make stiff text sound clearer, warmer, and more natural.",
    href: "/humanizer",
    tone: "green",
    icon: BrandIcon
  },
  {
    label: "Rewrite",
    title: "Paraphraser",
    description: "Rewrite, correct, or translate text while preserving meaning.",
    href: "/paraphraser",
    tone: "orange",
    icon: FileIcon
  },
  {
    label: "Study",
    title: "Study with AI",
    description: "Generate quizzes, flashcards, and mind maps from your notes.",
    href: "/study",
    tone: "pink",
    icon: FilesIcon
  },
  {
    label: "Create",
    title: "Images",
    description: "Turn rough ideas into professional image prompts for presentations.",
    href: "/images",
    tone: "emerald",
    icon: UploadIcon
  }
];

export function DashboardClient() {
  return (
    <section className="res-page">
      <div className="res-hero">
        <div>
          <h1>Hi, what would you like to do today?</h1>
          <p>Pick a tool to get started. Everything is available from the sidebar, without login.</p>
        </div>
        <Link href="/documents" className="res-create res-create--large">
          <UploadIcon className="h-4 w-4" />
          Create new
        </Link>
      </div>

      <div className="tool-grid">
        {tools.map((tool) => {
          const Icon = tool.icon;
          return (
            <Link key={tool.href} href={tool.href} className={`tool-card tool-card--${tool.tone}`}>
              <div>
                <span className="tool-card__pill">{tool.label}</span>
                <h2>{tool.title}</h2>
                <p>{tool.description}</p>
              </div>
              <span className="tool-card__icon">
                <Icon className="h-8 w-8" />
              </span>
              <strong>Open -&gt;</strong>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
