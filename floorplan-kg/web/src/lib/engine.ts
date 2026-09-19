import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";

/**
 * Thin wrapper around `python -m engine.cli`.
 *
 * The extraction engine stays a separate process on purpose: PyMuPDF and
 * pdfplumber have no JS equivalent worth trusting for dimension geometry, and
 * keeping the boundary at a CLI means the engine is testable and runnable with
 * no web server at all.
 */

export const projectRoot = path.resolve(process.cwd(), "..");

export const pythonExecutable =
  process.env.FLOORPLAN_PYTHON ?? path.resolve(projectRoot, "..", ".venv", "bin", "python");

export const sampleDir =
  process.env.FLOORPLAN_SAMPLES ??
  path.resolve(projectRoot, "..", "Floorplan-Dimractor", "data", "input");

const MAX_BUFFER = 256 * 1024 * 1024;

export class EngineError extends Error {
  constructor(message: string, readonly stderr = "", readonly code: number | null = null) {
    super(message);
    this.name = "EngineError";
  }
}

export type RunOptions = {
  /** Python module to invoke with `-m`. Defaults to the extraction CLI. */
  module?: string;
  /** Written to the child's stdin and closed. */
  stdin?: string | Buffer;
  timeoutMs?: number;
};

export function runEngine(args: string[], options: RunOptions = {}): Promise<Buffer> {
  const { module = "engine.cli", stdin, timeoutMs = 120_000 } = options;
  return new Promise((resolve, reject) => {
    const child = spawn(pythonExecutable, ["-m", module, ...args], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONWARNINGS: "ignore" },
    });

    if (stdin !== undefined) {
      child.stdin.on("error", () => {
        /* the child may exit before reading; the close handler reports it */
      });
      child.stdin.end(stdin);
    } else {
      child.stdin.end();
    }

    const stdout: Buffer[] = [];
    let stderr = "";
    let size = 0;
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill("SIGKILL");
      reject(new EngineError(`Engine timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    child.stdout.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > MAX_BUFFER) {
        child.kill("SIGKILL");
        return;
      }
      stdout.push(chunk);
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    child.on("error", (err) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(new EngineError(`Could not start the engine (${pythonExecutable}): ${err.message}`));
    });

    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (code !== 0) {
        reject(new EngineError(firstMeaningfulLine(stderr) || `Engine exited with code ${code}`, stderr, code));
        return;
      }
      resolve(Buffer.concat(stdout));
    });
  });
}

/** Python tracebacks are bottom-line-significant; surface that, not the header. */
function firstMeaningfulLine(stderr: string): string {
  const lines = stderr.trim().split("\n").filter((l) => l.trim());
  if (!lines.length) return "";
  const last = lines[lines.length - 1].trim();
  return last.length > 400 ? `${last.slice(0, 400)}…` : last;
}

export async function withTempPdf<T>(
  bytes: Uint8Array,
  filename: string,
  fn: (filePath: string) => Promise<T>,
): Promise<T> {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "floorplan-kg-"));
  const safe = filename.replace(/[^a-zA-Z0-9._-]/g, "_") || "upload.pdf";
  const filePath = path.join(dir, safe.endsWith(".pdf") ? safe : `${safe}.pdf`);
  try {
    await fs.writeFile(filePath, bytes);
    return await fn(filePath);
  } finally {
    await fs.rm(dir, { recursive: true, force: true });
  }
}

/** Resolve a sample name to a path inside the sample directory, or null. */
export async function resolveSample(name: string): Promise<string | null> {
  const base = path.basename(name);
  if (base !== name || !base.toLowerCase().endsWith(".pdf")) return null;
  const full = path.join(sampleDir, base);
  try {
    const stat = await fs.stat(full);
    return stat.isFile() ? full : null;
  } catch {
    return null;
  }
}

export async function listSamples(): Promise<Array<{ name: string; sizeBytes: number }>> {
  try {
    const entries = await fs.readdir(sampleDir);
    const pdfs = entries.filter((e) => e.toLowerCase().endsWith(".pdf")).sort();
    return await Promise.all(
      pdfs.map(async (name) => ({
        name,
        sizeBytes: (await fs.stat(path.join(sampleDir, name))).size,
      })),
    );
  } catch {
    return [];
  }
}
