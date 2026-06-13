"use client";

import { useEffect, useState } from "react";
import { Citation } from "@/lib/api";
import { CloseIcon, ExternalIcon, FileIcon } from "./Icons";
import { ProtectedImage } from "./ProtectedImage";

export function CitationCards({ citations }: { citations: Citation[] }) {
  const [active, setActive] = useState<Citation | null>(null);

  useEffect(() => {
    if (!active) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActive(null);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [active]);

  if (!citations.length) return null;

  return (
    <>
      <div className="citations">
        <p className="citations__label">
          {citations.length} source{citations.length === 1 ? "" : "s"}
        </p>
        <div className="citations__grid">
          {citations.map((citation, index) => (
            <article
              key={`${citation.document_name}-${citation.page_number}-${index}`}
              className="citation-card"
            >
              <button
                type="button"
                onClick={() => setActive(citation)}
                className="citation-card__preview"
                aria-label={`Open ${citation.document_name}, page ${citation.page_number}`}
              >
                <ProtectedImage path={citation.page_image_url} alt="" />
                <span><ExternalIcon className="h-3.5 w-3.5" /> Open page</span>
              </button>
              <div className="citation-card__content">
                <div className="flex items-center gap-2">
                  <FileIcon className="h-4 w-4 shrink-0 text-blue-600" />
                  <p title={citation.document_name}>{citation.document_name}</p>
                  <span>p. {citation.page_number}</span>
                </div>
                <blockquote>{citation.quoted_text}</blockquote>
              </div>
            </article>
          ))}
        </div>
      </div>

      {active && (
        <div
          className="document-modal"
          role="dialog"
          aria-modal="true"
          aria-label={`${active.document_name}, page ${active.page_number}`}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setActive(null);
          }}
        >
          <div className="document-modal__panel">
            <div className="document-modal__header">
              <div>
                <p>{active.document_name}</p>
                <span>Page {active.page_number}</span>
              </div>
              <button
                type="button"
                onClick={() => setActive(null)}
                className="icon-button"
                aria-label="Close page preview"
              >
                <CloseIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="document-modal__body">
              <ProtectedImage
                path={active.page_image_url}
                alt={`${active.document_name}, page ${active.page_number}`}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
