-- R9 Enterprise Development / Social Outreach closure.
CREATE TABLE IF NOT EXISTS outreach_discovery_jobs (
  discovery_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), job_name text NOT NULL, mode text NOT NULL CHECK(mode IN ('CONTINUOUS','SINGLE_RUN')), search_scope jsonb NOT NULL, allowed_sources jsonb NOT NULL, interval_seconds integer NOT NULL DEFAULT 3600 CHECK(interval_seconds >= 60), result_limit integer NULL CHECK(result_limit IS NULL OR result_limit > 0), status text NOT NULL CHECK(status IN ('DRAFT','RUNNING','PAUSED','STOPPED','COMPLETED','FAILED','WAITING_CONNECTOR')), stats jsonb NOT NULL DEFAULT '{}'::jsonb, started_at timestamptz NULL, stopped_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS company_master_entities (
  company_master_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), jurisdiction text NULL, registration_id text NULL, current_name text NOT NULL, aliases jsonb NOT NULL DEFAULT '[]'::jsonb, classification jsonb NOT NULL DEFAULT '{}'::jsonb, status text NOT NULL DEFAULT 'ACTIVE', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(jurisdiction,registration_id)
);
CREATE TABLE IF NOT EXISTS company_contact_points (
  contact_point_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_master_id uuid NOT NULL REFERENCES company_master_entities(company_master_id), contact_type text NOT NULL CHECK(contact_type IN ('PHONE','EMAIL','ADDRESS','DOMAIN','WEBSITE','SOCIAL')), value text NOT NULL, normalized_value text NOT NULL, source_evidence jsonb NOT NULL, is_primary boolean NOT NULL DEFAULT false, verification_status text NOT NULL DEFAULT 'UNVERIFIED', first_seen_at timestamptz NOT NULL DEFAULT now(), last_seen_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_master_id,contact_type,normalized_value)
);
CREATE TABLE IF NOT EXISTS outreach_campaigns (
  campaign_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), campaign_name text NOT NULL, message_version_id text NOT NULL, sender_account_id text NOT NULL, status text NOT NULL CHECK(status IN ('DRAFT','REVIEW','APPROVED','QUEUED','SENDING','COMPLETED','STOPPED','FAILED')), schedule_policy jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), approved_at timestamptz NULL
);
CREATE TABLE IF NOT EXISTS outreach_email_deliveries (
  delivery_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id uuid NOT NULL REFERENCES outreach_campaigns(campaign_id), company_master_id uuid NULL REFERENCES company_master_entities(company_master_id), recipient_contact_id uuid NULL REFERENCES company_contact_points(contact_point_id), recipient_email text NOT NULL, message_id text NOT NULL UNIQUE, to_count integer NOT NULL DEFAULT 1 CHECK(to_count=1), cc jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_array_length(cc)=0), bcc jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_array_length(bcc)=0), status text NOT NULL DEFAULT 'QUEUED', delivery_status text NULL, bounce_status text NULL, reply_status text NULL, suppression_status text NULL, created_at timestamptz NOT NULL DEFAULT now(), sent_at timestamptz NULL, UNIQUE(campaign_id,recipient_email)
);
CREATE TABLE IF NOT EXISTS social_account_bindings (
  social_account_binding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), platform_key text NOT NULL, display_name text NOT NULL, login_identifier_masked text NOT NULL, auth_mode text NOT NULL CHECK(auth_mode IN ('OFFICIAL_OAUTH_OR_TOKEN','MANUAL_BROWSER_CREDENTIAL','CUSTOM_SECRET')), secret_reference_id uuid NULL REFERENCES secret_references(secret_reference_id), external_account_ref text NULL, status text NOT NULL CHECK(status IN ('UNBOUND','CONFIGURED','BOUND_LOCKED','HEALTHY','REAUTH_REQUIRED','DISABLED','REVOKED')), locked_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS social_target_discovery_jobs (
  discovery_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), platform_key text NOT NULL, target_types jsonb NOT NULL, categories jsonb NOT NULL, keywords jsonb NOT NULL, filters jsonb NOT NULL DEFAULT '{}'::jsonb, mode text NOT NULL CHECK(mode IN ('CONTINUOUS','SINGLE_RUN')), status text NOT NULL DEFAULT 'RUNNING', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS social_market_targets (
  social_target_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), platform_key text NOT NULL, target_type text NOT NULL CHECK(target_type IN ('OWN_MANAGED_PAGE','MARKET_PAGE','MARKET_GROUP','ACCOUNT','CHANNEL','OTHER')), target_name text NOT NULL, target_url text NOT NULL, category text NULL, scale bigint NULL, capability jsonb NOT NULL DEFAULT '{}'::jsonb, join_status text NOT NULL DEFAULT 'DISCOVERED', posting_policy jsonb NOT NULL DEFAULT '{}'::jsonb, last_posted_at timestamptz NULL, next_eligible_at timestamptz NULL, status text NOT NULL DEFAULT 'ACTIVE', UNIQUE(platform_key,target_url)
);
CREATE TABLE IF NOT EXISTS social_manual_actions (
  manual_action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), social_target_id uuid NULL REFERENCES social_market_targets(social_target_id), social_account_binding_id uuid NULL REFERENCES social_account_bindings(social_account_binding_id), action_type text NOT NULL, reason text NOT NULL, target_url text NULL, status text NOT NULL CHECK(status IN ('OPEN','PENDING_ADMIN_APPROVAL','COMPLETED','FAILED')), completion_note text NULL, created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz NULL
);

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0015_enterprise_social_outreach_closure', '61ef9501826c3a9243ca7b8153061e981088d34e37c1e936009bf2e414745c3c', 'migration-runner', 'CR-R9-0015')
ON CONFLICT (migration_id) DO NOTHING;
