import { NextResponse } from "next/server";
import { bootstrapDatabase } from "../db/migrate";
import { authenticate, type AuthenticatedPrincipal } from "./authenticate";

export async function requireAuth(request: Request): Promise<AuthenticatedPrincipal | NextResponse> {
  try {
    await bootstrapDatabase();
  } catch (error) {
    const message = error instanceof Error ? error.message : "DATABASE_RUNTIME_NOT_BOUND";
    return jsonError("DATABASE_RUNTIME_NOT_BOUND", message, 503);
  }
  const principal = await authenticate(request.headers);
  if (!principal.authenticated) {
    return NextResponse.json(
      { error: { code: "UNAUTHENTICATED", message: "Valid session and account identity are required" } },
      { status: 401 },
    );
  }
  return principal;
}

export function jsonError(code: string, message: string, status: number): NextResponse {
  return NextResponse.json({ error: { code, message } }, { status });
}
