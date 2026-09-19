import { execFileSync, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { PYTHON, WEB_ROOT } from "./helpers";

/**
 * Fail fast and loudly if the Python engine the whole suite depends on is not
 * runnable — a hundred confusing UI timeouts is a worse diagnostic than one
 * clear message here.
 */
export default async function globalSetup() {
  const probe = spawnSync(PYTHON, ["-c", "import pymupdf, pdfplumber"], {
    cwd: path.resolve(WEB_ROOT, ".."),
    encoding: "utf8",
  });
  if (probe.status !== 0) {
    throw new Error(
      `The extraction engine is not runnable with ${PYTHON}.\n` +
        `Install its dependencies (pip install -r engine/requirements.txt) or set ` +
        `FLOORPLAN_PYTHON to an interpreter that has them.\n${probe.stderr ?? ""}`,
    );
  }

  const fixtures = path.join(WEB_ROOT, "tests", "e2e", "fixtures");
  const required = ["sample.txt", "corrupt.pdf", "empty.pdf", "scanned.pdf"];
  if (!required.every((f) => existsSync(path.join(fixtures, f)))) {
    execFileSync(PYTHON, [path.join(fixtures, "make-fixtures.py")], { stdio: "inherit" });
  }
}
