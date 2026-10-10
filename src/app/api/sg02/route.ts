import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { persistGetSg02ReadModel } from "@/server/db/persist";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const model = await persistGetSg02ReadModel(principal.accountUid);
    return NextResponse.json(model);
  } catch {
    return jsonError("SG02_READ_UNAVAILABLE", "Unexpected SG02 runtime error", 500);
  }
}
