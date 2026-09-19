"use client";

import { useCallback, useEffect, useState } from "react";
import type { ExtractionResult } from "@/lib/types";

type Status = { ok: boolean; engineAvailable?: boolean; reason?: string; error?: string };
type Answer = {
  ok: boolean;
  answer?: string;
  citations?: unknown[];
  reasoning_path?: unknown[];
  error?: string;
};

const SUGGESTIONS = [
  "How many doors are in the door schedule, and what are their sizes?",
  "Which rooms are adjacent to the kitchen?",
  "What is the total measured floor area, and which rooms have no size label?",
  "Do the window tags on the plan agree with the window schedule?",
];

export default function AssistPanel({ result }: { result: ExtractionResult | null }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [pushing, setPushing] = useState(false);
  const [pushResult, setPushResult] = useState<string | null>(null);
  const [question, setQuestion] = useState(SUGGESTIONS[0]);
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);

  const call = useCallback(async (body: Record<string, unknown>) => {
    const res = await fetch("/api/veritasgraph", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return (await res.json()) as Status & Answer & Record<string, unknown>;
  }, []);

  useEffect(() => {
    let cancelled = false;
    call({ action: "status" })
      .then((s) => !cancelled && setStatus(s))
      .catch(() => !cancelled && setStatus({ ok: false, engineAvailable: false }));
    return () => {
      cancelled = true;
    };
  }, [call]);

  const available = status?.engineAvailable === true;

  async function push() {
    if (!result) return;
    setPushing(true);
    setPushResult(null);
    try {
      const res = await call({ action: "push", result });
      setPushResult(
        res.ok
          ? `Imported into VeritasGraph: ${JSON.stringify(
              Object.fromEntries(
                Object.entries(res).filter(([k]) => k !== "ok" && k !== "error"),
              ),
            )}`
          : `Import failed: ${res.error}`,
      );
    } finally {
      setPushing(false);
    }
  }

  async function ask() {
    setAsking(true);
    setAnswer(null);
    try {
      setAnswer(await call({ action: "ask", question }));
    } finally {
      setAsking(false);
    }
  }

  return (
    <div data-testid="assist-panel">
      <div
        className={`alert ${available ? "ok" : "info"}`}
        data-testid="assist-status"
        data-available={available ? "true" : "false"}
      >
        {status == null ? (
          <>Checking for a local VeritasGraph engine…</>
        ) : available ? (
          <>VeritasGraph engine detected. The graph can be imported and queried locally.</>
        ) : (
          <>
            <strong>AI assist unavailable.</strong> No local VeritasGraph engine or Ollama runtime
            was reachable{status.reason ? ` (${status.reason})` : ""}. Every extraction, graph and
            takeoff feature on this page is deterministic and keeps working without it.
          </>
        )}
      </div>

      <div className="panel">
        <h2>1 · Import this graph into VeritasGraph</h2>
        <p className="small muted">
          Pushes the extracted nodes and edges with <code>source_type=&quot;extracted&quot;</code>,
          so a reviewer&apos;s curated corrections outrank machine output on merge.
        </p>
        <button data-testid="assist-push" disabled={!result || pushing || !available} onClick={push}>
          {pushing ? <><span className="spinner" /> Importing…</> : "Import graph"}
        </button>
        {pushResult && (
          <p className="small mono" data-testid="assist-push-result" style={{ marginTop: 10 }}>
            {pushResult}
          </p>
        )}
      </div>

      <div className="panel">
        <h2>2 · Ask a grounded question</h2>
        <div className="row" style={{ marginBottom: 8 }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              className="secondary"
              style={{ fontSize: 12, padding: "4px 9px" }}
              data-testid="assist-suggestion"
              onClick={() => setQuestion(s)}
            >
              {s.length > 46 ? `${s.slice(0, 46)}…` : s}
            </button>
          ))}
        </div>
        <textarea
          aria-label="Question"
          data-testid="assist-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <div style={{ marginTop: 8 }}>
          <button data-testid="assist-ask" disabled={asking || !available || !question.trim()} onClick={ask}>
            {asking ? <><span className="spinner" /> Thinking…</> : "Ask"}
          </button>
        </div>
        {answer && (
          <div style={{ marginTop: 12 }} data-testid="assist-answer">
            {answer.ok ? (
              <>
                <p style={{ whiteSpace: "pre-wrap" }}>{answer.answer}</p>
                {Array.isArray(answer.citations) && answer.citations.length > 0 && (
                  <details>
                    <summary className="small muted">
                      {answer.citations.length} citation(s)
                    </summary>
                    <pre className="mono small" style={{ overflow: "auto" }}>
                      {JSON.stringify(answer.citations, null, 2)}
                    </pre>
                  </details>
                )}
              </>
            ) : (
              <div className="alert error small">{answer.error}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
