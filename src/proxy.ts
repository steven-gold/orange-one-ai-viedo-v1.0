import { NextRequest, NextResponse } from "next/server";
import { emitObservability } from "@/server/shared/observability";
import { checkMutationRateLimit, clientIdentity } from "@/server/shared/requestGuard";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function correlationId(request: NextRequest) {
  const supplied = request.headers.get("x-correlation-id")?.trim();
  return supplied || crypto.randomUUID();
}

export async function proxy(request: NextRequest) {
  if (!MUTATING_METHODS.has(request.method)) return NextResponse.next();

  const correlation_id = correlationId(request);
  const path = request.nextUrl.pathname;
  const identity = clientIdentity(request.headers);
  const decision = checkMutationRateLimit(identity);

  if (!decision.allowed) {
    await emitObservability("warn", {
      event: "HTTP_MUTATION_RATE_LIMITED",
      correlation_id,
      method: request.method,
      path,
      status: 429,
      outcome: "RATE_LIMITED",
      reason_code: "RATE_LIMITED",
    });

    return NextResponse.json(
      { reason_code: "RATE_LIMITED", correlation_id },
      {
        status: 429,
        headers: {
          "cache-control": "no-store",
          "retry-after": String(decision.retry_after_seconds),
          "x-correlation-id": correlation_id,
          "x-ratelimit-limit": String(decision.limit),
          "x-ratelimit-remaining": String(decision.remaining),
        },
      },
    );
  }

  const forwardedHeaders = new Headers(request.headers);
  forwardedHeaders.set("x-correlation-id", correlation_id);
  const response = NextResponse.next({ request: { headers: forwardedHeaders } });
  response.headers.set("x-correlation-id", correlation_id);
  response.headers.set("x-ratelimit-limit", String(decision.limit));
  response.headers.set("x-ratelimit-remaining", String(decision.remaining));

  await emitObservability("info", {
    event: "HTTP_MUTATION_ACCEPTED",
    correlation_id,
    method: request.method,
    path,
    outcome: "ACCEPTED",
  });

  return response;
}

export const config = {
  matcher: ["/v1/:path*"],
};
