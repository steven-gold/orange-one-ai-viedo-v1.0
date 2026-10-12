import { NextResponse } from "next/server";
import { jsonError } from "@/server/auth/requireAuth";
import { endIdentitySession, establishIdentity, readIdentitySession } from "@/server/identity/login";
import { clearSessionCookie, cookieSecure, parseSessionCookie, serializeSessionCookie } from "@/server/identity/sessionCookie";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const token = parseSessionCookie(request.headers.get("cookie"));
  const session = await readIdentitySession(token);
  if (!session) {
    return jsonError("UNAUTHENTICATED", "Valid session is required", 401);
  }
  return NextResponse.json({
    sessionUid: session.session_uid,
    accountUid: session.account_uid,
    expiresAt: session.expires_at,
  });
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { email?: string; password?: string };
    const result = await establishIdentity(String(body.email ?? ""), String(body.password ?? ""));
    if (!result.ok) {
      return jsonError(result.reason, result.reason, result.reason === "DATABASE_RUNTIME_NOT_BOUND" ? 503 : 401);
    }
    const response = NextResponse.json(
      { sessionUid: result.sessionUid, accountUid: result.accountUid },
      { status: 201 },
    );
    response.headers.set("Set-Cookie", serializeSessionCookie(result.token, cookieSecure()));
    return response;
  } catch {
    return jsonError("IDENTITY_SESSION_CREATE_FAILED", "Session create failed", 500);
  }
}

export async function DELETE(request: Request) {
  const token = parseSessionCookie(request.headers.get("cookie"));
  await endIdentitySession(token);
  const response = NextResponse.json({ ended: true });
  response.headers.set("Set-Cookie", clearSessionCookie(cookieSecure()));
  return response;
}
