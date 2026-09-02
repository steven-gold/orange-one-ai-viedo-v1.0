export type ObservabilityLevel = "info" | "warn" | "error";
export type ObservabilityOutcome = "ACCEPTED" | "RATE_LIMITED" | "ERROR";

export type ObservabilityEvent = {
  event: string;
  correlation_id?: string;
  method?: string;
  path?: string;
  status?: number;
  duration_ms?: number;
  reason_code?: string;
  operation_id?: string;
  outcome?: ObservabilityOutcome;
};

export type ObservabilityEntry = Readonly<ObservabilityEvent & {
  timestamp: string;
  level: ObservabilityLevel;
}>;

export type ObservabilitySink = (entry: ObservabilityEntry) => void | Promise<void>;

let configuredSink: ObservabilitySink | null = null;

export function configureObservabilitySink(next: ObservabilitySink | null) {
  configuredSink = next;
}

function fallbackWrite(entry: ObservabilityEntry) {
  const line = JSON.stringify(entry);
  if (entry.level === "error") console.error(line);
  else console.warn(line);
}

export async function emitObservability(level: ObservabilityLevel, event: ObservabilityEvent) {
  const entry: ObservabilityEntry = Object.freeze({
    timestamp: new Date().toISOString(),
    level,
    ...event,
  });

  try {
    if (configuredSink) {
      await configuredSink(entry);
      return;
    }
    fallbackWrite(entry);
  } catch {
    try {
      fallbackWrite({
        timestamp: new Date().toISOString(),
        level: "error",
        event: "OBSERVABILITY_SINK_FAILURE",
        correlation_id: event.correlation_id,
        outcome: "ERROR",
        reason_code: "OBSERVABILITY_SINK_FAILURE",
      });
    } catch {
      // Observability must never alter application control flow.
    }
  }
}
