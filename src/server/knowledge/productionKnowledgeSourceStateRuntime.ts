import { randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import {
  hashSessionToken,
  IDENTITY_COOKIE_NAME,
  resolveIdentityFromCookie,
} from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { KnowledgeRuntimeRequest } from "@/domain/knowledge/knowledgeRuntimeContract";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

function record(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function positiveInt(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) && rows.length > 0 && rows[0] && typeof rows[0] === "object"
    ? rows[0] as Row
    : null;
}
function uuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}
function exactKeys(payload: Row): boolean {
  const actual = Object.keys(payload).sort();
  const expected = ["correlation_id","expected_version","idempotency_key","reason","source_id"];
  return actual.length === expected.length && expected.every((key, index) => actual[index] === key);
}

async function requireContext(): Promise<{
  sql: SqlClient;
  actor_user_id: string;
  session_token_hash: string;
}> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const store = await cookies();
  const token = store.get(IDENTITY_COOKIE_NAME)?.value?.trim() ?? "";
  if (!token) throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity = await resolveIdentityFromCookie(token);
  if (!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  return {
    sql,
    actor_user_id: identity.actor.user_id,
    session_token_hash: hashSessionToken(token),
  };
}


const CREATE_SOURCE_ALLOWED = new Set([
  "name","source_type","scope","rights","classification","collection_method",
  "freshness_policy","retention_policy","correlation_id","idempotency_key",
  "collection_config","secret_reference_id",
]);
const CREATE_SOURCE_REQUIRED = [
  "name","source_type","scope","rights","classification","collection_method",
  "freshness_policy","retention_policy","correlation_id","idempotency_key",
] as const;
const UPDATE_SOURCE_ALLOWED = new Set([
  "source_id","expected_version","correlation_id","idempotency_key",
  "name","source_type","scope","rights","classification","collection_method",
  "collection_config","freshness_policy","retention_policy",
]);
const UPDATE_SOURCE_REQUIRED = ["source_id","expected_version","correlation_id","idempotency_key"] as const;

function sourceSchema(payload: Row, allowed: Set<string>, required: readonly string[]): boolean {
  return Object.keys(payload).every((key) => allowed.has(key))
    && required.every((key) => Object.prototype.hasOwnProperty.call(payload,key));
}
function requiredText(value: unknown): string {
  const valueText=text(value);
  if(!valueText||valueText==="—") throw new NamedRuntimeError("KB01_REQUIRED_SOURCE_FIELD_MISSING");
  return valueText;
}
function jsonPolicy(value: unknown,key: string): string {
  if(value&&typeof value==="object"&&!Array.isArray(value)) return JSON.stringify(value);
  const valueText=text(value);
  if(!valueText) throw new NamedRuntimeError("KB01_REQUIRED_SOURCE_FIELD_MISSING");
  try{
    const parsed:unknown=JSON.parse(valueText);
    if(parsed&&typeof parsed==="object"&&!Array.isArray(parsed)) return JSON.stringify(parsed);
  }catch{}
  return JSON.stringify({[key]:valueText});
}
function optionalJson(value: unknown,key: string): string {
  if(value===undefined||value===null||value==="") return "{}";
  if(value&&typeof value==="object"&&!Array.isArray(value)) return JSON.stringify(value);
  const valueText=text(value);
  if(!valueText) return "{}";
  try{
    const parsed:unknown=JSON.parse(valueText);
    if(parsed&&typeof parsed==="object"&&!Array.isArray(parsed)) return JSON.stringify(parsed);
  }catch{}
  return JSON.stringify({[key]:valueText});
}
function classification(value: unknown): string {
  const candidate=requiredText(value).toUpperCase();
  if(!["PUBLIC","INTERNAL","RESTRICTED","RESTRICTED_FINANCE"].includes(candidate)){
    throw new NamedRuntimeError("KB01_CLASSIFICATION_INVALID");
  }
  return candidate;
}
function scopeUri(value: unknown): string {
  const direct=text(value);
  if(direct) return direct;
  const object=record(value);
  const candidate=text(object.source_uri)||text(object.uri)||text(object.ref);
  if(!candidate) throw new NamedRuntimeError("KB_SCOPE_INVALID");
  return candidate;
}
function sourceKey(name: string,id: string): string {
  const slug=name.toUpperCase().replace(/[^A-Z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,32)||"SOURCE";
  return `KS-${slug}-${id.slice(0,8).toUpperCase()}`;
}
function correlationAndIdempotency(payload: Row,request: KnowledgeRuntimeRequest): {idempotencyKey:string} {
  const bodyCorrelation=text(payload.correlation_id);
  if(!uuid(bodyCorrelation)||bodyCorrelation!==request.correlation_id) throw new NamedRuntimeError("KB01_CORRELATION_ID_MISMATCH");
  const idempotencyKey=text(payload.idempotency_key);
  if(!idempotencyKey||idempotencyKey.length>128) throw new NamedRuntimeError("KB01_IDEMPOTENCY_KEY_REQUIRED");
  return{idempotencyKey};
}

export async function mutateProductionKnowledgeSource(request: KnowledgeRuntimeRequest): Promise<unknown> {
  if(request.operation!=="createKnowledgeSource"&&request.operation!=="updateKnowledgeSource"){
    throw new NamedRuntimeError("KB_UNSUPPORTED_OPERATION");
  }
  const payload=record(request.payload);
  if(payload.raw_secret!==undefined||payload.credential_plaintext!==undefined||payload.status_direct_write!==undefined){
    throw new NamedRuntimeError("KB_RAW_SECRET_FORBIDDEN");
  }
  const isCreate=request.operation==="createKnowledgeSource";
  if(isCreate&&!sourceSchema(payload,CREATE_SOURCE_ALLOWED,CREATE_SOURCE_REQUIRED)){
    throw new NamedRuntimeError("KB01_SOURCE_CREATE_REQUEST_SCHEMA_INVALID");
  }
  if(!isCreate&&!sourceSchema(payload,UPDATE_SOURCE_ALLOWED,UPDATE_SOURCE_REQUIRED)){
    throw new NamedRuntimeError("KB01_SOURCE_UPDATE_REQUEST_SCHEMA_INVALID");
  }
  const {idempotencyKey}=correlationAndIdempotency(payload,request);
  const {sql,actor_user_id,session_token_hash}=await requireContext();

  if(isCreate){
    const name=requiredText(payload.name);
    const sourceType=requiredText(payload.source_type);
    const scopeJson=jsonPolicy(payload.scope,"ref");
    const sourceUri=scopeUri(payload.scope);
    const rightsJson=jsonPolicy(payload.rights,"rights");
    const sourceClassification=classification(payload.classification);
    const collectionMethod=requiredText(payload.collection_method);
    const collectionConfig=optionalJson(payload.collection_config,"config");
    const freshnessJson=jsonPolicy(payload.freshness_policy,"policy");
    const retentionJson=jsonPolicy(payload.retention_policy,"policy");
    const secretReference=text(payload.secret_reference_id)||null;
    if(secretReference&&!uuid(secretReference)) throw new NamedRuntimeError("KB01_SECRET_REFERENCE_INVALID");
    const generatedId=randomUUID();
    const generatedKey=sourceKey(name,generatedId);
    const fingerprintInput=JSON.stringify({
      operation:"createKnowledgeSource",name,source_type:sourceType,scope:JSON.parse(scopeJson),
      rights:JSON.parse(rightsJson),classification:sourceClassification,collection_method:collectionMethod,
      collection_config:JSON.parse(collectionConfig),freshness_policy:JSON.parse(freshnessJson),
      retention_policy:JSON.parse(retentionJson),secret_reference_id:secretReference,
    });
    const replayRows=await runRlsActorQuery(sql,session_token_hash,sql`
      SELECT entity_id::text AS source_id,action,after_version,
             after_version->>'request_fingerprint' AS request_fingerprint,
             encode(digest(${fingerprintInput}::text,'sha256'),'hex') AS expected_fingerprint
      FROM public.audit_events
      WHERE payload_hash=encode(digest(${idempotencyKey}::text,'sha256'),'hex')
        AND entity_type='admin:KB-01'
      ORDER BY occurred_at DESC LIMIT 1
    `);
    const replay=first(replayRows);
    if(replay){
      const after=record(replay.after_version);
      if(text(replay.action)!=="knowledge.source.created"||text(replay.request_fingerprint)!==text(replay.expected_fingerprint)){
        throw new NamedRuntimeError("KB01_IDEMPOTENCY_CONFLICT");
      }
      return{
        source_id:text(replay.source_id),source_key:text(after.source_key),status:text(after.status)||"DRAFT",
        source_version:Number(after.source_version)||1,idempotent_replay:true,external_request_sent:false,
      };
    }
    const rows=await runRlsActorQuery(sql,session_token_hash,sql`
      WITH inserted AS(
        INSERT INTO public.knowledge_sources(
          knowledge_source_id,source_key,source_uri,name,source_type,scope,collection_method,collection_config,
          rights_policy,classification,freshness_policy,retention_policy,secret_reference_id,status,source_version,updated_at
        ) VALUES(
          ${generatedId}::uuid,${generatedKey},${sourceUri},${name},${sourceType},${scopeJson}::jsonb,${collectionMethod},${collectionConfig}::jsonb,
          ${rightsJson}::jsonb,${sourceClassification}::classification_level,${freshnessJson}::jsonb,${retentionJson}::jsonb,
          ${secretReference}::uuid,'DRAFT',1,now()
        )
        RETURNING knowledge_source_id::text AS source_id,source_key,status,source_version
      ),audited AS(
        INSERT INTO public.audit_events(
          action,entity_type,entity_id,actor_id,actor_type,before_version,after_version,reason,correlation_id,payload_hash
        )
        SELECT 'knowledge.source.created','admin:KB-01',i.source_id::uuid,${actor_user_id}::uuid,'USER',NULL,
          jsonb_build_object(
            'status',i.status,'source_version',i.source_version,'source_key',i.source_key,
            'request_fingerprint',encode(digest(${fingerprintInput}::text,'sha256'),'hex')
          ),
          'SOURCE_CREATE',${request.correlation_id}::uuid,encode(digest(${idempotencyKey}::text,'sha256'),'hex')
        FROM inserted i RETURNING audit_event_id::text AS audit_event_id
      )
      SELECT i.source_id,i.source_key,i.status,i.source_version,a.audit_event_id
      FROM inserted i CROSS JOIN audited a
    `);
    const created=first(rows);
    if(!created) throw new NamedRuntimeError("KNOWLEDGE_SOURCE_INSERT_FAILED");
    return{
      source_id:text(created.source_id),source_key:text(created.source_key),status:text(created.status)||"DRAFT",
      source_version:Number(created.source_version)||1,audit_event_id:text(created.audit_event_id),
      idempotent_replay:false,external_request_sent:false,
    };
  }

  const sourceId=text(payload.source_id);
  const pathSourceId=text(request.path_params?.sourceId);
  if(!uuid(sourceId)||sourceId!==pathSourceId) throw new NamedRuntimeError("KB01_SOURCE_ID_MISMATCH");
  const expectedVersion=positiveInt(payload.expected_version);
  if(!expectedVersion) throw new NamedRuntimeError("KB01_EXPECTED_VERSION_MISSING");
  const fingerprintInput=JSON.stringify({
    operation:"updateKnowledgeSource",source_id:sourceId,expected_version:expectedVersion,
    name:payload.name??null,source_type:payload.source_type??null,scope:payload.scope??null,rights:payload.rights??null,
    classification:payload.classification??null,collection_method:payload.collection_method??null,
    collection_config:payload.collection_config??null,freshness_policy:payload.freshness_policy??null,
    retention_policy:payload.retention_policy??null,
  });
  const replayRows=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT entity_id::text AS source_id,action,after_version,
           after_version->>'request_fingerprint' AS request_fingerprint,
           encode(digest(${fingerprintInput}::text,'sha256'),'hex') AS expected_fingerprint
    FROM public.audit_events
    WHERE payload_hash=encode(digest(${idempotencyKey}::text,'sha256'),'hex')
      AND entity_type='admin:KB-01'
    ORDER BY occurred_at DESC LIMIT 1
  `);
  const replay=first(replayRows);
  if(replay){
    const after=record(replay.after_version);
    if(text(replay.source_id)!==sourceId||text(replay.action)!=="knowledge.source.updated"||text(replay.request_fingerprint)!==text(replay.expected_fingerprint)){
      throw new NamedRuntimeError("KB01_IDEMPOTENCY_CONFLICT");
    }
    return{
      source_id:sourceId,source_key:text(after.source_key),status:text(after.status)||"ACTIVE",
      source_version:Number(after.source_version)||expectedVersion+1,idempotent_replay:true,external_request_sent:false,
    };
  }

  const currentRows=await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT knowledge_source_id::text AS source_id,source_key,source_uri,name,source_type,scope,collection_method,collection_config,
           rights_policy,classification::text AS classification,freshness_policy,retention_policy,status,source_version,secret_reference_id::text AS secret_reference_id
    FROM public.knowledge_sources WHERE knowledge_source_id=${sourceId}::uuid LIMIT 1
  `);
  const current=first(currentRows);
  if(!current) throw new NamedRuntimeError("KB01_SOURCE_NOT_FOUND");
  if(Number(current.source_version)!==expectedVersion) throw new NamedRuntimeError("KB01_SOURCE_VERSION_CONFLICT");
  if(text(current.status)!=="DRAFT") throw new NamedRuntimeError("KB01_SOURCE_STATE_GUARD_REJECTED");

  const name=payload.name!==undefined?requiredText(payload.name):requiredText(current.name);
  const sourceType=payload.source_type!==undefined?requiredText(payload.source_type):requiredText(current.source_type);
  const scopeSource=payload.scope!==undefined?payload.scope:current.scope;
  const scopeJson=jsonPolicy(scopeSource,"ref");
  const sourceUri=scopeUri(scopeSource);
  const rightsJson=jsonPolicy(payload.rights!==undefined?payload.rights:current.rights_policy,"rights");
  const sourceClassification=classification(payload.classification!==undefined?payload.classification:current.classification);
  const collectionMethod=payload.collection_method!==undefined?requiredText(payload.collection_method):requiredText(current.collection_method);
  const collectionConfig=optionalJson(payload.collection_config!==undefined?payload.collection_config:current.collection_config,"config");
  const freshnessJson=jsonPolicy(payload.freshness_policy!==undefined?payload.freshness_policy:current.freshness_policy,"policy");
  const retentionJson=jsonPolicy(payload.retention_policy!==undefined?payload.retention_policy:current.retention_policy,"policy");
  const stableKey=requiredText(current.source_key);
  const secretReference=text(current.secret_reference_id)||null;

  const rows=await runRlsActorQuery(sql,session_token_hash,sql`
    WITH updated AS(
      UPDATE public.knowledge_sources
      SET name=${name},source_type=${sourceType},scope=${scopeJson}::jsonb,source_uri=${sourceUri},
          collection_method=${collectionMethod},collection_config=${collectionConfig}::jsonb,
          rights_policy=${rightsJson}::jsonb,classification=${sourceClassification}::classification_level,
          freshness_policy=${freshnessJson}::jsonb,retention_policy=${retentionJson}::jsonb,
          status='ACTIVE',source_version=source_version+1,updated_at=now()
      WHERE knowledge_source_id=${sourceId}::uuid AND source_version=${expectedVersion} AND status='DRAFT'
      RETURNING knowledge_source_id::text AS source_id,source_key,status,source_version
    ),audited AS(
      INSERT INTO public.audit_events(
        action,entity_type,entity_id,actor_id,actor_type,before_version,after_version,reason,correlation_id,payload_hash
      )
      SELECT 'knowledge.source.updated','admin:KB-01',u.source_id::uuid,${actor_user_id}::uuid,'USER',
        jsonb_build_object('status','DRAFT','source_version',${expectedVersion},'source_key',${stableKey}),
        jsonb_build_object(
          'status',u.status,'source_version',u.source_version,'source_key',u.source_key,
          'request_fingerprint',encode(digest(${fingerprintInput}::text,'sha256'),'hex')
        ),
        'SOURCE_SAVE',${request.correlation_id}::uuid,encode(digest(${idempotencyKey}::text,'sha256'),'hex')
      FROM updated u RETURNING audit_event_id::text AS audit_event_id
    )
    SELECT u.source_id,u.source_key,u.status,u.source_version,a.audit_event_id
    FROM updated u CROSS JOIN audited a
  `);
  const changed=first(rows);
  if(!changed) throw new NamedRuntimeError("KB01_SOURCE_STATE_GUARD_REJECTED");
  return{
    source_id:sourceId,source_key:text(changed.source_key),status:text(changed.status)||"ACTIVE",
    source_version:Number(changed.source_version)||expectedVersion+1,audit_event_id:text(changed.audit_event_id),
    secret_reference_id:secretReference,idempotent_replay:false,external_request_sent:false,
  };
}

export async function transitionProductionKnowledgeSource(request: KnowledgeRuntimeRequest): Promise<unknown> {
  if (request.operation !== "pauseKnowledgeSource" && request.operation !== "resumeKnowledgeSource") {
    throw new NamedRuntimeError("KB_UNSUPPORTED_OPERATION");
  }

  const payload = record(request.payload);
  if (!exactKeys(payload)) throw new NamedRuntimeError("KB01_SOURCE_STATE_REQUEST_SCHEMA_INVALID");

  const sourceId = text(payload.source_id);
  const pathSourceId = text(request.path_params?.sourceId);
  if (!uuid(sourceId) || sourceId !== pathSourceId) throw new NamedRuntimeError("KB01_SOURCE_ID_MISMATCH");

  const expectedVersion = positiveInt(payload.expected_version);
  if (!expectedVersion) throw new NamedRuntimeError("KB01_EXPECTED_VERSION_MISSING");

  const reason = text(payload.reason);
  if (!reason) throw new NamedRuntimeError("KB01_SOURCE_STATE_REASON_REQUIRED");

  const bodyCorrelation = text(payload.correlation_id);
  if (!uuid(bodyCorrelation) || bodyCorrelation !== request.correlation_id) {
    throw new NamedRuntimeError("KB01_CORRELATION_ID_MISMATCH");
  }

  const idempotencyKey = text(payload.idempotency_key);
  if (!idempotencyKey || idempotencyKey.length > 128) {
    throw new NamedRuntimeError("KB01_IDEMPOTENCY_KEY_REQUIRED");
  }

  const expectedState = request.operation === "pauseKnowledgeSource" ? "ACTIVE" : "PAUSED";
  const targetState = request.operation === "pauseKnowledgeSource" ? "PAUSED" : "ACTIVE";
  const auditAction = request.operation === "pauseKnowledgeSource"
    ? "knowledge.source.paused"
    : "knowledge.source.resumed";

  const { sql, actor_user_id, session_token_hash } = await requireContext();

  const replayRows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      SELECT
        entity_id::text AS source_id,
        action,
        reason,
        before_version,
        after_version
      FROM public.audit_events
      WHERE payload_hash=encode(digest(${idempotencyKey}::text,'sha256'),'hex')
        AND entity_type='admin:KB-01'
      ORDER BY occurred_at DESC
      LIMIT 1
    `,
  );
  const replay = first(replayRows);
  if (replay) {
    const beforeVersion = record(replay.before_version);
    const afterVersion = record(replay.after_version);
    if (
      text(replay.source_id) !== sourceId
      || text(replay.action) !== auditAction
      || text(replay.reason) !== reason
      || Number(beforeVersion.source_version) !== expectedVersion
    ) {
      throw new NamedRuntimeError("KB01_IDEMPOTENCY_CONFLICT");
    }
    return {
      source_id: sourceId,
      state: text(afterVersion.status) || targetState,
      source_version: Number(afterVersion.source_version) || expectedVersion + 1,
      idempotent_replay: true,
      external_request_sent: false,
    };
  }

  const rows = await runRlsActorQuery(
    sql,
    session_token_hash,
    sql`
      WITH updated AS (
        UPDATE public.knowledge_sources
        SET status=${targetState},
            source_version=source_version+1,
            updated_at=now()
        WHERE knowledge_source_id=${sourceId}::uuid
          AND status=${expectedState}
          AND source_version=${expectedVersion}
        RETURNING knowledge_source_id::text AS source_id,status,source_version
      ),
      audited AS (
        INSERT INTO public.audit_events(
          action,
          entity_type,
          entity_id,
          actor_id,
          actor_type,
          before_version,
          after_version,
          reason,
          correlation_id,
          payload_hash
        )
        SELECT
          ${auditAction},
          'admin:KB-01',
          u.source_id::uuid,
          ${actor_user_id}::uuid,
          'USER',
          jsonb_build_object('status',${expectedState},'source_version',${expectedVersion}),
          jsonb_build_object('status',u.status,'source_version',u.source_version),
          ${reason},
          ${request.correlation_id}::uuid,
          encode(digest(${idempotencyKey}::text,'sha256'),'hex')
        FROM updated u
        RETURNING audit_event_id::text AS audit_event_id
      )
      SELECT u.source_id,u.status,u.source_version,a.audit_event_id
      FROM updated u
      CROSS JOIN audited a
    `,
  );

  const changed = first(rows);
  if (!changed) {
    const currentRows = await runRlsActorQuery(
      sql,
      session_token_hash,
      sql`
        SELECT knowledge_source_id::text AS source_id,status,source_version
        FROM public.knowledge_sources
        WHERE knowledge_source_id=${sourceId}::uuid
        LIMIT 1
      `,
    );
    const current = first(currentRows);
    if (!current) throw new NamedRuntimeError("KB01_SOURCE_NOT_FOUND");
    if (Number(current.source_version) !== expectedVersion) throw new NamedRuntimeError("KB01_SOURCE_VERSION_CONFLICT");
    throw new NamedRuntimeError("KB01_SOURCE_STATE_GUARD_REJECTED");
  }

  return {
    source_id: text(changed.source_id),
    state: text(changed.status),
    source_version: Number(changed.source_version),
    audit_event_id: text(changed.audit_event_id),
    idempotent_replay: false,
    external_request_sent: false,
  };
}
