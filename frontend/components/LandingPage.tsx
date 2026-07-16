import Link from "next/link";
import {
  BrandIcon,
  CheckIcon,
  FileIcon,
  FilesIcon,
  MessageIcon,
  SearchIcon,
  UploadIcon
} from "./Icons";

const navItems = ["Services", "Intelligent tools", "Solutions", "Pricing", "Resources", "About Us"];

const pdfFeatures = [
  {
    title: "Instant PDF summary",
    description: "Turn long documents into clear summaries, decisions, risks, and next steps.",
    icon: FilesIcon
  },
  {
    title: "Ask your PDF",
    description: "Chat with uploaded documents and receive answers grounded in page evidence.",
    icon: MessageIcon
  },
  {
    title: "Extract key information",
    description: "Find names, dates, amounts, biomarkers, clauses, skills, and important facts.",
    icon: SearchIcon
  },
  {
    title: "Humanize and rewrite",
    description: "Improve text from PDFs with clearer tone, paraphrasing, translation, and corrections.",
    icon: FileIcon
  }
];

const tools = [
  "PDF Q&A with citations",
  "Document library",
  "Healthcare report explainer",
  "Humanizer",
  "Paraphraser",
  "Study quizzes",
  "Flashcards",
  "Image prompt studio"
];

export function LandingPage() {
  return (
    <main className="landing-page">
      <header className="landing-nav">
        <Link href="/" className="landing-brand" aria-label="AskMyPDF AI home">
          <span><BrandIcon className="h-6 w-6" /></span>
          <strong>AskMyPDF AI</strong>
        </Link>

        <nav className="landing-nav__links" aria-label="Landing navigation">
          {navItems.map((item) => (
            <a key={item} href={`#${item.toLowerCase().replaceAll(" ", "-")}`}>
              {item}
            </a>
          ))}
        </nav>

        <div className="landing-nav__actions">
          <span className="landing-language">En</span>
          <Link href="/workspace" className="landing-user" aria-label="Open workspace">
            <BrandIcon className="h-5 w-5" />
          </Link>
          <Link href="/documents" className="landing-start">
            Start for free
            <span>-&gt;</span>
          </Link>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-hero__panel">
          <p className="landing-kicker">AI PDF analyzer for students, teams, and researchers</p>
          <h1>Analyze PDF with AI</h1>
          <h2>The best AI workspace for PDF analysis</h2>
          <p>
            Summarize PDFs, extract relevant information, ask document questions, and
            transform source material into polished writing or study assets in seconds.
          </p>
          <div className="landing-hero__actions">
            <Link href="/documents" className="landing-primary">
              <UploadIcon className="h-5 w-5" />
              Upload your PDF
            </Link>
            <Link href="/investigator" className="landing-secondary">
              Ask a PDF question
            </Link>
          </div>
        </div>
      </section>

      <section className="landing-upload" id="services">
        <div className="landing-upload__card">
          <span><UploadIcon className="h-7 w-7" /></span>
          <div>
            <h2>Upload your .pdf file</h2>
            <p>Use PDF, images, or text files. Your workspace stays local-first and no login is required.</p>
          </div>
          <Link href="/documents">Analyze a PDF</Link>
        </div>
      </section>

      <section className="landing-section" id="intelligent-tools">
        <div className="landing-section__intro">
          <p>Instant PDF intelligence</p>
          <h2>Everything you need after upload</h2>
          <span>
            AskMyPDF AI combines document parsing, grounded answers, citations,
            writing tools, study helpers, and healthcare-safe lab report explanations.
          </span>
        </div>

        <div className="landing-feature-grid">
          {pdfFeatures.map((feature) => {
            const Icon = feature.icon;
            return (
              <article key={feature.title} className="landing-feature">
                <span><Icon className="h-6 w-6" /></span>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="landing-tools" id="solutions">
        <div>
          <p>With AskMyPDF AI you can...</p>
          <h2>Create, research, study, and analyze from one place</h2>
        </div>
        <div className="landing-tool-list">
          {tools.map((tool) => (
            <span key={tool}>
              <CheckIcon className="h-4 w-4" />
              {tool}
            </span>
          ))}
        </div>
      </section>

      <section className="landing-cta" id="pricing">
        <div>
          <h2>Start analyzing your documents now</h2>
          <p>No signup page, no complicated workspace key, just open the app and upload.</p>
        </div>
        <Link href="/workspace" className="landing-primary">
          Open workspace
          <span>-&gt;</span>
        </Link>
      </section>
    </main>
  );
}
