import { NextRequest, NextResponse } from "next/server";
import { DASHBOARD_SECTION_KEYS, type DashboardSectionKey } from "@/domain/dashboard/readModelContract";
import { getDashboardReadModel } from "@/server/dashboard/readModelRuntime";

function correlationId(request: NextRequest): string {
  const existing = request.headers.get("x-correlation-id");
  return existing && existing.trim().length > 0 ? existing : crypto.randomUUID();
}

function sectionKey(request: NextRequest): DashboardSectionKey | undefined {
  const raw = request.nextUrl.searchParams.get("section");
  if (!raw) return undefined;
  return (DASHBOARD_SECTION_KEYS as readonly string[]).includes(raw) ? (raw as DashboardSectionKey) : undefined;
}

export async function GET(request: NextRequest) {
  const correlation_id = correlationId(request);
  const requestedSection = request.nextUrl.searchParams.get("section");
  const section_key = sectionKey(request);

  if (requestedSection && !section_key) {
    return NextResponse.json(
      { error_uid: "WB-01-ERR-UNDEFINED-001", reason_code: "UNREGISTERED_SECTION_REQUEST", correlation_id },
      { status: 400, headers: { "x-correlation-id": correlation_id } },
    );
  }

  const result = await getDashboardReadModel({ correlation_id, section_key });
  if (!result.ok) {
    const status = result.error.error_uid === "WB-01-ERR-POLICY-001" ? 403 : result.error.error_uid === "WB-01-ERR-SCHEMA-001" ? 502 : 503;
    return NextResponse.json(result.error, { status, headers: { "x-correlation-id": correlation_id } });
  }

  return NextResponse.json(result.value, {
    status: 200,
    headers: {
      "cache-control": "no-store",
      "x-correlation-id": correlation_id,
    },
  });
}
