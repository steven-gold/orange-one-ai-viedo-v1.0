import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createCorePostRoute } from "@/server/core/coreRouteFactory";
import { decideCandidate } from "@/server/shared/candidateDecisionRuntime";

const corePost = createCorePostRoute("CORE-01-PORT-CANDIDATE-DECIDE");
const CORE_DECISION_ACTIONS = new Set(["CORE-01-ACT-CANDIDATE-ACCEPT", "CORE-01-ACT-CANDIDATE-RETURN"]);

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(request: NextRequest, context: RouteContext) {
  const actionUid = request.headers.get("x-core-action-uid");
  if (actionUid && CORE_DECISION_ACTIONS.has(actionUid)) {
    return corePost(request, context);
  }

  const current = request.headers.get("x-correlation-id");
  const correlation_id = current && current.trim() ? current : crypto.randomUUID();
  const { id } = await context.params;
  const payload = await request.json().catch(() => null);
  const result = await decideCandidate({ correlation_id, candidate_id: id, payload });
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
