-- ACPOS migration 0019: canonical async queue delivery runtime.
-- Change ref: CR-QUEUE-0019
-- Reuses public.queues/public.workers/public.outbox_events/public.inbox_events/public.dead_letters.
-- No second queue table is created.

ALTER TABLE public.outbox_events
  ADD COLUMN IF NOT EXISTS queue_id uuid NULL REFERENCES public.queues(queue_id),
  ADD COLUMN IF NOT EXISTS idempotency_key char(64) NULL,
  ADD COLUMN IF NOT EXISTS available_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS claimed_by_worker_id uuid NULL REFERENCES public.workers(worker_id),
  ADD COLUMN IF NOT EXISTS lease_until timestamptz NULL,
  ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 3,
  ADD COLUMN IF NOT EXISTS last_error_code text NULL,
  ADD COLUMN IF NOT EXISTS dead_lettered_at timestamptz NULL;

ALTER TABLE public.outbox_events
  DROP CONSTRAINT IF EXISTS outbox_events_attempt_count_nonnegative,
  ADD CONSTRAINT outbox_events_attempt_count_nonnegative CHECK (attempt_count >= 0),
  DROP CONSTRAINT IF EXISTS outbox_events_max_attempts_positive,
  ADD CONSTRAINT outbox_events_max_attempts_positive CHECK (max_attempts > 0),
  DROP CONSTRAINT IF EXISTS outbox_events_claim_pair,
  ADD CONSTRAINT outbox_events_claim_pair CHECK (
    (claimed_by_worker_id IS NULL AND lease_until IS NULL)
    OR
    (claimed_by_worker_id IS NOT NULL AND lease_until IS NOT NULL)
  ),
  DROP CONSTRAINT IF EXISTS outbox_events_terminal_exclusive,
  ADD CONSTRAINT outbox_events_terminal_exclusive CHECK (
    NOT (published_at IS NOT NULL AND dead_lettered_at IS NOT NULL)
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_outbox_queue_idempotency
  ON public.outbox_events(queue_id, idempotency_key)
  WHERE queue_id IS NOT NULL AND idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_outbox_queue_claimable
  ON public.outbox_events(queue_id, available_at, occurred_at)
  WHERE published_at IS NULL AND dead_lettered_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_outbox_queue_lease
  ON public.outbox_events(queue_id, lease_until)
  WHERE claimed_by_worker_id IS NOT NULL AND published_at IS NULL AND dead_lettered_at IS NULL;

WITH q AS (
  INSERT INTO public.queues(queue_key, purpose, capacity, status, policy)
  VALUES(
    'acpos.provider.execution.v1',
    'Execute governed ProviderGateway requests after provider route preflight.',
    100,
    'READY',
    '{"max_attempts":3,"lease_seconds":120,"backoff_seconds":[30,120,300],"ordering":"FIFO_AVAILABLE_AT","claim":"FOR_UPDATE_SKIP_LOCKED","restart_recovery":"LEASE_EXPIRY_RECLAIM","idempotency_scope":"QUEUE_ID_PLUS_IDEMPOTENCY_KEY"}'::jsonb
  )
  ON CONFLICT(queue_key) DO UPDATE
  SET purpose=EXCLUDED.purpose,
      capacity=EXCLUDED.capacity,
      status=EXCLUDED.status,
      policy=EXCLUDED.policy
  RETURNING queue_id
)
INSERT INTO public.workers(worker_key, queue_id, capability, health, status)
SELECT
  'acpos.provider.execution.worker.v1',
  queue_id,
  '{"handler":"PROVIDER_EXECUTION","supported_event_types":["ACPOS_PROVIDER_EXECUTION_REQUESTED","ACPOS_QUEUE_RUNTIME_PROBE"],"execution_model":"VERCEL_CRON_ONE_SHOT_DRAIN","max_batch":10}'::jsonb,
  '{"status":"NOT_STARTED","last_probe":null}'::jsonb,
  'READY'
FROM q
ON CONFLICT(worker_key) DO UPDATE
SET queue_id=EXCLUDED.queue_id,
    capability=EXCLUDED.capability,
    status=EXCLUDED.status;

DO $$
DECLARE
  q_count bigint;
  w_count bigint;
BEGIN
  SELECT count(*) INTO q_count
  FROM public.queues
  WHERE queue_key='acpos.provider.execution.v1'
    AND status='READY';

  SELECT count(*) INTO w_count
  FROM public.workers w
  JOIN public.queues q ON q.queue_id=w.queue_id
  WHERE w.worker_key='acpos.provider.execution.worker.v1'
    AND q.queue_key='acpos.provider.execution.v1'
    AND w.status='READY';

  IF q_count <> 1 THEN
    RAISE EXCEPTION 'ACPOS_QUEUE_REGISTRY_MISMATCH:%', q_count;
  END IF;
  IF w_count <> 1 THEN
    RAISE EXCEPTION 'ACPOS_WORKER_REGISTRY_MISMATCH:%', w_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0019_async_queue_delivery_runtime',
  'aea7ea811c826b255d3478e12e9715cb042444c5d2c6f8431f02b0189c0818cc',
  'migration-runner',
  'CR-QUEUE-0019'
)
ON CONFLICT (migration_id) DO NOTHING;
