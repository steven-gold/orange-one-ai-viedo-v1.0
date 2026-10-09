import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { persistGetSocReadModel } from "@/server/db/persist";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const model = await persistGetSocReadModel(principal.accountUid);
    return NextResponse.json(model);
  } catch {
    return jsonError("SOC_READ_UNAVAILABLE", "Unexpected social publishing runtime error", 500);
  }
}
