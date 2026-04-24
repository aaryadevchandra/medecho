"use client";

import { useCallback, useState } from "react";
import { DocumentSummary } from "@/components/DocumentSummary";
import { QuestionAnswer } from "@/components/QuestionAnswer";
import { SampleDocument } from "@/components/SampleDocument";
import { UploadPanel } from "@/components/UploadPanel";
import { uploadAndExtract, type ExtractedJson } from "@/lib/api";

type UploadStatus = "idle" | "loading" | "success" | "error";

export default function HomePage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [extracted, setExtracted] = useState<ExtractedJson | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastFilename, setLastFilename] = useState<string | null>(null);
  const [qaPanelKey, setQaPanelKey] = useState(0);

  const handleUpload = useCallback(async (file: File) => {
    setStatus("loading");
    setError(null);
    try {
      const res = await uploadAndExtract(file);
      setSessionId(res.session_id);
      setExtracted(res.extracted);
      setLastFilename(res.filename);
      setQaPanelKey((k) => k + 1);
      setStatus("success");
    } catch (e) {
      setSessionId(null);
      setExtracted(null);
      setLastFilename(null);
      setError(e instanceof Error ? e.message : "Something went wrong");
      setStatus("error");
    }
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <h1 className="text-3xl font-bold tracking-tight text-blue-700 md:text-4xl">
            AfterCare
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-slate-600 md:text-xl">
            Turn medical documents into clear, structured patient instructions — then ask
            questions grounded in your document.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="grid gap-8 lg:grid-cols-2 lg:items-start">
          <div className="flex flex-col gap-8">
            <UploadPanel
              onFileSelected={handleUpload}
              onPendingFileChange={() => {
                setStatus("idle");
                setError(null);
                setSessionId(null);
                setExtracted(null);
                setLastFilename(null);
                setQaPanelKey((k) => k + 1);
              }}
              status={status}
              errorMessage={error}
              lastFilename={lastFilename}
            />
            <SampleDocument />
          </div>
          <div className="flex flex-col gap-8 lg:sticky lg:top-8">
            {extracted ? (
              <DocumentSummary data={extracted} />
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 p-8 text-center">
                <p className="text-lg text-slate-600">
                  After you upload a PDF or TXT, a readable summary of your document will
                  appear here — not raw JSON.
                </p>
              </div>
            )}
            <QuestionAnswer key={qaPanelKey} sessionId={sessionId} />
          </div>
        </div>
      </main>
    </div>
  );
}
