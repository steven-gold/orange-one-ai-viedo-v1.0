export const AUTHORITY_NEON_PROJECT_ID = "wild-wave-25661146";

export function readEnv(name: string): string {
  const value = process.env[name];
  return typeof value === "string" ? value.trim() : "";
}

export function deploymentEnv(): string {
  return readEnv("ACPOS_DEPLOYMENT_ENV").toLowerCase() || "production";
}

export function databaseUrl(): string {
  return readEnv("DATABASE_URL");
}

export function neonProjectId(): string {
  return readEnv("NEON_PROJECT_ID");
}

export function isNeonConfigured(): boolean {
  return databaseUrl().length > 0;
}

export function assertNeonIdentity(): void {
  const projectId = neonProjectId();
  if (projectId && projectId !== AUTHORITY_NEON_PROJECT_ID) {
    throw new Error("NEON_PROJECT_ID_IDENTITY_MISMATCH");
  }
}
