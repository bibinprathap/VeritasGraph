import { NextResponse } from "next/server";
import { EngineError, resolveSample, runEngine, withTempPdf } from "@/lib/engine";
import type { ExtractionResult } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 120;

const MAX_UPLOAD_BYTES = 80 * 1024 * 1024;

function engineArgs(pdfPath: string, method: string, ceiling: number | null): string[] {
  const args = [pdfPath, "--method", method, "--format", "json"];
  if (ceiling && Number.isFinite(ceiling) && ceiling > 0) {
    args.push("--ceiling-height", String(ceiling));
  }
  return args;
}

export async function POST(req: Request) {
  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return NextResponse.json({ error: "Expected a multipart form body." }, { status: 400 });
  }

  const methodInput = String(form.get("method") ?? "pymupdf");
  const method = methodInput === "pdfplumber" ? "pdfplumber" : "pymupdf";
  const ceilingRaw = form.get("ceilingHeightFeet");
  const ceiling = ceilingRaw ? Number(ceilingRaw) : null;

  const upload = form.get("file");
  const sample = form.get("sample");

  try {
    let stdout: Buffer;

    if (upload instanceof File) {
      // A zero-byte file was still *provided*; reporting it as "no file" would
      // send the user looking for the wrong problem.
      if (upload.size === 0) {
        return NextResponse.json(
          { error: "Error processing PDF: the uploaded file is empty (0 bytes)." },
          { status: 422 },
        );
      }
      if (upload.size > MAX_UPLOAD_BYTES) {
        return NextResponse.json(
          { error: `File is larger than the ${MAX_UPLOAD_BYTES / 1024 / 1024} MB limit.` },
          { status: 413 },
        );
      }
      if (!upload.name.toLowerCase().endsWith(".pdf")) {
        return NextResponse.json({ error: "Only .pdf files are accepted." }, { status: 415 });
      }
      const bytes = new Uint8Array(await upload.arrayBuffer());
      stdout = await withTempPdf(bytes, upload.name, (p) =>
        runEngine(engineArgs(p, method, ceiling)),
      );
    } else if (typeof sample === "string" && sample) {
      const path = await resolveSample(sample);
      if (!path) {
        return NextResponse.json({ error: `Unknown sample: ${sample}` }, { status: 404 });
      }
      stdout = await runEngine(engineArgs(path, method, ceiling));
    } else {
      return NextResponse.json(
        { error: "Provide a PDF in the 'file' field or a 'sample' name." },
        { status: 400 },
      );
    }

    const result = JSON.parse(stdout.toString("utf8")) as ExtractionResult;
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof EngineError) {
      return NextResponse.json({ error: `Error processing PDF: ${error.message}` }, { status: 422 });
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: `Error processing PDF: ${message}` }, { status: 500 });
  }
}
