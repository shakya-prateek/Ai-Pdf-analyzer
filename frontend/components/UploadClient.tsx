"use client";

import Link from "next/link";
import {
  ChangeEvent,
  DragEvent,
  useCallback,
  useEffect,
  useRef,
  useState
} from "react";
import { apiFetch, Classification, DocumentRecord } from "@/lib/api";
import {
  CheckIcon,
  FileIcon,
  FilesIcon,
  MessageIcon,
  RefreshIcon,
  TrashIcon,
  UploadIcon
} from "./Icons";

const terminalStatuses = new Set(["indexed", "failed"]);
const statusOrder = ["uploaded", "parsing", "classifying", "indexing", "indexed"];
const allowedExtensions = new Set(["pdf", "png", "jpg", "jpeg", "txt"]);
const maxFileBytes = 10 * 1024 * 1024;

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function displayStatus(status: string) {
  return status === "indexed"
    ? "Ready"
    : status.charAt(0).toUpperCase() + status.slice(1);
}

export function UploadClient() {
  const [selected, setSelected] = useState<File[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [pendingDelete, setPendingDelete] = useState<DocumentRecord | null>(null);
  const [deletingId, setDeletingId] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    const data = await apiFetch<{ documents: DocumentRecord[] }>("/api/documents");
    setDocuments(data.documents);
    return data.documents;
  }, []);

  const beginPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const current = await loadDocuments();
        if (!current.some((document) => !terminalStatuses.has(document.status))) {
          stopPolling();
        }
      } catch {
        // Retain the current UI and recover on the next manual refresh.
      }
    }, 2000);
  }, [loadDocuments, stopPolling]);

  useEffect(() => {
    loadDocuments()
      .then((current) => {
        if (current.some((document) => !terminalStatuses.has(document.status))) {
          beginPolling();
        }
      })
      .catch(() => setError("Unable to connect to the document service."))
      .finally(() => setLoadingDocuments(false));
    return stopPolling;
  }, [beginPolling, loadDocuments, stopPolling]);

  const addFiles = (files: File[]) => {
    setError("");
    const valid: File[] = [];
    for (const file of files) {
      const extension = file.name.split(".").pop()?.toLowerCase() || "";
      if (!allowedExtensions.has(extension)) {
        setError(`${file.name} is not a supported file type.`);
        continue;
      }
      if (!file.size) {
        setError(`${file.name} is empty.`);
        continue;
      }
      if (file.size > maxFileBytes) {
        setError(`${file.name} exceeds the 10 MB limit.`);
        continue;
      }
      valid.push(file);
    }
    setSelected((current) => {
      const next = [...current];
      for (const file of valid) {
        if (!next.some((item) => item.name === file.name && item.size === file.size)) {
          next.push(file);
        }
      }
      return next.slice(0, 20);
    });
  };

  const chooseFiles = (event: ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(event.target.files || []));
    event.target.value = "";
  };

  const dropFiles = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    addFiles(Array.from(event.dataTransfer.files));
  };

  const upload = async () => {
    if (!selected.length || uploading) return;
    setUploading(true);
    setError("");
    const form = new FormData();
    selected.forEach((file) => form.append("files", file));
    try {
      await apiFetch("/api/upload", { method: "POST", body: form });
      setSelected([]);
      await loadDocuments();
      beginPolling();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const deleteSelectedDocument = async () => {
    if (!pendingDelete || deletingId) return;
    setDeletingId(pendingDelete.id);
    setError("");
    try {
      await apiFetch<void>(`/api/documents/${pendingDelete.id}`, { method: "DELETE" });
      setDocuments((current) =>
        current.filter((document) => document.id !== pendingDelete.id)
      );
      setPendingDelete(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to delete document.");
    } finally {
      setDeletingId("");
    }
  };

  const indexedCount = documents.filter((document) => document.status === "indexed").length;
  const processingCount = documents.filter(
    (document) => !terminalStatuses.has(document.status)
  ).length;
  const failedCount = documents.filter((document) => document.status === "failed").length;

  return (
    <main className="library-shell">
      <div className="page-heading page-heading--library">
        <div>
          <p className="eyebrow">Source management</p>
          <h1>Build your document library</h1>
          <p>Upload files, monitor indexing, and remove sources you no longer need.</p>
        </div>
        <Link href="/investigator" className="secondary-button">
          <MessageIcon className="h-4 w-4" />
          Ask documents
        </Link>
      </div>

      <section className="metrics-grid" aria-label="Document statistics">
        <Metric
          label="Total documents"
          value={loadingDocuments ? "—" : documents.length}
          icon={<FilesIcon className="h-5 w-5" />}
        />
        <Metric
          label="Ready to search"
          value={loadingDocuments ? "—" : indexedCount}
          icon={<CheckIcon className="h-5 w-5" />}
          tone="success"
        />
        <Metric
          label="Processing"
          value={loadingDocuments ? "—" : processingCount}
          icon={<RefreshIcon className="h-5 w-5" />}
          tone="warning"
        />
        <Metric
          label="Needs attention"
          value={loadingDocuments ? "—" : failedCount}
          icon={<FileIcon className="h-5 w-5" />}
          tone="danger"
        />
      </section>

      <div className="library-grid">
        <section className="upload-panel">
          <div className="section-heading">
            <div>
              <h2>Upload sources</h2>
              <p>Files stay local and are converted into searchable page evidence.</p>
            </div>
          </div>

          <div
            className={dragging ? "drop-zone drop-zone--active" : "drop-zone"}
            onDragEnter={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => {
              if (event.currentTarget === event.target) setDragging(false);
            }}
            onDrop={dropFiles}
          >
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              onChange={chooseFiles}
              className="sr-only"
            />
            <span className="drop-zone__icon"><UploadIcon className="h-6 w-6" /></span>
            <h3>Drop documents here</h3>
            <p>PDF, PNG, JPG, JPEG, or TXT. Maximum 10 MB per file.</p>
            <button
              type="button"
              className="secondary-button"
              onClick={() => inputRef.current?.click()}
            >
              Browse files
            </button>
          </div>

          {selected.length > 0 && (
            <div className="selected-files">
              <div className="selected-files__header">
                <p>{selected.length} file{selected.length === 1 ? "" : "s"} selected</p>
                <button type="button" onClick={() => setSelected([])}>Clear all</button>
              </div>
              <div className="selected-files__list">
                {selected.map((file) => (
                  <div key={`${file.name}-${file.size}`} className="selected-file">
                    <span><FileIcon className="h-4 w-4" /></span>
                    <div>
                      <p>{file.name}</p>
                      <small>{formatBytes(file.size)}</small>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setSelected((current) => current.filter((item) => item !== file))
                      }
                      aria-label={`Remove ${file.name}`}
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && <div className="alert alert--error mt-4">{error}</div>}

          <button
            type="button"
            onClick={upload}
            disabled={!selected.length || uploading}
            className="primary-button mt-5 w-full justify-center"
          >
            <UploadIcon className="h-4 w-4" />
            {uploading
              ? "Uploading files"
              : `Upload ${selected.length ? selected.length : ""} file${selected.length === 1 ? "" : "s"}`}
          </button>
          <p className="mt-3 text-center text-xs leading-5 text-slate-400">
            Up to 20 files per batch. PDFs are limited to 50 pages.
          </p>
        </section>

        <section className="documents-panel">
          <div className="section-heading">
            <div>
              <h2>Library status</h2>
              <p>Ready files can be searched immediately from the analyst workspace.</p>
            </div>
            <button
              type="button"
              onClick={() => void loadDocuments()}
              className="icon-button"
              aria-label="Refresh documents"
              title="Refresh"
            >
              <RefreshIcon className="h-4 w-4" />
            </button>
          </div>

          <div className="document-list">
            {loadingDocuments ? (
              <div className="list-empty">Loading document library…</div>
            ) : documents.length === 0 ? (
              <div className="list-empty">
                <FilesIcon className="mx-auto h-7 w-7 text-slate-300" />
                <p>No documents uploaded</p>
                <span>Add a file to begin building your searchable library.</span>
              </div>
            ) : (
              documents.map((document) => (
                <DocumentRow
                  key={document.id}
                  document={document}
                  deleting={deletingId === document.id}
                  onDelete={() => setPendingDelete(document)}
                />
              ))
            )}
          </div>
        </section>
      </div>

      {pendingDelete && (
        <div
          className="confirm-modal"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !deletingId) {
              setPendingDelete(null);
            }
          }}
        >
          <section
            className="confirm-modal__panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-document-title"
          >
            <span className="confirm-modal__icon"><TrashIcon className="h-5 w-5" /></span>
            <h2 id="delete-document-title">Delete this document?</h2>
            <p>
              <strong>{pendingDelete.original_name}</strong> and its indexed pages will be
              permanently removed from this workspace.
            </p>
            <div className="confirm-modal__actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setPendingDelete(null)}
                disabled={Boolean(deletingId)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger-button"
                onClick={() => void deleteSelectedDocument()}
                disabled={Boolean(deletingId)}
              >
                <TrashIcon className="h-4 w-4" />
                {deletingId ? "Deleting" : "Delete document"}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function Metric({
  label,
  value,
  icon,
  tone = "default"
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  return (
    <article className="metric-card">
      <span className={`metric-card__icon metric-card__icon--${tone}`}>{icon}</span>
      <div>
        <strong>{value}</strong>
        <p>{label}</p>
      </div>
    </article>
  );
}

function DocumentRow({
  document,
  deleting,
  onDelete
}: {
  document: DocumentRecord;
  deleting: boolean;
  onDelete: () => void;
}) {
  const currentIndex = statusOrder.indexOf(document.status);
  const processing = !terminalStatuses.has(document.status);
  return (
    <article className="document-row">
      <div className="document-row__top">
        <span className="file-type">{document.original_name.split(".").pop()?.slice(0, 4) || "FILE"}</span>
        <div className="min-w-0 flex-1">
          <h3 title={document.original_name}>{document.original_name}</h3>
          <p>
            {document.classification
              ? document.classification.document_type.replaceAll("_", " ")
              : "Classification pending"}
          </p>
        </div>
        <div className="document-row__actions">
          <span className={`status-badge status-badge--${document.status}`}>
            {processing && <span className="status-spinner" />}
            {displayStatus(document.status)}
          </span>
          <button
            type="button"
            className="document-delete"
            onClick={onDelete}
            disabled={processing || deleting}
            aria-label={`Delete ${document.original_name}`}
            title={processing ? "Available after processing finishes" : "Delete document"}
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {processing && currentIndex >= 0 && (
        <div className="processing-track" aria-label={`Current status: ${document.status}`}>
          {statusOrder.map((status, index) => (
            <span key={status} className={index <= currentIndex ? "processing-track__active" : ""} />
          ))}
        </div>
      )}

      {document.error_message && (
        <div className="alert alert--error mt-4">{document.error_message}</div>
      )}
      {document.classification && (
        <ClassificationSummary classification={document.classification} />
      )}
    </article>
  );
}

function ClassificationSummary({ classification }: { classification: Classification }) {
  return (
    <div className="classification">
      <p>{classification.summary}</p>
      <div className="classification__tags">
        {classification.topics.slice(0, 3).map((topic) => (
          <span key={topic}>{topic}</span>
        ))}
        <span className={`sensitivity sensitivity--${classification.sensitivity.level}`}>
          {classification.sensitivity.level} sensitivity
        </span>
      </div>
    </div>
  );
}
