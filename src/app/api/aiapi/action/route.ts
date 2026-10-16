import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownAiapiAction, persistHasAiapiPermission, persistListAiapiFields, persistRecordAiapiAction } from "@/server/db/persist";
import { AIAPI_PERMISSION } from "@/server/domain/aiapi";
import { validateAiapiAction } from "@/lib/aiapiActionPreview";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string; value?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    if (!knownAiapiAction(controlUid, actionUid)) {
      return jsonError("AIAPI_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasAiapiPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${AIAPI_PERMISSION} required`, 403);
    }
    const value = typeof body.value === "string" ? body.value : undefined;
    const fields = await persistListAiapiFields();
    const fieldMap = new Map(fields.map((field) => [field.controlUid, field.value] as const));
    const validation = validateAiapiAction(controlUid, actionUid, (uid) => fieldMap.get(uid) ?? null, value);
    if (!validation.ok) {
      return jsonError(validation.code, `AIAPI action rejected: ${validation.code}`, 409);
    }
    const eventUid = await persistRecordAiapiAction(principal.accountUid, controlUid, actionUid, value);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected AIAPI runtime error", 500);
  }
}
