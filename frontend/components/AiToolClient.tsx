"use client";

import { FormEvent, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { MessageIcon, SendIcon } from "./Icons";

type ToolKind =
  | "chat"
  | "humanize"
  | "verify_ai"
  | "paraphrase"
  | "correct"
  | "translate"
  | "quiz"
  | "flashcards"
  | "mind_map"
  | "image_prompt"
  | "document_draft";

type ModeOption = {
  label: string;
  value: string;
};

type ToolMessage = {
  role: "user" | "assistant";
  content: string;
};

export function AiToolClient({
  tool,
  title,
  subtitle,
  placeholder,
  actionLabel,
  modes,
  showLanguage = false,
  chatMode = false
}: {
  tool: ToolKind;
  title: string;
  subtitle: string;
  placeholder: string;
  actionLabel: string;
  modes?: ModeOption[];
  showLanguage?: boolean;
  chatMode?: boolean;
}) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState(modes?.[0]?.value || "");
  const [targetLanguage, setTargetLanguage] = useState("Hindi");
  const [result, setResult] = useState("");
  const [messages, setMessages] = useState<ToolMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const selectedTool = useMemo(() => {
    if (tool !== "paraphrase") return tool;
    if (mode === "correct" || mode === "translate") return mode;
    return "paraphrase";
  }, [mode, tool]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim() || loading) return;
    const prompt = text.trim();
    setLoading(true);
    setError("");
    if (chatMode) {
      setMessages((current) => [...current, { role: "user", content: prompt }]);
    }
    try {
      const response = await apiFetch<{ result: string; provider: string }>("/api/tools/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool: selectedTool,
          text: prompt,
          mode,
          target_language: showLanguage ? targetLanguage : undefined,
          history: chatMode ? messages.slice(-8) : []
        })
      });
      if (chatMode) {
        setMessages((current) => [
          ...current,
          { role: "assistant", content: response.result }
        ]);
      } else {
        setResult(response.result);
      }
      setText("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The AI service is unavailable.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="res-page tool-workspace">
      <div className="tool-heading">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>

      {modes && (
        <div className="mode-tabs" role="tablist" aria-label={`${title} modes`}>
          {modes.map((option) => (
            <button
              key={option.value}
              type="button"
              className={mode === option.value ? "mode-tabs__item mode-tabs__item--active" : "mode-tabs__item"}
              onClick={() => setMode(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}

      {chatMode ? (
        <div className="simple-chat">
          <div className="simple-chat__feed">
            {messages.length === 0 ? (
              <div className="simple-empty">
                <MessageIcon className="h-8 w-8" />
                <h2>Welcome to Chat AI</h2>
                <p>Ask for writing help, planning, explanations, or quick summaries.</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <article key={`${message.role}-${index}`} className={`simple-message simple-message--${message.role}`}>
                  <p>{message.content}</p>
                </article>
              ))
            )}
            {loading && <div className="simple-loading">Thinking...</div>}
          </div>
          <ToolComposer
            text={text}
            setText={setText}
            placeholder={placeholder}
            submit={submit}
            loading={loading}
            actionLabel={actionLabel}
          />
        </div>
      ) : (
        <div className="split-tool">
          <form className="tool-input-panel" onSubmit={submit}>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder={placeholder}
              maxLength={12000}
            />
            <div className="tool-panel__footer">
              <span>Characters: {text.length}/12000</span>
              {showLanguage && (
                <input
                  value={targetLanguage}
                  onChange={(event) => setTargetLanguage(event.target.value)}
                  aria-label="Target language"
                />
              )}
              <button type="submit" className="primary-button" disabled={!text.trim() || loading}>
                <SendIcon className="h-4 w-4" />
                {loading ? "Working" : actionLabel}
              </button>
            </div>
          </form>

          <section className="tool-output-panel">
            {result ? (
              <div className="tool-result">{result}</div>
            ) : (
              <div className="tool-placeholder">
                <MessageIcon className="h-9 w-9" />
                <p>Your result will appear here</p>
              </div>
            )}
          </section>
        </div>
      )}

      {error && <div className="alert alert--error mt-4">{error}</div>}
    </section>
  );
}

function ToolComposer({
  text,
  setText,
  placeholder,
  submit,
  loading,
  actionLabel
}: {
  text: string;
  setText: (value: string) => void;
  placeholder: string;
  submit: (event: FormEvent) => void;
  loading: boolean;
  actionLabel: string;
}) {
  return (
    <form className="simple-composer" onSubmit={submit}>
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={placeholder}
        rows={1}
      />
      <button type="submit" disabled={!text.trim() || loading} aria-label={actionLabel}>
        <SendIcon className="h-5 w-5" />
      </button>
    </form>
  );
}
