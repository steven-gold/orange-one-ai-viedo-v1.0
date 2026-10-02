import { NextResponse } from "next/server";
import { readyCheck } from "@/server/db/migrate";

export const dynamic = "force-dynamic";

export async function GET() {
  const ready = await readyCheck();
  return NextResponse.json(ready, { status: ready.ready ? 200 : 503 });
}
