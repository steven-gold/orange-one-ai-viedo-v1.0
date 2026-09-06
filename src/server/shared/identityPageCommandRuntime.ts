import { createHash } from "node:crypto";
import { cookies } from "next/headers";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { configureCoreRuntime, type CoreRuntimeBindings } from "@/server/core/coreRuntime";
import type { CoreRuntimeRequest } from "@/domain/core/coreRuntimeContract";
import { configureDbReadModelRuntime, type DbReadRequest } from "@/server/database/dbReadModelRuntime";
import { configureIamRuntime, type IamRuntimeRequest } from "@/server/iam/iamRuntime";
import { executeProductionIamCommand } from "@/server/iam/productionIamCommandRuntime";
import { configureDepartmentOperationRuntime } from "@/server/shared/departmentOperationRuntime";
import { configureInfoCommandRuntime, type InfoRequest } from "@/server/info/infoCommandRuntime";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { hashSessionToken, IDENTITY_COOKIE_NAME, resolveIdentityFromCookie, type IdentityActor } from "@/server/identity/identityRuntime";
import { CURRENT_PAGE_RESOURCE_KEYS } from "@/server/shared/pageCatalogProjectionRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import { configureQaRuntime, type QaRequest } from "@/server/qa/qaRuntime";
import { configureKnowledgeRuntime } from "@/server/knowledge/knowledgeRuntime";
import type { KnowledgeRuntimeRequest } from "@/domain/knowledge/knowledgeRuntimeContract";
import { configureConversationRuntime, type ConversationRequest } from "@/server/shared/conversationRuntime";
import { configureStrategyDecisionRuntime } from "@/server/strategy/strategyDecisionRuntime";
import { configureSocCommandRuntime } from "@/server/social/socCommandRuntime";
import type { SocRuntimeRequest } from "@/server/testing/controlledSocTestRuntime";
import { configureErpCommandRuntime } from "@/server/erp/erpCommandRuntime";
import type { ErpRuntimeRequest } from "@/server/testing/controlledErpTestRuntime";
import { configureSystemLifecycleRuntime } from "@/server/system/systemLifecycleRuntime";
import { configureAiApiCommandRuntime } from "@/server/aiApi/aiApiCommandRuntime";
import { executeProductionAiApiCommand, auditProductionAiApiCommand } from "@/server/aiApi/productionAiApiCommandRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;

let bound = false;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function asJsonObject(value: unknown): Record<string, unknown> | null {
  if (typeof value === "string") {
    try {
      return asRecord(JSON.parse(value));
    } catch {
      return null;
    }
  }
  return asRecord(value);
}

function emptyObjectMatches(assignmentScope: unknown, requestScope: Record<string, never>): boolean {
  const scope = asJsonObject(assignmentScope);
  if (!scope) return false;
  return Object.keys(scope).every((key) => key in requestScope && Object.is(scope[key], requestScope[key as never]));
}

function conditionAllows(condition: unknown): boolean {
  const object = asJsonObject(condition);
  if (!object) return false;
  return Object.keys(object).length === 0;
}

function sha256(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}

function firstRow(rows: unknown): Record<string, unknown> | null {
  return Array.isArray(rows) ? asRecord(rows[0]) : null;
}

async function readSessionCookie(): Promise<string | undefined> {
  try {
    const jar = await cookies();
    return jar.get(IDENTITY_COOKIE_NAME)?.value;
  } catch {
    return undefined;
  }
}

type IdentityContext = {
  actor: IdentityActor;
  session_token_hash: string;
};

async function requireIdentityContext(): Promise<IdentityContext> {
  await ensureProductionNeonRuntime();
  const cookieValue = await readSessionCookie();
  const identity = await resolveIdentityFromCookie(cookieValue);
  if (!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  if (!cookieValue) throw new NamedRuntimeError("RLS_SESSION_CONTEXT_REQUIRED");
  return {
    actor: identity.actor,
    session_token_hash: hashSessionToken(cookieValue),
  };
}

async function requireActor(): Promise<IdentityActor> {
  return (await requireIdentityContext()).actor;
}

async function requireSql(): Promise<SqlClient> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  return sql;
}

async function evaluatePageView(resourceKey: string): Promise<{ allowed: true; actor: IdentityActor } | { allowed: false; reason_code: string }> {
  const sql = getProductionNeonSql();
  if (!sql) {
    await ensureProductionNeonRuntime();
  }
  const boundSql = getProductionNeonSql();
  if (!boundSql) return { allowed: false, reason_code: "DATABASE_RUNTIME_NOT_BOUND" };
  const cookieValue = await readSessionCookie();
  const identity = await resolveIdentityFromCookie(cookieValue);
  if (!identity.ok) return { allowed: false, reason_code: identity.reason_code };
  if (!cookieValue) return { allowed: false, reason_code: "RLS_SESSION_CONTEXT_REQUIRED" };
  try {
    const rows = await runRlsActorQuery(
      boundSql,
      hashSessionToken(cookieValue),
      boundSql`
        SELECT a.effect, a.scope, a.condition
        FROM account_permission_assignments a
        JOIN permission_resources r ON r.resource_id = a.resource_id
        WHERE a.user_id = ${identity.actor.user_id}
          AND r.resource_key = ${resourceKey}
          AND r.resource_type = 'PAGE'
          AND r.active = true
          AND a.action = 'VIEW'
          AND a.status = 'APPROVED'
          AND a.effective_from <= now()
          AND (a.effective_to IS NULL OR a.effective_to > now())
      `,
    );
    const requestScope = {} as Record<string, never>;
    const matched: string[] = [];
    for (const raw of Array.isArray(rows) ? rows : []) {
      const row = asRecord(raw);
      if (!row) continue;
      if (!emptyObjectMatches(row.scope, requestScope)) continue;
      if (!conditionAllows(row.condition)) continue;
      const effect = asText(row.effect);
      if (effect) matched.push(effect);
    }
    if (matched.includes("DENY")) return { allowed: false, reason_code: "PERMISSION_DENIED" };
    if (matched.includes("ALLOW")) return { allowed: true, actor: identity.actor };
    return { allowed: false, reason_code: "PERMISSION_OR_SCOPE_DENIED" };
  } catch {
    return { allowed: false, reason_code: "AUTHORIZATION_EVALUATION_FAILED" };
  }
}

async function evaluateResourceAction(
  resourceKey: string,
  action: string,
): Promise<{ allowed: true; actor: IdentityActor } | { allowed: false; reason_code: string }> {
  if (!resourceKey || !action) return { allowed: false, reason_code: "OPERATION_PERMISSION_MAPPING_REQUIRED" };
  if (!getProductionNeonSql()) await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) return { allowed: false, reason_code: "DATABASE_RUNTIME_NOT_BOUND" };
  const cookieValue = await readSessionCookie();
  const identity = await resolveIdentityFromCookie(cookieValue);
  if (!identity.ok) return { allowed: false, reason_code: identity.reason_code };
  if (!cookieValue) return { allowed: false, reason_code: "RLS_SESSION_CONTEXT_REQUIRED" };
  try {
    const result = await runRlsActorQuery(
      sql,
      hashSessionToken(cookieValue),
      sql`
        SELECT a.effect,a.scope,a.condition
        FROM account_permission_assignments a
        JOIN permission_resources r ON r.resource_id=a.resource_id
        WHERE a.user_id=${identity.actor.user_id}
          AND r.resource_key=${resourceKey}
          AND r.resource_type IN ('ACTION','CONTROL','API','SENSITIVE_PERMISSION')
          AND r.active=true
          AND ${action}=ANY(
            SELECT jsonb_array_elements_text(
              CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
            )
          )
          AND a.action=${action}
          AND a.status='APPROVED'
          AND a.effective_from<=now()
          AND (a.effective_to IS NULL OR a.effective_to>now())
      `,
    );
    const requestScope={} as Record<string,never>;
    const matched:string[]=[];
    for(const raw of Array.isArray(result)?result:[]){
      const row=asRecord(raw);
      if(!row)continue;
      if(!emptyObjectMatches(row.scope,requestScope))continue;
      if(!conditionAllows(row.condition))continue;
      const effect=asText(row.effect);
      if(effect)matched.push(effect);
    }
    if(matched.includes("DENY"))return{allowed:false,reason_code:"PERMISSION_DENIED"};
    if(matched.includes("ALLOW"))return{allowed:true,actor:identity.actor};
    return{allowed:false,reason_code:"PERMISSION_OR_SCOPE_DENIED"};
  } catch {
    return{allowed:false,reason_code:"AUTHORIZATION_EVALUATION_FAILED"};
  }
}

const IAM_OPERATION_PERMISSION: Readonly<Record<string,{resource_key:string;action:string}>> = {
  searchProjection:{resource_key:"action:admin:IAM-01:ACT-SEARCH",action:"INVOKE"},
  saveDraft:{resource_key:"action:admin:IAM-02:ACT-DRAFT-SAVE",action:"INVOKE"},
  validateDraft:{resource_key:"action:admin:IAM-02:ACT-DRAFT-VALIDATE",action:"INVOKE"},
  previewAuthorizationImpact:{resource_key:"action:admin:IAM-02:ACT-ACCOUNT-PERMISSION-PREVIEW",action:"INVOKE"},
  assignAccountPermission:{resource_key:"action:admin:IAM-05:ACT-CONFIGURE",action:"INVOKE"},
  revokeAccountPermission:{resource_key:"action:admin:IAM-05:ACT-CONFIGURE",action:"INVOKE"},
};

const GOVERNANCE_PERMISSION_CONTEXT: Readonly<Record<string,{
  configure:{resource_key:string;action:string};
  approve:{resource_key:string;action:string};
}>> = {
  "admin:IAM-01":{
    configure:{resource_key:"action:admin:IAM-05:ACT-CONFIGURE",action:"INVOKE"},
    approve:{resource_key:"action:admin:IAM-05:ACT-APPROVE",action:"INVOKE"},
  },
  "admin:AIAPI-01":{
    configure:{resource_key:"action:admin:AIAPI-04:ACT-CONFIGURE",action:"INVOKE"},
    approve:{resource_key:"action:admin:AIAPI-04:ACT-APPROVE",action:"INVOKE"},
  },
  "admin:SG-02":{
    configure:{resource_key:"action:admin:SG-02:ACT-CONFIGURE",action:"INVOKE"},
    approve:{resource_key:"action:admin:SG-02:ACT-APPROVE",action:"INVOKE"},
  },
};

async function authorizeIam(request:IamRuntimeRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  const page=await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["admin:IAM-01"]);
  if(!page.allowed)return page;
  if(request.operation==="getUiProjection")return{allowed:true};
  if(request.operation==="configureGovernedResource"||request.operation==="approveGovernedResource"){
    const payload=asRecord(request.payload)??{};
    const pageUid=asText(payload.page_uid);
    if(!pageUid)return{allowed:false,reason_code:"IAM_OPERATION_PERMISSION_CONTEXT_REQUIRED"};
    const context=GOVERNANCE_PERMISSION_CONTEXT[pageUid];
    if(!context)return{allowed:false,reason_code:"IAM_OPERATION_PERMISSION_CONTEXT_UNREGISTERED"};
    const permission=request.operation==="configureGovernedResource"?context.configure:context.approve;
    const gate=await evaluateResourceAction(permission.resource_key,permission.action);
    return gate.allowed?{allowed:true}:gate;
  }
  const permission=IAM_OPERATION_PERMISSION[request.operation];
  if(!permission)return{allowed:false,reason_code:"IAM_OPERATION_PERMISSION_MAPPING_REQUIRED"};
  const gate=await evaluateResourceAction(permission.resource_key,permission.action);
  return gate.allowed?{allowed:true}:gate;
}

async function authorizeCore(request: CoreRuntimeRequest): Promise<{ allowed: true } | { allowed: false; reason_code: string }> {
  const gate = await evaluatePageView(CURRENT_PAGE_RESOURCE_KEYS["CORE-01"]);
  if (!gate.allowed) return gate;
  void request;
  return { allowed: true };
}

function payloadRecord(request: CoreRuntimeRequest): Record<string, unknown> {
  return asRecord(request.payload) ?? {};
}

function requirePayloadText(payload: Record<string, unknown>, key: string): string {
  const value = asText(payload[key]);
  if (!value) throw new NamedRuntimeError(`STORY_CANDIDATE_FIELD_REQUIRED:${key}`);
  return value;
}

function requirePayloadJson(payload: Record<string, unknown>, key: string): string {
  const value = payload[key];
  if (value === undefined || value === null) {
    throw new NamedRuntimeError(`STORY_CANDIDATE_FIELD_REQUIRED:${key}`);
  }
  try {
    return JSON.stringify(value);
  } catch {
    throw new NamedRuntimeError(`STORY_CANDIDATE_FIELD_INVALID:${key}`);
  }
}

function slugCode(title: string, prefix: string): string {
  const base = title.toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 20);
  return `${prefix}-${base || "ITEM"}-${Date.now().toString(36).toUpperCase()}`;
}

async function executeCore(request: CoreRuntimeRequest): Promise<unknown> {
  const sql = await requireSql();
  const identityContext = await requireIdentityContext();
  const actor = identityContext.actor;
  const payload = payloadRecord(request);

  switch (request.port_uid) {
    case "CORE-01-PORT-PROJECT-CREATE": {
      const title = asText(payload.title) ?? asText(payload.fixture_label);
      if (!title) throw new NamedRuntimeError("PROJECT_TITLE_REQUIRED");
      const project_code = asText(payload.project_code) ?? slugCode(title, "PRJ");
      const workspaceRows = await sql`
        SELECT workspace_id::text AS workspace_id
        FROM workspaces
        WHERE status = 'READY'
        ORDER BY created_at ASC
        LIMIT 1
      `;
      const workspace_id = asText(firstRow(workspaceRows)?.workspace_id);
      if (!workspace_id) throw new NamedRuntimeError("WORKSPACE_NOT_READY");
      const inserted = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          INSERT INTO projects (workspace_id, project_code, title, owner_id, status)
          VALUES (${workspace_id}::uuid, ${project_code}, ${title}, ${actor.user_id}::uuid, 'DRAFT')
          RETURNING project_id::text AS project_id
        `,
      );
      const project_id = asText(firstRow(inserted)?.project_id);
      if (!project_id) throw new NamedRuntimeError("PROJECT_INSERT_FAILED");
      const content_hash = sha256(`project:${project_id}:v1:${title}:${project_code}`);
      const story_core = JSON.stringify({ title });
      const versionRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          INSERT INTO project_versions (
            project_id, version_no, status, story_core, content_hash, created_by
          ) VALUES (
            ${project_id}::uuid, 1, 'DRAFT', ${story_core}::jsonb, ${content_hash}, ${actor.user_id}::uuid
          )
          RETURNING project_version_id::text AS project_version_ref
        `,
      );
      const project_version_ref = asText(firstRow(versionRows)?.project_version_ref);
      if (!project_version_ref) throw new NamedRuntimeError("PROJECT_VERSION_INSERT_FAILED");
      await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          UPDATE projects
          SET active_version_id = ${project_version_ref}::uuid
          WHERE project_id = ${project_id}::uuid
        `,
      );
      return { project_id, project_version_ref, project_code, title, state: "DRAFT" };
    }

    case "CORE-01-PORT-PROJECT-VALIDATE": {
      const projectVersionId = asText(request.path_params?.projectVersionId);
      if (!projectVersionId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:projectVersionId");
      const rows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          UPDATE project_versions
          SET decision_reason = 'VALIDATED'
          WHERE project_version_id = ${projectVersionId}::uuid
            AND status = 'DRAFT'
          RETURNING project_version_id::text AS project_version_ref, project_id::text AS project_id
        `,
      );
      const row = firstRow(rows);
      if (!row) throw new NamedRuntimeError("PROJECT_VERSION_NOT_IN_DRAFT");
      return { project_id: asText(row.project_id), project_version_ref: asText(row.project_version_ref), state: "VALIDATED" };
    }

    case "CORE-01-PORT-PROJECT-CONFIRM": {
      const id = asText(request.path_params?.id);
      if (!id) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:id");
      const rows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          UPDATE project_versions
          SET status = 'CORE_MODELING'
          WHERE project_version_id = ${id}::uuid
            AND status = 'DRAFT'
            AND decision_reason = 'VALIDATED'
          RETURNING project_version_id::text AS project_version_ref, project_id::text AS project_id
        `,
      );
      const row = firstRow(rows);
      if (!row) throw new NamedRuntimeError("PROJECT_VERSION_NOT_VALIDATED");
      const project_id = asText(row.project_id);
      await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          UPDATE projects
          SET status = 'CORE_MODELING', active_version_id = ${id}::uuid
          WHERE project_id = ${project_id}::uuid
        `,
      );
      return { project_id, project_version_ref: asText(row.project_version_ref), state: "CORE_MODELING" };
    }

    case "CORE-01-PORT-TOPIC-CREATE": {
      const projectId = asText(request.path_params?.projectId);
      if (!projectId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:projectId");
      const title = asText(payload.title) ?? asText(payload.fixture_label);
      if (!title) throw new NamedRuntimeError("TOPIC_TITLE_REQUIRED");
      const topic_code = asText(payload.topic_code) ?? slugCode(title, "TPC");
      const lockRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT mother_lock_id::text AS mother_lock_id, project_version_id::text AS project_version_id
          FROM mother_locks
          WHERE project_id = ${projectId}::uuid
            AND status = 'MOTHER_LOCKED'
          ORDER BY lock_version DESC
          LIMIT 1
        `,
      );
      const lock = firstRow(lockRows);
      const mother_lock_id = asText(lock?.mother_lock_id);
      const mother_project_version_id = asText(lock?.project_version_id);
      if (!mother_lock_id || !mother_project_version_id) throw new NamedRuntimeError("MOTHER_LOCK_REQUIRED");
      const topicRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          INSERT INTO topics (project_id, topic_code, title, mother_lock_id, status)
          VALUES (${projectId}::uuid, ${topic_code}, ${title}, ${mother_lock_id}::uuid, 'DRAFT')
          RETURNING topic_id::text AS topic_id
        `,
      );
      const topic_id = asText(firstRow(topicRows)?.topic_id);
      if (!topic_id) throw new NamedRuntimeError("TOPIC_INSERT_FAILED");
      const content_hash = sha256(`topic:${topic_id}:v1:${title}`);
      const boundary = JSON.stringify({ title });
      const bridge = JSON.stringify({});
      const versionRows = await sql`
        INSERT INTO topic_versions (
          topic_id, version_no, mother_project_version_id, boundary, bridge, status, content_hash, created_by
        ) VALUES (
          ${topic_id}::uuid, 1, ${mother_project_version_id}::uuid, ${boundary}::jsonb, ${bridge}::jsonb, 'DRAFT', ${content_hash}, ${actor.user_id}::uuid
        )
        RETURNING topic_version_id::text AS topic_version_ref
      `;
      const topic_version_ref = asText(firstRow(versionRows)?.topic_version_ref);
      if (!topic_version_ref) throw new NamedRuntimeError("TOPIC_VERSION_INSERT_FAILED");
      await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          UPDATE topics SET active_version_id = ${topic_version_ref}::uuid WHERE topic_id = ${topic_id}::uuid
        `,
      );
      return { topic_id, topic_version_ref, project_id: projectId, title, state: "DRAFT" };
    }

    case "CORE-01-PORT-THREAD-CREATE": {
      const projectId = asText(request.path_params?.projectId);
      if (!projectId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:projectId");
      const work_item = asText(payload.work_item);
      if (!work_item) throw new NamedRuntimeError("REQUIRED_WORK_ITEM_MISSING");
      const topic_id = asText(payload.topic_id);
      const title = `${work_item} / ${new Date().toISOString()}`;
      const projectRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT p.workspace_id::text AS workspace_id
          FROM projects p
          WHERE p.project_id = ${projectId}::uuid
          LIMIT 1
        `,
      );
      const workspace_id = asText(firstRow(projectRows)?.workspace_id);
      if (!workspace_id) throw new NamedRuntimeError("PROJECT_NOT_FOUND");
      const conversation_id = crypto.randomUUID();
      const threadRows = topic_id
        ? await runRlsActorQuery(
            sql,
            identityContext.session_token_hash,
            sql`
              INSERT INTO conversations (conversation_id, workspace_id, project_id, topic_id, title, created_by)
              VALUES (${conversation_id}::uuid, ${workspace_id}::uuid, ${projectId}::uuid, ${topic_id}::uuid, ${title}, ${actor.user_id}::uuid)
              RETURNING conversation_id::text AS conversation_id
            `,
          )
        : await runRlsActorQuery(
            sql,
            identityContext.session_token_hash,
            sql`
              INSERT INTO conversations (conversation_id, workspace_id, project_id, title, created_by)
              VALUES (${conversation_id}::uuid, ${workspace_id}::uuid, ${projectId}::uuid, ${title}, ${actor.user_id}::uuid)
              RETURNING conversation_id::text AS conversation_id
            `,
          );
      if (!asText(firstRow(threadRows)?.conversation_id)) throw new NamedRuntimeError("CONVERSATION_INSERT_FAILED");
      return { conversation_id, project_id: projectId, work_item, topic_id };
    }

    case "CORE-01-PORT-MESSAGE-SEND": {
      const conversationId = asText(request.path_params?.conversationId);
      if (!conversationId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:conversationId");
      const message = asText(payload.message);
      if (!message) throw new NamedRuntimeError("MESSAGE_REQUIRED");
      const seqRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT COALESCE(MAX(sequence_no), 0)::int AS seq
          FROM conversation_messages
          WHERE conversation_id = ${conversationId}::uuid
        `,
      );
      const seq = Number(firstRow(seqRows)?.seq ?? 0) + 1;
      const content = JSON.stringify({ text: message, instruction_kind: asText(payload.instruction_kind) ?? "MESSAGE" });
      const message_ref = crypto.randomUUID();
      const msgRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          INSERT INTO conversation_messages (
            conversation_message_id, conversation_id, sequence_no, actor_type, actor_ref, message_content
          ) VALUES (
            ${message_ref}::uuid, ${conversationId}::uuid, ${seq}, 'USER', ${actor.user_id}, ${content}::jsonb
          )
          RETURNING conversation_message_id::text AS message_ref
        `,
      );
      if (!asText(firstRow(msgRows)?.message_ref)) throw new NamedRuntimeError("MESSAGE_INSERT_FAILED");
      return { conversation_id: conversationId, message_ref, accepted: true };
    }

    case "CORE-01-PORT-STORY-CANDIDATE": {
      const projectId = asText(request.path_params?.projectId);
      if (!projectId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:projectId");
      const projectRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT project_id::text AS project_id, status::text AS status
          FROM projects
          WHERE project_id = ${projectId}::uuid
          LIMIT 1
        `,
      );
      const project = firstRow(projectRows);
      if (!project) throw new NamedRuntimeError("PROJECT_NOT_FOUND");
      if (asText(project.status) !== "CORE_MODELING") throw new NamedRuntimeError("PROJECT_NOT_CONFIRMED");
      const candidate_key = asText(payload.candidate_key) ?? `STORY-${Date.now().toString(36).toUpperCase()}`;
      const content = requirePayloadJson(payload, "content");
      const strengths = requirePayloadJson(payload, "strengths");
      const weaknesses = requirePayloadJson(payload, "weaknesses");
      const market_positioning = requirePayloadText(payload, "market_positioning");
      const character_space = requirePayloadText(payload, "character_space");
      const long_form_extension = requirePayloadText(payload, "long_form_extension");
      const foreshadowing_capacity = requirePayloadText(payload, "foreshadowing_capacity");
      const production_cost = requirePayloadText(payload, "production_cost");
      const production_risk = requirePayloadText(payload, "production_risk");
      const recommendation = requirePayloadText(payload, "recommendation");
      const wizard_session_id = asText(payload.wizard_session_id);
      const storyRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          INSERT INTO story_candidates (
            story_candidate_id, project_id, candidate_key, content, status, wizard_session_id,
            strengths, weaknesses, market_positioning, character_space, long_form_extension,
            foreshadowing_capacity, production_cost, production_risk, recommendation,
            generated_by_subject_type
          ) VALUES (
            gen_random_uuid(), ${projectId}::uuid, ${candidate_key}, ${content}::jsonb, 'CANDIDATE',
            ${wizard_session_id}::uuid, ${strengths}::jsonb, ${weaknesses}::jsonb,
            ${market_positioning}, ${character_space}, ${long_form_extension},
            ${foreshadowing_capacity}, ${production_cost}, ${production_risk},
            ${recommendation}, 'USER'
          )
          RETURNING story_candidate_id::text AS story_candidate_set_ref
        `,
      );
      const story_candidate_set_ref = asText(firstRow(storyRows)?.story_candidate_set_ref);
      if (!story_candidate_set_ref) throw new NamedRuntimeError("STORY_CANDIDATE_INSERT_FAILED");
      return { story_candidate_set_ref, project_id: projectId };
    }

    case "CORE-01-PORT-MOTHER-LOCK": {
      const project_id = asText(payload.project_id);
      const project_version_ref = asText(payload.project_version_ref);
      if (!project_id || !project_version_ref) throw new NamedRuntimeError("REQUIRED_PROJECT_VERSION_REF_MISSING");
      const versionRows = await runRlsActorQuery(
        sql,
        identityContext.session_token_hash,
        sql`
          SELECT content_hash, status::text AS status
          FROM project_versions
          WHERE project_version_id = ${project_version_ref}::uuid
            AND project_id = ${project_id}::uuid
          LIMIT 1
        `,
      );
      const version = firstRow(versionRows);
      const content_hash = asText(version?.content_hash);
      if (!content_hash) throw new NamedRuntimeError("PROJECT_VERSION_NOT_FOUND");
      const evidence = JSON.stringify({ evidence_refs: payload.evidence_refs ?? [] });
      const reviewer_path = JSON.stringify([]);
      const reviewRows = await sql`
        INSERT INTO lock_reviews (
          lock_kind, target_type, target_version_id, evidence, reviewer_path, status, expected_target_hash, requested_by
        ) VALUES (
          'MOTHER', 'PROJECT_VERSION', ${project_version_ref}::uuid, ${evidence}::jsonb, ${reviewer_path}::jsonb, 'IN_REVIEW', ${content_hash}, ${actor.user_id}::uuid
        )
        RETURNING lock_review_id::text AS lock_review_id
      `;
      const lock_review_id = asText(firstRow(reviewRows)?.lock_review_id);
      if (!lock_review_id) throw new NamedRuntimeError("LOCK_REVIEW_INSERT_FAILED");
      return { lock_review_id, project_id, project_version_ref, state: "IN_REVIEW" };
    }

    case "CORE-01-PORT-PROJECTION":
      return { reason_code: "USE_UI_PROJECTION_ROUTE" };

    default:
      throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
  }
}

const coreBindings: CoreRuntimeBindings = {
  authorize: authorizeCore,
  execute: executeCore,
  audit: async () => undefined,
};

async function authorizePage(resourceKey: string): Promise<{ allowed: true } | { allowed: false; reason_code: string }> {
  const gate = await evaluatePageView(resourceKey);
  if (!gate.allowed) return gate;
  return { allowed: true };
}

function dbProjection(partial: Record<string, unknown>) {
  return {
    page_state: "READY",
    values: {},
    lists: {},
    tables: {},
    gates: {
      "DB-01-GATE-PAGE": true,
      "DB-01-GATE-CONTEXT": true,
      "DB-01-GATE-ENTITY": true,
      "DB-01-GATE-SCHEMA": true,
      "DB-01-GATE-TRACE": true,
      "DB-01-GATE-MIGRATION": true,
      "DB-01-GATE-INTEGRITY": true,
      "DB-01-GATE-AUDIT": true,
    },
    filters: {},
    graph: null,
    trace: null,
    audit: null,
    source_sync: "neon:wild-wave",
    ...partial,
  };
}

async function readDb(request: DbReadRequest): Promise<unknown> {
  const sql = await requireSql();
  const query = asRecord(request.query) ?? {};
  const client = asRecord(query.client_state) ?? {};
  const search = asText(query.value) ?? asText(client.search) ?? "";

  if (request.port_uid === "DB-01-PORT-ENTITY-LIST") {
    const rows = await sql`
      SELECT table_name::text AS ref
      FROM information_schema.tables
      WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
      ORDER BY table_name
    `;
    const entities = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const ref = asText(asRecord(raw)?.ref);
      if (!ref) return [];
      if (search && !ref.toLowerCase().includes(search.toLowerCase())) return [];
      return [{ ref, label: ref, meta: { entity_type: "TABLE", domain: "public" } }];
    });
    return dbProjection({
      lists: { "DB-01-LIST-ENTITIES": entities },
      values: { "DB-01-FLD-ENV": "wild-wave", "DB-01-FLD-SCOPE": "public", "DB-01-FLD-HEALTH": "BOUND" },
    });
  }

  if (request.port_uid === "DB-01-PORT-SCHEMA") {
    const table = asText(client.entity_ref) ?? asText(query.value);
    if (!table) throw new NamedRuntimeError("ENTITY_REF_REQUIRED");
    const rows = await sql`
      SELECT column_name::text AS column_name, data_type::text AS data_type
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = ${table}
      ORDER BY ordinal_position
    `;
    const columns = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const row = asRecord(raw);
      const column_name = asText(row?.column_name);
      const data_type = asText(row?.data_type);
      if (!column_name || !data_type) return [];
      return [{ ref: column_name, label: `${column_name} ${data_type}` }];
    });
    return dbProjection({
      values: { "DB-01-FLD-ENTITY": table, "DB-01-FLD-TABLE": table },
      tables: { "DB-01-TBL-COLUMNS": columns },
    });
  }

  if (request.port_uid === "DB-01-PORT-MIGRATION") {
    const needle = asText(client.migration_search) ?? search;
    const rows = await sql`
      SELECT migration_id AS ref, applied_at::text AS applied_at, applied_by, approval_ref
      FROM schema_migration_history
      ORDER BY applied_at
    `;
    const migrations = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const row = asRecord(raw);
      const ref = asText(row?.ref);
      if (!ref) return [];
      if (needle && !ref.toLowerCase().includes(needle.toLowerCase())) return [];
      return [{ ref, label: ref, applied_at: asText(row?.applied_at), applied_by: asText(row?.applied_by), approval_ref: asText(row?.approval_ref) }];
    });
    return dbProjection({
      tables: { "DB-01-TBL-MIGRATIONS": migrations },
      values: { "DB-01-FLD-MIGRATION-HEAD": String(migrations.length) },
    });
  }

  if (request.port_uid === "DB-01-PORT-TRACE" || request.port_uid === "DB-01-PORT-INTEGRITY" || request.port_uid === "DB-01-PORT-AUDIT") {
    return dbProjection({
      lists: { "DB-01-LIST-FINDINGS": [] },
      trace: [],
      audit: [],
    });
  }

  throw new NamedRuntimeError("DB_READ_PORT_UNSUPPORTED");
}

async function executeIam(request: IamRuntimeRequest): Promise<unknown> {
  return executeProductionIamCommand(request);
}

async function executeInfo(request: InfoRequest): Promise<unknown> {
  if (request.operation_id === "refreshProjection") {
    return { refreshed: true };
  }
  if (request.operation_id !== "searchProjection") {
    throw new NamedRuntimeError("INFO_WRITE_RUNTIME_NOT_MATERIALIZED");
  }
  const sql = await requireSql();
  const identityContext = await requireIdentityContext();
  const payload = asRecord(request.payload) ?? {};
  const pageUid = asText(payload.page_uid);
  if (pageUid === "admin:IAM-01") {
    const needle = (asText(payload.query) ?? "").toLowerCase();
    const rows = await runRlsActorQuery(
      sql,
      identityContext.session_token_hash,
      sql`
        SELECT u.user_id::text AS ref, u.display_name AS label, u.email::text AS email
        FROM app_users u
        ORDER BY u.created_at DESC
      `,
    );
    const results = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
      const row = asRecord(raw);
      const ref = asText(row?.ref);
      const label = asText(row?.label);
      const email = asText(row?.email) ?? "";
      if (!ref || !label) return [];
      if (needle && !ref.toLowerCase().includes(needle) && !label.toLowerCase().includes(needle) && !email.toLowerCase().includes(needle)) return [];
      return [{ ref, label }];
    });
    return { results, matches: results.map((item) => item.ref) };
  }
  const q = `%${asText(payload.query) ?? ""}%`;
  const rows = await runRlsActorQuery(
    sql,
    identityContext.session_token_hash,
    sql`
      SELECT p.project_id::text AS ref, p.title AS label
      FROM projects p
      WHERE p.archived_at IS NULL
        AND (${q} = '%%' OR p.title ILIKE ${q} OR p.project_code ILIKE ${q})
      ORDER BY p.created_at DESC
      LIMIT 50
    `,
  );
  const results = (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    const label = asText(row?.label);
    if (!ref || !label) return [];
    return [{ ref, label }];
  });
  return { results };
}

function refItems(rows: unknown) {
  return (Array.isArray(rows) ? rows : []).flatMap((raw) => {
    const row = asRecord(raw);
    const ref = asText(row?.ref);
    const label = asText(row?.label) ?? ref;
    if (!ref || !label) return [];
    return [{ ref, label }];
  });
}

async function executeQa(_request: QaRequest): Promise<unknown> {
  void _request;
  throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
}

async function executeKnowledge(request: KnowledgeRuntimeRequest): Promise<unknown> {
  if (request.operation === "searchKnowledge") {
    const sql = await requireSql();
    const payload = asRecord(request.payload) ?? {};
    const q = `%${asText(payload.query) ?? ""}%`;
    const sources = await sql`
      SELECT knowledge_source_id::text AS ref, source_key AS label, status::text AS status
      FROM knowledge_sources
      WHERE ${q} = '%%' OR source_key ILIKE ${q} OR source_uri ILIKE ${q}
      ORDER BY created_at DESC
      LIMIT 50
    `;
    const evidence = await sql`
      SELECT evidence_record_id::text AS ref, source_uri AS label
      FROM evidence_records
      WHERE ${q} = '%%' OR source_uri ILIKE ${q}
      ORDER BY retrieved_at DESC
      LIMIT 50
    `;
    return { results: [...refItems(sources), ...refItems(evidence)] };
  }
  if (request.operation === "getCitation") {
    const sql = await requireSql();
    const citationId = asText(request.path_params?.citationId);
    if (!citationId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:citationId");
    const rows = await sql`
      SELECT evidence_record_id::text AS ref, source_uri AS label, citation, classification::text AS classification
      FROM evidence_records
      WHERE evidence_record_id = ${citationId}::uuid
      LIMIT 1
    `;
    const row = firstRow(rows);
    if (!row) throw new NamedRuntimeError("CITATION_NOT_FOUND");
    return row;
  }
  throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
}

async function executeConversation(request: ConversationRequest): Promise<unknown> {
  if (request.operation_id !== "sendConversationMessage") {
    throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
  }
  const sql = await requireSql();
  const identityContext = await requireIdentityContext();
  const actor = identityContext.actor;
  const payload = asRecord(request.payload) ?? {};
  const message = asText(payload.message);
  if (!message) throw new NamedRuntimeError("MESSAGE_REQUIRED");
  const conversationId = asText(request.conversation_id);
  if (!conversationId) throw new NamedRuntimeError("REQUIRED_PATH_REFERENCE_MISSING:conversationId");
  const exists = await runRlsActorQuery(
    sql,
    identityContext.session_token_hash,
    sql`
      SELECT conversation_id::text AS conversation_id
      FROM conversations
      WHERE conversation_id = ${conversationId}::uuid
      LIMIT 1
    `,
  );
  if (!asText(firstRow(exists)?.conversation_id)) throw new NamedRuntimeError("CONVERSATION_NOT_FOUND");
  const seqRows = await runRlsActorQuery(
    sql,
    identityContext.session_token_hash,
    sql`
      SELECT COALESCE(MAX(sequence_no), 0)::int AS seq
      FROM conversation_messages
      WHERE conversation_id = ${conversationId}::uuid
    `,
  );
  const seq = Number(firstRow(seqRows)?.seq ?? 0) + 1;
  const content = JSON.stringify({ text: message, instruction_kind: asText(payload.instruction_kind) ?? "MESSAGE" });
  const message_ref = crypto.randomUUID();
  const msgRows = await runRlsActorQuery(
    sql,
    identityContext.session_token_hash,
    sql`
      INSERT INTO conversation_messages (
        conversation_message_id, conversation_id, sequence_no, actor_type, actor_ref, message_content
      ) VALUES (
        ${message_ref}::uuid, ${conversationId}::uuid, ${seq}, 'USER', ${actor.user_id}, ${content}::jsonb
      )
      RETURNING conversation_message_id::text AS message_ref
    `,
  );
  if (!asText(firstRow(msgRows)?.message_ref)) throw new NamedRuntimeError("MESSAGE_INSERT_FAILED");
  return { conversation_id: conversationId, message_ref, accepted: true };
}

async function executeSoc(request: SocRuntimeRequest): Promise<unknown> {
  if (request.operation_id === "refreshProjection") return { refreshed: true };
  if (request.operation_id === "searchProjection") {
    const sql = await requireSql();
    const payload = asRecord(request.payload) ?? {};
    const q = `%${asText(payload.query) ?? ""}%`;
    const rows = await sql`
      SELECT channel_account_id::text AS ref, platform_key AS label, status::text AS status
      FROM channel_accounts
      WHERE ${q} = '%%' OR platform_key ILIKE ${q} OR external_account_ref ILIKE ${q}
      ORDER BY platform_key
      LIMIT 50
    `;
    return { results: refItems(rows) };
  }
  throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
}

async function executeErp(request: ErpRuntimeRequest): Promise<unknown> {
  if (request.operation_id === "refreshProjection" || request.operation_id === "refreshERPSnapshot") {
    return { refreshed: true };
  }
  const sql = await requireSql();
  if (request.operation_id === "getERPSyncStatus") {
    const rows = await sql`
      SELECT erp_sync_job_id::text AS ref, status::text AS label
      FROM erp_sync_jobs
      ORDER BY requested_at DESC
      LIMIT 50
    `;
    return { jobs: refItems(rows) };
  }
  if (request.operation_id === "getERPFailure") {
    const rows = await sql`
      SELECT erp_failure_id::text AS ref, failure_code AS label, status::text AS status
      FROM erp_failures
      ORDER BY occurred_at DESC
      LIMIT 50
    `;
    return { failures: refItems(rows) };
  }
  if (
    request.operation_id === "getERPFinanceFactPack"
    || request.operation_id === "getERPCapacityGuardrails"
    || request.operation_id === "getERPForecast"
  ) {
    const rows = await sql`
      SELECT erp_snapshot_id::text AS ref, snapshot_type AS label, completeness::text AS completeness
      FROM erp_snapshots
      ORDER BY created_at DESC
      LIMIT 20
    `;
    return { snapshots: refItems(rows) };
  }
  throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
}

export function bindIdentityPageCommandRuntimes(): void {
  if (bound || isControlledTestMode()) return;
  bound = true;
  configureCoreRuntime(coreBindings);
  configureDbReadModelRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["admin:DB-01"]),
    read: readDb,
    audit: async () => undefined,
  });
  configureIamRuntime({
    authorize: authorizeIam,
    execute: executeIam,
    audit: async () => undefined,
  });
  configureInfoCommandRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["workspace:INFO-01"]),
    execute: executeInfo,
    audit: async () => undefined,
  });
  configureDepartmentOperationRuntime({
    authorize: async () => {
      const identity = await resolveIdentityFromCookie(await readSessionCookie());
      if (!identity.ok) return { allowed: false, reason_code: identity.reason_code };
      return { allowed: true };
    },
    execute: async () => {
      throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
    },
    audit: async () => undefined,
  });
  configureQaRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["QA-01"]),
    execute: executeQa,
    audit: async () => undefined,
  });
  configureKnowledgeRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["admin:KB-01"]),
    execute: executeKnowledge,
    audit: async () => undefined,
  });
  configureConversationRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["workspace:STR-01"]),
    execute: executeConversation,
    audit: async () => undefined,
  });
  configureStrategyDecisionRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["workspace:STR-01"]),
    execute: async () => {
      throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
    },
    audit: async () => undefined,
  });
  configureSocCommandRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["admin:SOC-01"]),
    execute: executeSoc,
    audit: async () => undefined,
  });
  configureErpCommandRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["admin:ERP-01"]),
    execute: executeErp,
    audit: async () => undefined,
  });
  configureAiApiCommandRuntime({
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["admin:AIAPI-01"]),
    execute: executeProductionAiApiCommand,
    audit: auditProductionAiApiCommand,
  });
  configureSystemLifecycleRuntime({
    resolveContinuityContext: async (system_change_id) => ({
      system_change_id,
      system_truth: null,
      active_change: null,
      conversation: null,
      decisions: null,
      affected_scope: null,
      validation: null,
      deployment: null,
      latest_context_fingerprint: sha256(system_change_id),
    }),
    authorize: async () => authorizePage(CURRENT_PAGE_RESOURCE_KEYS["admin:SYS-01"]),
    execute: async () => {
      throw new NamedRuntimeError("PROVIDER_GATEWAY_NOT_MATERIALIZED");
    },
    audit: async () => undefined,
  });
}

export function isIdentityPageCommandRuntimeBound(): boolean {
  return bound;
}
