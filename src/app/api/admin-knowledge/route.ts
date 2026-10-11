import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { persistGetKbReadModel } from "@/server/db/persist";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const model = await persistGetKbReadModel(principal.accountUid);
    return NextResponse.json(model);
  } catch {
    return jsonError("KB_READ_UNAVAILABLE", "Unexpected admin:KB-01 runtime error", 500);
  }
}
