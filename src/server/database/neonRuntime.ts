import { neon, type NeonQueryFunction } from "@neondatabase/serverless";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { emitObservability } from "@/server/shared/observability";

export const AUTHORITY_NEON_PROJECT_ID = "wild-wave-25661146";
export const REQUIRED_MIGRATION_COUNT = 15;

type NeonSql = NeonQueryFunction<false, false>;

let boundSql: NeonSql | null = null;
let bindReason: string = "DATABASE_RUNTIME_NOT_BOUND";
let bindInFlight: Promise<void> | null = null;

export function getProductionNeonSql(): NeonSql | null {
  return boundSql;
}

export function getProductionNeonBindReason(): string {
  return bindReason;
}

export async function ensureProductionNeonRuntime(): Promise<void> {
  if (boundSql) return;
  if (!bindInFlight) {
    bindInFlight = (async () => {
      try {
        await bindProductionNeonRuntime();
      } catch {
        // bindReason is already set by bindProductionNeonRuntime
      }
    })().finally(() => {
      bindInFlight = null;
    });
  }
  await bindInFlight;
}

function readEnv(name: string): string {
  const value = process.env[name];
  return typeof value === "string" ? value.trim() : "";
}

export async function bindProductionNeonRuntime(): Promise<void> {
  boundSql = null;
  bindReason = "DATABASE_RUNTIME_NOT_BOUND";

  if (isControlledTestMode()) {
    bindReason = "CONTROLLED_TEST_NOT_PRODUCTION_READY";
    await emitObservability("info", {
      event: "acpos_neon_bind_skipped",
      reason_code: bindReason,
      outcome: "ACCEPTED",
    });
    return;
  }

  const projectId = readEnv("NEON_PROJECT_ID");
  const databaseUrl = readEnv("DATABASE_URL");
  const unpooledUrl = readEnv("DATABASE_URL_UNPOOLED");
  const deploymentEnvironment = readEnv("ACPOS_DEPLOYMENT_ENV").toLowerCase();

  if (projectId && projectId !== AUTHORITY_NEON_PROJECT_ID) {
    bindReason = "NEON_PROJECT_ID_IDENTITY_MISMATCH";
    await emitObservability("error", {
      event: "acpos_neon_bind_blocked",
      reason_code: bindReason,
      outcome: "ERROR",
    });
    throw new Error(bindReason);
  }

  if (!projectId || !databaseUrl || !unpooledUrl) {
    bindReason = "DATABASE_RUNTIME_ENV_INCOMPLETE";
    await emitObservability(deploymentEnvironment === "production" ? "error" : "warn", {
      event: "acpos_neon_bind_blocked",
      reason_code: bindReason,
      outcome: "ERROR",
    });
    return;
  }

  const sql = neon(databaseUrl);

  try {
    const rows = await sql`
      SELECT count(*)::int AS n
      FROM schema_migration_history
    `;
    const n = Array.isArray(rows) && rows[0] && typeof rows[0] === "object" ? Number((rows[0] as { n?: unknown }).n) : NaN;
    if (n !== REQUIRED_MIGRATION_COUNT) {
      bindReason = "SCHEMA_MIGRATION_HISTORY_COUNT_MISMATCH";
      await emitObservability("error", {
        event: "acpos_neon_bind_blocked",
        reason_code: bindReason,
        outcome: "ERROR",
      });
      return;
    }
  } catch {
    bindReason = "SCHEMA_MIGRATION_HISTORY_UNAVAILABLE";
    await emitObservability("error", {
      event: "acpos_neon_bind_blocked",
      reason_code: bindReason,
      outcome: "ERROR",
    });
    return;
  }

  boundSql = sql;
  bindReason = "BOUND";
  await emitObservability("info", {
    event: "acpos_neon_bind_ok",
    reason_code: "WILD_WAVE_DRIVER_BOUND",
    outcome: "ACCEPTED",
  });
}
