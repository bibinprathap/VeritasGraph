import fs from "node:fs";

export default async function globalTeardown() {
  const dir = process.env.VG_DATA_DIR;
  if (process.env.VG_DATA_DIR_AUTO === "1" && dir) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}