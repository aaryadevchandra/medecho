"use client";

import { useCallback, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { askSession } from "@/lib/api";

type Msg = { role: "user" | "assistant"; content: string };

type QuestionAnswerProps = {
  sessionId: string | null;
};

export function QuestionAnswer({ sessionId }: QuestionAnswerProps) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const send = useCallback(async () => {
    if (!sessionId || loading) return;
    const q = input.trim();
    if (!q) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: q }]);
    setLoading(true);
    try {
      const { answer } = await askSession(sessionId, q);
      setMessages((m) => [...m, { role: "assistant", content: answer }]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not get an answer.";
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `Sorry — ${msg}` },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  }, [sessionId, input, loading]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-900">Ask about this document</h2>
      <p className="mt-1 text-base text-slate-600">
        Answers combine your document with mainstream medical context and, when available, a
        short web instant summary — not document-only.
      </p>

      {!sessionId ? (
        <p className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-base text-slate-600">
          Upload a document first. Then you can ask questions in everyday language.
        </p>
      ) : (
        <>
          <div className="mt-4 max-h-[340px] space-y-4 overflow-y-auto rounded-xl border border-slate-100 bg-slate-50/80 p-4">
            {messages.length === 0 && (
              <p className="text-base text-slate-500">
                Try: “What medications am I on?” or “When should I follow up?”
              </p>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`rounded-xl px-4 py-3 text-base leading-relaxed ${
                  msg.role === "user"
                    ? "ml-8 bg-blue-600 text-white"
                    : "mr-4 border border-slate-200 bg-white text-slate-800"
                }`}
              >
                {msg.role === "assistant" ? (
                  <div
                    className={
                      "prose prose-slate prose-sm max-w-none " +
                      "prose-headings:font-semibold prose-headings:text-slate-900 " +
                      "prose-h2:text-lg prose-h3:text-base prose-h4:text-base " +
                      "prose-p:my-2 prose-li:my-0.5 " +
                      "prose-hr:border-slate-200 prose-hr:my-4 " +
                      "prose-strong:text-slate-900 prose-a:text-blue-600 prose-blockquote:border-slate-300"
                    }
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="m-0 whitespace-pre-wrap break-words">{msg.content}</p>
                )}
              </div>
            ))}
            {loading && (
              <div className="mr-4 rounded-xl border border-slate-200 bg-white px-4 py-3 text-base text-slate-500">
                Thinking…
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="block flex-1 text-sm font-medium text-slate-700">
              Your question
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                rows={2}
                disabled={loading}
                placeholder="Type a question…"
                className="mt-1 w-full resize-none rounded-xl border border-slate-200 px-3 py-2 text-base text-slate-900 shadow-inner outline-none ring-blue-200 focus:border-blue-400 focus:ring-2"
              />
            </label>
            <button
              type="button"
              onClick={() => void send()}
              disabled={loading || !input.trim()}
              className="inline-flex h-12 min-w-[120px] shrink-0 items-center justify-center rounded-xl bg-blue-600 px-5 text-base font-semibold text-white shadow-sm hover:bg-blue-700 disabled:bg-slate-300"
            >
              {loading ? "…" : "Ask"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
