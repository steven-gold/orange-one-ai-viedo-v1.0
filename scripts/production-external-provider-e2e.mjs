const base = (process.env.ACPOS_DEPLOYMENT_URL ?? "https://orange-one-acpos-test.vercel.app").replace(/\/$/, "");
const email = (process.env.ACPOS_PRODUCTION_E2E_EMAIL ?? "").trim();
const password = process.env.ACPOS_PRODUCTION_E2E_PASSWORD ?? "";
const singleProfileId = (process.env.ACPOS_EXTERNAL_E2E_PROFILE_ID ?? "").trim();
const profileIds = (process.env.ACPOS_EXTERNAL_E2E_PROFILE_IDS ?? singleProfileId)
  .split(",").map((value) => value.trim()).filter(Boolean);
const groupId = (process.env.ACPOS_EXTERNAL_E2E_GROUP_ID ?? "").trim();
const capability = (process.env.ACPOS_EXTERNAL_E2E_CAPABILITY ?? "").trim().toUpperCase();
const classification = (process.env.ACPOS_EXTERNAL_E2E_CLASSIFICATION ?? "INTERNAL").trim().toUpperCase();
const expectedReleaseSha = (process.env.ACPOS_EXPECT_RELEASE_SHA ?? "").trim();

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function protectionHeaders() {
  const secret = process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
  return secret ? { "x-vercel-protection-bypass": secret } : {};
}
function cookieHeaders(cookie) {
  return { ...protectionHeaders(), cookie };
}
function blocked(reason) {
  process.stdout.write(`PRODUCTION_EXTERNAL_PROVIDER_E2E_BLOCKED reason=${reason} external_request_sent=false\n`);
  process.exit(78);
}
async function json(response, stage) {
  const text = await response.text();
  try { return JSON.parse(text); } catch { throw new Error(`${stage}_RESPONSE_NOT_JSON`); }
}
async function logout(cookie) {
  if (!cookie) return;
  await fetch(`${base}/v1/identity/session`, {
    method: "DELETE",
    cache: "no-store",
    headers: cookieHeaders(cookie),
  }).catch(() => undefined);
}

if (!email || !password) blocked("PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED");
if (!profileIds.length) blocked("REAL_PROVIDER_PROFILE_ID_NOT_CONFIGURED");
if (!groupId) blocked("REAL_PROVIDER_GROUP_ID_NOT_CONFIGURED");
if (!capability) blocked("REAL_PROVIDER_CAPABILITY_NOT_CONFIGURED");

let cookie = "";
try {
  const health = await fetch(`${base}/health`, { cache: "no-store", headers: protectionHeaders() });
  const healthBody = await json(health, "HEALTH");
  assert(health.status === 200, `HEALTH_HTTP_${health.status}`);
  assert(healthBody?.environment === "production", "HEALTH_ENVIRONMENT_NOT_PRODUCTION");
  if (expectedReleaseSha) {
    assert(
      healthBody?.release_sha === expectedReleaseSha,
      `HEALTH_RELEASE_SHA_MISMATCH_${healthBody?.release_sha ?? "UNRESOLVED"}`,
    );
  }

  const login = await fetch(`${base}/v1/identity/session`, {
    method: "POST",
    cache: "no-store",
    redirect: "manual",
    headers: {
      ...protectionHeaders(),
      "content-type": "application/json",
      "x-correlation-id": crypto.randomUUID(),
    },
    body: JSON.stringify({ email, password }),
  });
  const loginBody = await json(login, "LOGIN");
  assert(login.status === 200, `LOGIN_HTTP_${login.status}`);
  assert(loginBody?.ok === true && loginBody?.logged_in === true, "LOGIN_BODY_INVALID");
  const setCookie = login.headers.get("set-cookie") ?? "";
  cookie = setCookie.split(";")[0].trim();
  assert(cookie.startsWith("acpos_session="), "LOGIN_SESSION_COOKIE_MISSING");

  const list = await fetch(`${base}/v1/aiapi/provider-profiles`, {
    method: "GET",
    cache: "no-store",
    headers: cookieHeaders(cookie),
  });
  const listBody = await json(list, "PROFILE_LIST");
  assert(list.status === 200 && listBody?.ok === true, `PROFILE_LIST_HTTP_${list.status}`);
  const profiles = Array.isArray(listBody?.value?.profiles) ? listBody.value.profiles : [];

  const tested = [];
  const profileFailures = [];
  for (const profileId of profileIds) {
    const profile = profiles.find((row) => row?.profile_id === profileId);
    try {
      assert(profile, `REAL_PROVIDER_PROFILE_NOT_FOUND_${profileId}`);
      assert(profile.enabled === true, `REAL_PROVIDER_PROFILE_DISABLED_${profileId}`);
      assert(profile.credential_status === "SET", `REAL_PROVIDER_CREDENTIAL_NOT_SET_${profileId}`);
      assert(
        String(profile.capability_type ?? "").toUpperCase() === capability,
        `REAL_PROVIDER_CAPABILITY_PROFILE_MISMATCH_${profileId}`,
      );

      const connectionTest = await fetch(
        `${base}/v1/aiapi/provider-profiles/${encodeURIComponent(profileId)}/test`,
        {
          method: "POST",
          cache: "no-store",
          headers: {
            ...cookieHeaders(cookie),
            "content-type": "application/json",
            "x-correlation-id": crypto.randomUUID(),
          },
          body: JSON.stringify({}),
        },
      );
      const connectionBody = await json(connectionTest, `PROFILE_CONNECTION_TEST_${profileId}`);
      assert(
        connectionTest.status === 200 && connectionBody?.ok === true,
        `PROFILE_CONNECTION_TEST_HTTP_${profileId}_${connectionTest.status}_${connectionBody?.reason_code ?? "UNKNOWN"}`,
      );
      assert(connectionBody?.value?.status === "PASS", `PROFILE_CONNECTION_TEST_STATUS_NOT_PASS_${profileId}`);
      assert(connectionBody?.value?.dry_run === false, `PROFILE_CONNECTION_TEST_MUST_BE_REAL_${profileId}`);
      assert(
        connectionBody?.value?.external_request_sent === true,
        `PROFILE_CONNECTION_TEST_EXTERNAL_REQUEST_NOT_ATTESTED_${profileId}`,
      );
      assert(
        typeof connectionBody?.value?.result_hash === "string" && connectionBody.value.result_hash.length > 0,
        `PROFILE_CONNECTION_TEST_RESULT_HASH_MISSING_${profileId}`,
      );
      tested.push({
        profile_id: profileId,
        provider_id: profile.provider_id,
        model_id: profile.model_id,
        test_id: connectionBody.value.test_id,
        result_hash: connectionBody.value.result_hash,
      });
    } catch (error) {
      const reason = error instanceof Error ? error.message : "UNKNOWN_PROFILE_CONNECTION_FAILURE";
      profileFailures.push({ profile_id: profileId, reason });
      process.stdout.write(
        `PRODUCTION_EXTERNAL_PROVIDER_PROFILE_FAIL profile_id=${profileId} reason=${reason} external_request_attempted=true result_accepted=false\n`,
      );
    }
  }

  const route = await fetch(`${base}/v1/aiapi/routes`, {
    method: "POST",
    cache: "no-store",
    headers: {
      ...cookieHeaders(cookie),
      "content-type": "application/json",
      "x-correlation-id": crypto.randomUUID(),
    },
    body: JSON.stringify({
      candidate_group_id: groupId,
      required_capability: capability,
      use_case: "PRODUCTION_EXTERNAL_PROVIDER_ACCEPTANCE",
      data_classification: classification,
      canonical_instruction: "ACPOS Production External Provider acceptance check. Return a short acknowledgement.",
      scoped_context: { acceptance_scope: "GATE_22_EXTERNAL_PROVIDER_E2E" },
    }),
  });
  const routeBody = await json(route, "PROVIDER_ROUTE");
  assert(
    route.status === 200 && routeBody?.ok === true,
    `PROVIDER_ROUTE_HTTP_${route.status}_${routeBody?.reason_code ?? "UNKNOWN"}`,
  );
  const value = routeBody?.value ?? {};
  assert(
    value.external_request_sent === true,
    `PROVIDER_ROUTE_EXTERNAL_REQUEST_NOT_SENT_${value.status ?? "UNKNOWN"}_${value.reason ?? "UNKNOWN"}`,
  );
  assert(value.status === "SUCCESS", `PROVIDER_ROUTE_STATUS_${value.status ?? "UNRESOLVED"}`);
  assert(typeof value.result_hash === "string" && value.result_hash.length > 0, "PROVIDER_ROUTE_RESULT_HASH_MISSING");
  assert(value.worker?.succeeded === 1, "PROVIDER_ROUTE_WORKER_NOT_SUCCESSFUL");
  const decisionId = value.route_decision_id;
  assert(typeof decisionId === "string" && decisionId.length > 0, "PROVIDER_ROUTE_DECISION_ID_MISSING");

  const decision = await fetch(`${base}/v1/aiapi/routes/${encodeURIComponent(decisionId)}`, {
    method: "GET",
    cache: "no-store",
    headers: cookieHeaders(cookie),
  });
  const decisionBody = await json(decision, "ROUTE_DECISION");
  assert(decision.status === 200 && decisionBody?.ok === true, `ROUTE_DECISION_HTTP_${decision.status}`);
  const resolved = decisionBody?.value ?? {};
  assert(resolved.status === "SUCCESS", `ROUTE_DECISION_STATUS_${resolved.status ?? "UNRESOLVED"}`);
  assert(resolved.payload?.external_request_sent === true, "ROUTE_DECISION_EXTERNAL_REQUEST_NOT_ATTESTED");
  assert(resolved.payload?.result_hash === value.result_hash, "ROUTE_DECISION_RESULT_HASH_MISMATCH");
  assert(
    typeof resolved.provider_id === "string" && resolved.provider_id.length > 0,
    "ROUTE_DECISION_PROVIDER_MISSING",
  );
  assert(
    typeof resolved.model_id === "string" && resolved.model_id.length > 0,
    "ROUTE_DECISION_MODEL_MISSING",
  );

  if (profileFailures.length) {
    process.stdout.write(
      `PRODUCTION_EXTERNAL_PROVIDER_E2E_PARTIAL release_sha=${healthBody.release_sha} profile_tests_passed=${tested.length} profile_tests_failed=${profileFailures.length} failed_profiles=${profileFailures.map((row) => row.profile_id).join(",")} route_provider=${resolved.provider_id} route_model=${resolved.model_id} worker_succeeded=1 external_request_sent=true provider_matrix_complete=false plaintext_persisted=false\n`,
    );
  }

  process.stdout.write(
    `PRODUCTION_EXTERNAL_PROVIDER_E2E_PASS release_sha=${healthBody.release_sha} profile_tests=${tested.length} providers=${tested.map((row) => row.provider_id).join(",")} capability=${capability} route_provider=${resolved.provider_id} route_model=${resolved.model_id} route_decision_id=${decisionId} worker_succeeded=1 external_request_sent=true provider_matrix_complete=${profileFailures.length === 0} plaintext_persisted=false\n`,
  );
} finally {
  await logout(cookie);
}
