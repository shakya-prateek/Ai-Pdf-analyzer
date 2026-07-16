"use client";

import { FormEvent, useState } from "react";
import { apiFetch } from "@/lib/api";
import { FilesIcon, SendIcon } from "./Icons";

const studyTools = [
  {
    tool: "quiz",
    label: "Practice with quizzes",
    description: "Generate multiple-choice questions with explanations.",
    tone: "green"
  },
  {
    tool: "flashcards",
    label: "Memorize with flashcards",
    description: "Create quick Q&A cards from your notes.",
    tone: "pink"
  },
  {
    tool: "mind_map",
    label: "Organize with mind maps",
    description: "Visualize ideas as a Mermaid mind map.",
    tone: "blue"
  }
] as const;

type StudyTool = (typeof studyTools)[number]["tool"];

export function StudyClient() {
  const [active, setActive] = useState<StudyTool>("quiz");
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim() || loading) return;
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch<{ result: string }>("/api/tools/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: active, text: text.trim() })
      });
      setResult(response.result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to generate study material.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="res-page study-page">
      <div className="res-hero res-hero--stack">
        <h1>Study from your material</h1>
        <p>Paste notes or summaries and generate quizzes, flashcards, and mind maps.</p>
      </div>

      <div className="study-card-grid">
        {studyTools.map((item) => (
          <button
            key={item.tool}
            type="button"
            className={active === item.tool ? `study-card study-card--${item.tone} study-card--active` : `study-card study-card--${item.tone}`}
            onClick={() => setActive(item.tool)}
          >
            <span>Practice</span>
            <strong>{item.label}</strong>
            <p>{item.description}</p>
            <em>Get started -&gt;</em>
          </button>
        ))}
      </div>

      <div className="split-tool split-tool--study">
        <form className="tool-input-panel" onSubmit={submit}>
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste study notes, PDF summary, or class material here..."
            maxLength={12000}
          />
          <div className="tool-panel__footer">
            <span>Characters: {text.length}/12000</span>
            <button type="submit" className="primary-button" disabled={!text.trim() || loading}>
              <SendIcon className="h-4 w-4" />
              {loading ? "Generating" : "Generate"}
            </button>
          </div>
        </form>
        <section className="tool-output-panel">
          {result ? (
            <div className="tool-result">{result}</div>
          ) : (
            <div className="tool-placeholder">
              <FilesIcon className="h-9 w-9" />
              <p>Your study output will appear here</p>
            </div>
          )}
        </section>
      </div>
      {error && <div className="alert alert--error mt-4">{error}</div>}
    </section>
  );
}
