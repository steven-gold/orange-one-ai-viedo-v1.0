import { NextRequest, NextResponse } from "next/server";
import { getDashboardReadModel } from "@/server/dashboard/readModelRuntime";

function correlationId(request: NextRequest): string {
  const existing = request.headers.get("x-correlation-id");
  return existing && existing.trim().length > 0 ? existing : crypto.randomUUID();
}

export async function GET(request: NextRequest) {
  const correlation_id = correlationId(request);
  const result = await getDashboardReadModel({ correlation_id });

  if (!result.ok) {
    const status = result.error.error_uid === "WB-01-ERR-POLICY-001" ? 403 : result.error.error_uid === "WB-01-ERR-SCHEMA-001" ? 502 : 503;
    return NextResponse.json(result.error, {
      status,
      headers: {
        "cache-control": "no-store",
        "x-correlation-id": correlation_id,
      },
    });
  }

  return NextResponse.json(result.value, {
    status: 200,
    headers: {
      "cache-control": "no-store",
      "x-correlation-id": correlation_id,
    },
  });
}
