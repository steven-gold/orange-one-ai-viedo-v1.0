import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { persistGetVideoReadModel } from "@/server/db/persist";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const model = await persistGetVideoReadModel(principal.accountUid);
    return NextResponse.json(model);
  } catch {
    return jsonError("VIDEO_READ_UNAVAILABLE", "Unexpected video runtime error", 500);
  }
}
