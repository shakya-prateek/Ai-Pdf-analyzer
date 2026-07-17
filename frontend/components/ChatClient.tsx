"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, Citation, DocumentRecord } from "@/lib/api";
import { CitationCards } from "./CitationCards";
import {
  FilesIcon,
  MessageIcon,
  MicIcon,
  SearchIcon,
  SendIcon
} from "./Icons";

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

type SpeechRecognitionType = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: any) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};

const suggestions = [
  "Create an executive summary.",
  "Extract strengths, risks, and gaps.",
  "How many documents are uploaded?"
];

function InlineAnswer({ text }: { text: string }) {
  const parts = text.split(/(\[[^\]]+,\s*page\s+\d+\])/gi);
  return (
    <>
      {parts.map((part, index) =>
        /^\[[^\]]+,\s*page\s+\d+\]$/i.test(part) ? (
          <span key={index} className="citation">{part}</span>
        ) : part
      )}
    </>
  );
}

function AnswerText({ text }: { text: string }) {
  return (
    <div className="answer-content">
      {text.split("\n").map((rawLine, index) => {
        const line = rawLine.trim();
        if (!line) return <span key={index} className="answer-spacer" />;
        const heading = line.match(/^(?:#{2,3}\s+|\*\*)(.+?)(?:\*\*)?$/);
        if (heading) {
          return <h4 key={index}><InlineAnswer text={heading[1]} /></h4>;
        }
        const bullet = line.match(/^(?:[-*])\s+(.+)$/);
        if (bullet) {
          return (
            <div key={index} className="answer-bullet">
              <span aria-hidden="true">•</span>
              <p><InlineAnswer text={bullet[1]} /></p>
            </div>
          );
        }
        return <p key={index}><InlineAnswer text={line} /></p>;
      })}
    </div>
  );
}

export function ChatClient() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [listening, setListening] = useState(false);
  const [speechMessage, setSpeechMessage] = useState("");
  const [indexedCount, setIndexedCount] = useState<number | null>(null);
  const [backendState, setBackendState] = useState<"connecting" | "online" | "offline">("connecting");
  const [aiProvider, setAiProvider] = useState("Local");
  const recognitionRef = useRef<SpeechRecognitionType | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const backendOnline = backendState === "online";

  const loadOverview = useCallback(async (active = true) => {
    try {
      const [data, capabilities] = await Promise.all([
        apiFetch<{ documents: DocumentRecord[] }>("/api/documents"),
        apiFetch<{ ai_enabled: boolean; provider: string }>("/api/capabilities")
      ]);
      if (!active) return;
      setBackendState("online");
      setIndexedCount(data.documents.filter((document) => document.status === "indexed").length);
      setAiProvider(
        capabilities.ai_enabled
          ? `${capabilities.provider.charAt(0).toUpperCase()}${capabilities.provider.slice(1)} AI`
          : "Local fallback"
      );
    } catch {
      if (!active) return;
      setBackendState("offline");
      setIndexedCount(null);
      setAiProvider("Offline");
    }
  }, []);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const refresh = async () => {
      await loadOverview(active);
      if (active) timer = window.setTimeout(refresh, 15_000);
    };
    void refresh();
    return () => {
      active = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [loadOverview]);

  useEffect(() => {
    if (messages.length || loading) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, loading]);

  useEffect(() => () => recognitionRef.current?.stop(), []);

  const toggleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechMessage("Voice input is not supported by this browser.");
      return;
    }
    const recognition: SpeechRecognitionType = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onresult = (event: any) => {
      let transcript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        transcript += event.results[index][0].transcript;
      }
      setInput(transcript);
    };
    recognition.onerror = () => {
      setListening(false);
      setSpeechMessage("Voice input stopped. You can continue by typing.");
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    setSpeechMessage("");
    setListening(true);
    recognition.start();
  };

  const askQuestion = async (question: string) => {
    if (!question.trim() || loading) return;
    if (!backendOnline) {
      setError(
        backendState === "connecting"
          ? "The document service is waking up. Please wait a moment."
          : "The document service is temporarily unavailable. Please try again."
      );
      return;
    }
    if (!indexedCount) {
      setError("Upload and finish indexing at least one document before asking a question.");
      void loadOverview();
      return;
    }
    const cleanQuestion = question.trim();
    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((current) => [...current, { role: "user", content: cleanQuestion }]);
    setInput("");
    setError("");
    setLoading(true);
    await new Promise<void>((resolve) => window.setTimeout(resolve, 0));
    try {
      const response = await apiFetch<{ answer: string; citations: Citation[] }>("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: cleanQuestion, history })
      });
      setMessages((current) => [
        ...current,
        { role: "assistant", content: response.answer, citations: response.citations }
      ]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The document service is unavailable.");
    } finally {
      setLoading(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void askQuestion(input);
  };

  return (
    <main className="workspace-shell">
      <section className="workspace-main">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Document Q&amp;A</p>
            <h2>Analyze your source documents</h2>
            <p>Professional answers with page references and source previews.</p>
          </div>
          <div className="page-heading__actions">
            {messages.length > 0 && (
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  setMessages([]);
                  void apiFetch("/api/chat/history", { method: "DELETE" });
                }}
              >
                Clear conversation
              </button>
            )}
            <button
              type="button"
              className={`api-service api-service--${backendState}`}
              onClick={() => void loadOverview()}
              aria-label="Refresh API service status"
              title="Refresh API status"
            >
              <span />
              {backendOnline
                ? "API online"
                : backendState === "connecting"
                  ? "API waking up"
                  : "API unavailable"}
            </button>
          </div>
        </div>

        <div className="chat-panel">
          <div className="chat-panel__header">
            <div className="flex items-center gap-3">
              <span className="panel-icon"><MessageIcon className="h-4 w-4" /></span>
              <div>
                <h3>Document analyst</h3>
                <p>Evidence-backed responses from indexed pages</p>
              </div>
            </div>
            <span className="secure-label">{aiProvider} · Citations on</span>
          </div>

          <div className="chat-feed" aria-live="polite">
            {!messages.length && (
              <div className="empty-chat">
                <span className="empty-chat__icon"><SearchIcon className="h-6 w-6" /></span>
                {backendOnline && indexedCount === 0 ? (
                  <>
                    <h3>Upload a document to start</h3>
                    <p>
                      Upload a PDF, image, or text file. Once indexing finishes, answers
                      and citations will appear here.
                    </p>
                    <Link href="/documents" className="primary-button">
                      <FilesIcon className="h-4 w-4" />
                      Upload documents
                    </Link>
                  </>
                ) : (
                  <>
                    <h3>{backendOnline ? "What would you like to find?" : backendState === "connecting" ? "Starting document service" : "Document service unavailable"}</h3>
                    <p>
                      {backendOnline
                        ? "Ask a question, request a summary, or extract key details."
                        : backendState === "connecting"
                          ? "The service is waking up and will be ready shortly."
                          : "The service could not be reached. Please retry in a moment."}
                    </p>
                    {backendOnline && (
                      <div className="suggestion-list">
                        {suggestions.map((suggestion) => (
                          <button
                            key={suggestion}
                            type="button"
                            onClick={() => void askQuestion(suggestion)}
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {messages.map((message, index) => (
              <article
                key={`${message.role}-${index}`}
                className={message.role === "user" ? "message message--user" : "message message--assistant"}
              >
                <div className="message__meta">
                  {message.role === "user" ? "You" : "AskMyPDF AI"}
                </div>
                <div className="message__body">
                  {message.role === "assistant" ? (
                    <AnswerText text={message.content} />
                  ) : (
                    <p className="text-[15px] leading-7">{message.content}</p>
                  )}
                </div>
                {message.role === "assistant" && (
                  <CitationCards citations={message.citations || []} />
                )}
              </article>
            ))}

            {loading && (
              <div className="message message--assistant">
                <div className="message__meta">AskMyPDF AI</div>
                <div className="message__body">
                  <div className="searching-state">
                    <span /><span /><span />
                    Searching relevant pages
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={submit} className="composer">
            {error && <div className="alert alert--error">{error}</div>}
            {speechMessage && <div className="alert alert--neutral">{speechMessage}</div>}
            <div className="composer__field">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                rows={2}
                maxLength={4000}
                placeholder="Ask a question about your indexed documents"
                aria-label="Question"
                disabled={!backendOnline || indexedCount === 0}
              />
              <div className="composer__actions">
                <button
                  type="button"
                  onClick={toggleVoice}
                  className={listening ? "icon-button icon-button--active" : "icon-button"}
                  aria-label={listening ? "Stop voice input" : "Start voice input"}
                  title={listening ? "Stop listening" : "Voice input"}
                >
                  <MicIcon className="h-4 w-4" />
                </button>
                <button
                  type="submit"
                  disabled={!input.trim() || loading || !backendOnline || indexedCount === 0}
                  className="primary-button"
                >
                  Ask
                  <SendIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
            <p className="composer__hint">
              Enter to send · Shift + Enter for a new line · Answers may require source review
            </p>
          </form>
        </div>
      </section>
    </main>
  );
}
