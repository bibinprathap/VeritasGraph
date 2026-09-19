import { NextResponse } from "next/server";
import { runEngine } from "@/lib/engine";

export const runtime = "nodejs";
export const maxDuration = 120;

/**
 * Optional VeritasGraph bridge: `status`, `preview`, `push`, `ask`.
 *
 * Never 500s on an absent engine — a missing Ollama runtime is an expected
 * state, not an error, and the UI renders it as "AI assist unavailable"
 * while every deterministic feature keeps working.
 */
export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    body = { action: "status" };
  }

  const action = typeof body.action === "string" ? body.action : "status";
  if (!["status", "preview", "push", "ask"].includes(action)) {
    return NextResponse.json({ ok: false, error: `Unknown action: ${action}` }, { status: 400 });
  }

  try {
    const stdout = await runEngine([], {
      module: "engine.mcp_cli",
      stdin: JSON.stringify(body),
      timeoutMs: action === "ask" ? 120_000 : 30_000,
    });
    return NextResponse.json(JSON.parse(stdout.toString("utf8")));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ ok: false, engineAvailable: false, error: message });
  }
}
