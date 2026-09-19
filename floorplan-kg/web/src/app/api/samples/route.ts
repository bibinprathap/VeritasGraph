import { NextResponse } from "next/server";
import { listSamples } from "@/lib/engine";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({ items: await listSamples() });
}
