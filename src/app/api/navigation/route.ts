import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { NavigationResolutionError, resolveVisibleNavigation } from "@/server/domain/navigation";
import type { NavigationArea } from "@/server/domain/types";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const area: NavigationArea = new URL(request.url).searchParams.get("area") === "ADMIN" ? "ADMIN" : "FRONT";
    const resolution = await resolveVisibleNavigation(principal.accountUid);
    return NextResponse.json({
      area,
      authorityUid: resolution.authorityUid,
      items: resolution.items.filter((item) => item.area === area),
      resolved: true,
      error: null,
    });
  } catch (error) {
    if (error instanceof NavigationResolutionError) {
      const status = error.code === "NAVIGATION_AUTHORITY_UNAVAILABLE" ? 403 : 404;
      return jsonError(error.code, error.message, status);
    }
    return jsonError("INTERNAL_ERROR", "Unexpected navigation runtime error", 500);
  }
}
