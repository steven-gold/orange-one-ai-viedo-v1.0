const base = (process.env.ACPOS_DEPLOYMENT_URL ?? "https://orange-one-acpos-test.vercel.app").replace(/\/$/, "");
const email = (process.env.ACPOS_PRODUCTION_E2E_EMAIL ?? "").trim();
const password = process.env.ACPOS_PRODUCTION_E2E_PASSWORD ?? "";
const singleProfileId = (process.env.ACPOS_EXTERNAL_E2E_PROFILE_ID ?? "").trim();
const profileIds = (process.env.ACPOS_EXTERNAL_E2E_PROFILE_IDS ?? singleProfileId)
  .split(",").map((value) => value.trim()).filter(Boolean);
const groupId = (process.env.ACPOS_EXTERNAL_E2E_GROUP_ID ?? "").trim();
const secondaryGroupId = (process.env.ACPOS_EXTERNAL_E2E_SECONDARY_GROUP_ID ?? "").trim();
const secondaryExpectedProvider = (process.env.ACPOS_EXTERNAL_E2E_SECONDARY_EXPECTED_PROVIDER ?? "").trim();
const secondaryExpectedModel = (process.env.ACPOS_EXTERNAL_E2E_SECONDARY_EXPECTED_MODEL ?? "").trim();
const blockedGroupId = (process.env.ACPOS_EXTERNAL_E2E_BLOCKED_GROUP_ID ?? "").trim();
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

  const sandboxTests = [];
  for (const testedProfile of tested) {
    const sandbox = await fetch(`${base}/v1/aiapi/sandbox-tests`, {
      method: "POST",
      cache: "no-store",
      headers: {
        ...cookieHeaders(cookie),
        "content-type": "application/json",
        "x-correlation-id": crypto.randomUUID(),
      },
      body: JSON.stringify({
        profile_id: testedProfile.profile_id,
        canonical_instruction: "ACPOS AIAPI acceptance dry-run compile. Preserve canonical meaning and do not send an external Provider request.",
      }),
    });
    const sandboxBody = await json(sandbox, `SANDBOX_${testedProfile.profile_id}`);
    assert(
      sandbox.status === 200 && sandboxBody?.ok === true,
      `SANDBOX_HTTP_${testedProfile.profile_id}_${sandbox.status}_${sandboxBody?.reason_code ?? "UNKNOWN"}`,
    );
    assert(sandboxBody?.value?.status === "PASS", `SANDBOX_STATUS_${testedProfile.profile_id}`);
    assert(sandboxBody?.value?.dry_run === true, `SANDBOX_NOT_DRY_RUN_${testedProfile.profile_id}`);
    assert(
      sandboxBody?.value?.external_request_sent === false,
      `SANDBOX_EXTERNAL_REQUEST_FORBIDDEN_${testedProfile.profile_id}`,
    );
    assert(
      typeof sandboxBody?.value?.test_id === "string" && sandboxBody.value.test_id.length > 0,
      `SANDBOX_TEST_ID_MISSING_${testedProfile.profile_id}`,
    );
    sandboxTests.push({
      profile_id: testedProfile.profile_id,
      test_id: sandboxBody.value.test_id,
    });
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

  let secondaryRoute = null;
  if (secondaryGroupId) {
    const secondary = await fetch(`${base}/v1/aiapi/routes`, {
      method: "POST",
      cache: "no-store",
      headers: {
        ...cookieHeaders(cookie),
        "content-type": "application/json",
        "x-correlation-id": crypto.randomUUID(),
      },
      body: JSON.stringify({
        candidate_group_id: secondaryGroupId,
        required_capability: capability,
        use_case: "PRODUCTION_EXTERNAL_PROVIDER_SECONDARY_ACCEPTANCE",
        data_classification: classification,
        canonical_instruction: "ACPOS secondary Provider acceptance check. Return a short acknowledgement.",
        scoped_context: { acceptance_scope: "GATE_22_SECONDARY_PROVIDER_ROUTE" },
      }),
    });
    const secondaryBody = await json(secondary, "SECONDARY_PROVIDER_ROUTE");
    assert(
      secondary.status === 200 && secondaryBody?.ok === true,
      `SECONDARY_PROVIDER_ROUTE_HTTP_${secondary.status}_${secondaryBody?.reason_code ?? "UNKNOWN"}`,
    );
    const secondaryValue = secondaryBody?.value ?? {};
    assert(secondaryValue.status === "SUCCESS", `SECONDARY_PROVIDER_ROUTE_STATUS_${secondaryValue.status ?? "UNRESOLVED"}`);
    assert(secondaryValue.external_request_sent === true, "SECONDARY_PROVIDER_EXTERNAL_REQUEST_NOT_SENT");
    assert(secondaryValue.worker?.succeeded === 1, "SECONDARY_PROVIDER_WORKER_NOT_SUCCESSFUL");
    assert(
      typeof secondaryValue.route_decision_id === "string" && secondaryValue.route_decision_id.length > 0,
      "SECONDARY_PROVIDER_DECISION_ID_MISSING",
    );
    const secondaryDecision = await fetch(
      `${base}/v1/aiapi/routes/${encodeURIComponent(secondaryValue.route_decision_id)}`,
      { method: "GET", cache: "no-store", headers: cookieHeaders(cookie) },
    );
    const secondaryDecisionBody = await json(secondaryDecision, "SECONDARY_ROUTE_DECISION");
    assert(secondaryDecision.status === 200 && secondaryDecisionBody?.ok === true, "SECONDARY_ROUTE_DECISION_READ_FAILED");
    const secondaryResolved = secondaryDecisionBody?.value ?? {};
    assert(secondaryResolved.status === "SUCCESS", "SECONDARY_ROUTE_DECISION_NOT_SUCCESS");
    assert(secondaryResolved.payload?.external_request_sent === true, "SECONDARY_ROUTE_EXTERNAL_REQUEST_NOT_ATTESTED");
    if (secondaryExpectedProvider) {
      assert(secondaryResolved.provider_id === secondaryExpectedProvider, `SECONDARY_PROVIDER_MISMATCH_${secondaryResolved.provider_id ?? "UNRESOLVED"}`);
    }
    if (secondaryExpectedModel) {
      assert(secondaryResolved.model_id === secondaryExpectedModel, `SECONDARY_MODEL_MISMATCH_${secondaryResolved.model_id ?? "UNRESOLVED"}`);
    }
    secondaryRoute = {
      provider_id: secondaryResolved.provider_id,
      model_id: secondaryResolved.model_id,
      route_decision_id: secondaryValue.route_decision_id,
    };
  }

  let blockedRouteVerified = false;
  if (blockedGroupId) {
    const blockedRoute = await fetch(`${base}/v1/aiapi/routes`, {
      method: "POST",
      cache: "no-store",
      headers: {
        ...cookieHeaders(cookie),
        "content-type": "application/json",
        "x-correlation-id": crypto.randomUUID(),
      },
      body: JSON.stringify({
        candidate_group_id: blockedGroupId,
        required_capability: capability,
        use_case: "PRODUCTION_EXTERNAL_PROVIDER_FAIL_CLOSED_ACCEPTANCE",
        data_classification: classification,
        canonical_instruction: "This acceptance request must not leave ACPOS because all members are health-gated.",
        scoped_context: { acceptance_scope: "GATE_22_FAIL_CLOSED" },
      }),
    });
    const blockedBody = await json(blockedRoute, "BLOCKED_PROVIDER_ROUTE");
    assert(blockedRoute.status === 200 && blockedBody?.ok === true, `BLOCKED_ROUTE_HTTP_${blockedRoute.status}`);
    const blockedValue = blockedBody?.value ?? {};
    assert(blockedValue.status === "BLOCKED", `BLOCKED_ROUTE_STATUS_${blockedValue.status ?? "UNRESOLVED"}`);
    assert(blockedValue.reason === "NO_ELIGIBLE_PROVIDER_MEMBER", `BLOCKED_ROUTE_REASON_${blockedValue.reason ?? "UNRESOLVED"}`);
    assert(blockedValue.eligible_members === 0, "BLOCKED_ROUTE_ELIGIBLE_MEMBER_PRESENT");
    assert(blockedValue.external_request_sent === false, "BLOCKED_ROUTE_EXTERNAL_REQUEST_SENT");
    assert(
      typeof blockedValue.route_decision_id === "string" && blockedValue.route_decision_id.length > 0,
      "BLOCKED_ROUTE_DECISION_ID_MISSING",
    );
    const blockedDecision = await fetch(
      `${base}/v1/aiapi/routes/${encodeURIComponent(blockedValue.route_decision_id)}`,
      { method: "GET", cache: "no-store", headers: cookieHeaders(cookie) },
    );
    const blockedDecisionBody = await json(blockedDecision, "BLOCKED_ROUTE_DECISION");
    assert(blockedDecision.status === 200 && blockedDecisionBody?.ok === true, "BLOCKED_ROUTE_DECISION_READ_FAILED");
    assert(blockedDecisionBody?.value?.status === "BLOCKED", "BLOCKED_ROUTE_DECISION_NOT_BLOCKED");
    assert(blockedDecisionBody?.value?.payload?.external_request_sent === false, "BLOCKED_ROUTE_DECISION_EXTERNAL_REQUEST_ATTESTED");
    blockedRouteVerified = true;
  }

  if (profileFailures.length) {
    process.stdout.write(
      `PRODUCTION_EXTERNAL_PROVIDER_E2E_PARTIAL release_sha=${healthBody.release_sha} profile_tests_passed=${tested.length} profile_tests_failed=${profileFailures.length} failed_profiles=${profileFailures.map((row) => row.profile_id).join(",")} route_provider=${resolved.provider_id} route_model=${resolved.model_id} worker_succeeded=1 sandbox_tests=${sandboxTests.length} secondary_route_provider=${secondaryRoute?.provider_id ?? "NONE"} blocked_route_verified=${blockedRouteVerified} external_request_sent=true provider_matrix_complete=false plaintext_persisted=false\n`,
    );
  }

  process.stdout.write(
    `PRODUCTION_EXTERNAL_PROVIDER_E2E_PASS release_sha=${healthBody.release_sha} profile_tests=${tested.length} providers=${tested.map((row) => row.provider_id).join(",")} capability=${capability} route_provider=${resolved.provider_id} route_model=${resolved.model_id} route_decision_id=${decisionId} worker_succeeded=1 sandbox_tests=${sandboxTests.length} secondary_route_provider=${secondaryRoute?.provider_id ?? "NONE"} secondary_route_model=${secondaryRoute?.model_id ?? "NONE"} blocked_route_verified=${blockedRouteVerified} external_request_sent=true provider_matrix_complete=${profileFailures.length === 0} plaintext_persisted=false\n`,
  );
} finally {
  await logout(cookie);
}
