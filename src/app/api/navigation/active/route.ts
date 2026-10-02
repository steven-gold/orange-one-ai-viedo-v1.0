import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import {
  NavigationResolutionError,
  resolveAdminActiveUid,
  resolveFrontActiveUid,
  resolveVisibleNavigation,
} from "@/server/domain/navigation";
import type { NavigationArea } from "@/server/domain/types";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const params = new URL(request.url).searchParams;
    const area: NavigationArea = params.get("area") === "ADMIN" ? "ADMIN" : "FRONT";
    const resolution = await resolveVisibleNavigation(principal.accountUid);
    const pageUid = params.get("pageUid");
    const ancestry = params.get("ancestry");
    const activeNavigationUid =
      area === "ADMIN"
        ? resolveAdminActiveUid(resolution.items, pageUid)
        : resolveFrontActiveUid(resolution.items, ancestry ? ancestry.split(",") : []);
    return NextResponse.json({ area, activeNavigationUid });
  } catch (error) {
    if (error instanceof NavigationResolutionError) {
      const status = error.code === "NAVIGATION_AUTHORITY_UNAVAILABLE" ? 403 : 404;
      return jsonError(error.code, error.message, status);
    }
    return jsonError("INTERNAL_ERROR", "Unexpected navigation runtime error", 500);
  }
}
