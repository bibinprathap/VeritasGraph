import { NextResponse } from "next/server";
import { EngineError, runEngine } from "@/lib/engine";

export const runtime = "nodejs";
export const maxDuration = 60;

type ExportBody = {
  format?: "csv" | "xlsx";
  target?: string;
  filename?: string;
  result?: unknown;
  takeoff?: unknown;
};

function safeFilename(name: string, extension: string): string {
  const base = (name || "floorplan-takeoff")
    .replace(/\.[a-z0-9]+$/i, "")
    .replace(/[^a-zA-Z0-9._-]/g, "_")
    .slice(0, 80) || "floorplan-takeoff";
  return `${base}.${extension}`;
}

export async function POST(req: Request) {
  let body: ExportBody;
  try {
    body = (await req.json()) as ExportBody;
  } catch {
    return NextResponse.json({ error: "Expected a JSON body." }, { status: 400 });
  }

  const format = body.format === "csv" ? "csv" : "xlsx";
  const target = typeof body.target === "string" ? body.target : "takeoff";

  if (!body.result || typeof body.result !== "object") {
    return NextResponse.json({ error: "Nothing to export — run an extraction first." }, { status: 400 });
  }

  const args = ["--format", format];
  if (format === "csv") args.push("--csv-target", target);

  try {
    const data = await runEngine(args, {
      module: "engine.export_cli",
      stdin: JSON.stringify({ result: body.result, takeoff: body.takeoff }),
      timeoutMs: 60_000,
    });

    const extension = format === "csv" ? "csv" : "xlsx";
    const filename = safeFilename(body.filename ?? "floorplan-takeoff", extension);
    const contentType =
      format === "csv"
        ? "text/csv; charset=utf-8"
        : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

    return new NextResponse(new Uint8Array(data), {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${filename}"`,
        "Content-Length": String(data.length),
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message = error instanceof EngineError ? error.message : String(error);
    return NextResponse.json({ error: `Export failed: ${message}` }, { status: 500 });
  }
}
