import type { NextRequest } from "next/server";
import { createCoreGetRoute } from "@/server/core/coreRouteFactory";
import { compareCandidates } from "@/server/shared/candidateCompareRuntime";
import { NextResponse } from "next/server";

const coreGet = createCoreGetRoute("CORE-01-PORT-CANDIDATE-COMPARE");

type RouteContext = { params: Promise<Record<string, string>> };

export async function GET(request: NextRequest, context: RouteContext) {
  if (request.headers.get("x-core-action-uid") === "CORE-01-ACT-CANDIDATE-COMPARE") {
    return coreGet(request, context);
  }

  const current = request.headers.get("x-correlation-id");
  const correlation_id = current && current.trim() ? current : crypto.randomUUID();
  const query = Object.fromEntries(request.nextUrl.searchParams.entries());
  const result = await compareCandidates({ correlation_id, query });
  if (!result.ok) {
    return NextResponse.json(
      { reason_code: result.reason_code, correlation_id },
      { status: result.status, headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" } },
    );
  }
  return NextResponse.json(result.value, {
    status: 200,
    headers: { "x-correlation-id": correlation_id, "cache-control": "no-store" },
  });
}
