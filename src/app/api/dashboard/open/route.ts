import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { persistHasDashboardPermission, persistRecordSectionOpen } from "@/server/db/persist";
import { DASHBOARD_SECTION_SEEDS } from "@/server/domain/dashboard";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { sectionUid?: string; controlUid?: string };
    const sectionUid = String(body.sectionUid ?? "");
    const controlUid = String(body.controlUid ?? "");
    const known = DASHBOARD_SECTION_SEEDS.find((row) => row.sectionUid === sectionUid && row.controlUid === controlUid);
    if (!known) {
      return jsonError("DASHBOARD_READ_UNAVAILABLE", `Unknown section ${sectionUid}`, 404);
    }
    const allowed = await persistHasDashboardPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", "workspace.dashboard.view required", 403);
    }
    const eventUid = await persistRecordSectionOpen(principal.accountUid, sectionUid, controlUid);
    return NextResponse.json({ eventUid, sectionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected dashboard runtime error", 500);
  }
}
