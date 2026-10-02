import { NextResponse } from "next/server";
import { recordNavigationEvent } from "@/server/audit/auditLogger";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { persistGetItem } from "@/server/db/persist";
import { NavigationResolutionError, resolveVisibleNavigation } from "@/server/domain/navigation";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { itemUid?: string };
    const itemUid = String(body.itemUid ?? "");
    const item = await persistGetItem(itemUid);
    if (!item) {
      return jsonError("NAVIGATION_TARGET_UNRESOLVABLE", `Unknown item ${itemUid}`, 404);
    }
    const resolution = await resolveVisibleNavigation(principal.accountUid);
    if (!resolution.items.some((entry) => entry.uid === itemUid)) {
      throw new NavigationResolutionError(
        "NAVIGATION_TARGET_UNRESOLVABLE",
        `Item ${itemUid} is not visible to ${principal.accountUid}`,
      );
    }
    const event = await recordNavigationEvent({
      accountUid: principal.accountUid,
      area: item.area,
      itemUid: item.uid,
      route: item.route,
    });
    return NextResponse.json({ eventUid: event.eventUid, route: item.route }, { status: 202 });
  } catch (error) {
    if (error instanceof NavigationResolutionError) {
      const status = error.code === "NAVIGATION_AUTHORITY_UNAVAILABLE" ? 403 : 404;
      return jsonError(error.code, error.message, status);
    }
    return jsonError("INTERNAL_ERROR", "Unexpected navigation runtime error", 500);
  }
}
