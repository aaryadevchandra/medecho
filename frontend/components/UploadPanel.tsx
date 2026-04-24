"use client";

import { useCallback, useRef, useState } from "react";

type Status = "idle" | "loading" | "success" | "error";

type UploadPanelProps = {
  onFileSelected: (file: File) => Promise<void>;
  onPendingFileChange?: () => void;
  status: Status;
  errorMessage: string | null;
  lastFilename: string | null;
};

export function UploadPanel({
  onFileSelected,
  onPendingFileChange,
  status,
  errorMessage,
  lastFilename,
}: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const acceptTypes = ".pdf,.txt,application/pdf,text/plain";

  const pickFile = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      const lower = file.name.toLowerCase();
      if (!lower.endsWith(".pdf") && !lower.endsWith(".txt")) {
        return;
      }
      setPendingFile(file);
      onPendingFileChange?.();
    },
    [onPendingFileChange]
  );

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleFile(e.target.files?.[0]);
      e.target.value = "";
    },
    [handleFile]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      handleFile(e.dataTransfer.files?.[0]);
    },
    [handleFile]
  );

  const onUploadClick = useCallback(async () => {
    if (!pendingFile || status === "loading") return;
    await onFileSelected(pendingFile);
  }, [onFileSelected, pendingFile, status]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">Upload document</h2>
      <p className="mt-1 text-base text-slate-600">
        PDF or TXT — we extract structured fields for your demo.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept={acceptTypes}
        className="hidden"
        onChange={onInputChange}
      />

      <div
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            pickFile();
          }
        }}
        onDragEnter={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={pickFile}
        className={`mt-5 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors ${
          dragActive
            ? "border-blue-500 bg-blue-50"
            : "border-slate-200 bg-slate-50 hover:border-blue-300 hover:bg-slate-100/80"
        }`}
      >
        <p className="m-0 text-lg font-medium text-slate-800">
          Drag and drop your file here
        </p>
        <p className="m-0 mt-2 text-base text-slate-600">or click to browse</p>
        <span className="mt-3 inline-block rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white">
          Choose file
        </span>
      </div>

      {pendingFile && (
        <p className="mt-4 text-base text-slate-700">
          Selected:{" "}
          <span className="font-medium text-slate-900">{pendingFile.name}</span>
        </p>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onUploadClick}
          disabled={!pendingFile || status === "loading"}
          className="inline-flex min-h-[48px] min-w-[140px] items-center justify-center rounded-xl bg-blue-600 px-6 text-base font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {status === "loading" ? (
            <span className="flex items-center gap-2">
              <Spinner />
              Extracting…
            </span>
          ) : (
            "Upload & extract"
          )}
        </button>
      </div>

      {status === "error" && errorMessage && (
        <div
          className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-base text-red-800"
          role="alert"
        >
          {errorMessage}
        </div>
      )}

      {status === "success" && lastFilename && (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-base text-emerald-900">
          Successfully extracted from{" "}
          <span className="font-semibold">{lastFilename}</span>
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="h-5 w-5 animate-spin text-white"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
