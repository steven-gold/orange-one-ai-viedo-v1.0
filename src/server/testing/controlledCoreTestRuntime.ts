import type { CoreRuntimeBindings } from "@/server/core/coreRuntime";
import type { CoreRuntimeRequest } from "@/domain/core/coreRuntimeContract";

type TestProject = {
  project_id: string;
  project_version_ref: string;
  label: string;
  state: "DRAFT" | "VALIDATED" | "CORE_MODELING";
};

type TestTopic = {
  topic_id: string;
  topic_version_ref: string;
  project_id: string;
  label: string;
};

type TestThread = {
  conversation_id: string;
  project_id: string;
  topic_id: string | null;
  work_item: string;
  label: string;
  parent_conversation_id?: string;
  source_message_id?: string;
};

type TestMessage = {
  message_ref: string;
  conversation_id: string;
  message: string;
  instruction_kind: "MESSAGE" | "ANALYZE";
  source_message_id?: string;
};

type TestCandidate = {
  candidate_ref: string;
  human_decision: string;
  state: "CANDIDATE" | "ACCEPTED" | "RETURNED";
};

type TestBlueprint = {
  blueprint_version_ref: string;
  topic_id: string;
  state: "BLUEPRINT_DRAFT" | "BLUEPRINT_REVIEW" | "READY_FOR_CHILD_REVIEW";
};

type TestState = {
  projects: TestProject[];
  topics: TestTopic[];
  threads: TestThread[];
  messages: TestMessage[];
  candidates: TestCandidate[];
  blueprints: TestBlueprint[];
  project_id: string | null;
  project_version_ref: string | null;
  topic_id: string | null;
  topic_version_ref: string | null;
  dna_version_ref: string | null;
  blueprint_version_ref: string | null;
  conversation_id: string | null;
  candidate_ref: string | null;
  work_item: string | null;
  story_candidate_set_ref: string | null;
  canonical_script_ref: string | null;
  assistant_summary: string | null;
  evaluation: string | null;
  structured_decision: string | null;
  core_review_state: string | null;
  dna_lock_state: string | null;
  mother_lock_state: string | null;
  child_lock_state: string | null;
  comparison_state: string | null;
  audit: Array<Record<string, unknown>>;
};

const state: TestState = {
  projects: [],
  topics: [],
  threads: [],
  messages: [],
  candidates: [],
  blueprints: [],
  project_id: null,
  project_version_ref: null,
  topic_id: null,
  topic_version_ref: null,
  dna_version_ref: null,
  blueprint_version_ref: null,
  conversation_id: null,
  candidate_ref: null,
  work_item: null,
  story_candidate_set_ref: null,
  canonical_script_ref: null,
  assistant_summary: null,
  evaluation: null,
  structured_decision: null,
  core_review_state: null,
  dna_lock_state: null,
  mother_lock_state: null,
  child_lock_state: null,
  comparison_state: null,
  audit: [],
};

function token(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function list(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && Boolean(item.trim())).map((item) => item.trim()) : [];
}

function currentProject(): TestProject | null {
  return state.projects.find((item) => item.project_id === state.project_id) ?? null;
}

function currentBlueprint(): TestBlueprint | null {
  return state.blueprints.find((item) => item.blueprint_version_ref === state.blueprint_version_ref) ?? null;
}

function currentCandidate(): TestCandidate | null {
  return state.candidates.find((item) => item.candidate_ref === state.candidate_ref) ?? null;
}

function runtimeStage(): string {
  if (state.candidate_ref) return "CORE-01-STAGE-05-CANDIDATE";
  if (state.assistant_summary && state.evaluation) return "CORE-01-STAGE-04-HUMAN-DECIDE";
  if (state.conversation_id) return "CORE-01-STAGE-02-CONVERSE";
  return "CORE-01-STAGE-01-CONTEXT";
}

function lockReviewDisplay(): string {
  const values = [state.dna_lock_state, state.core_review_state, state.mother_lock_state, state.child_lock_state].filter(Boolean);
  return values.length ? `[TEST] ${values.join(" | ")}` : "—";
}

function projection() {
  const topicMode = Boolean(state.topic_id);
  const project = currentProject();
  const blueprint = currentBlueprint();
  const candidate = currentCandidate();
  const packageState = state.canonical_script_ref
    ? `[TEST] Canonical Script Bound: ${state.canonical_script_ref}`
    : state.topic_id ? "[TEST] Topic package awaiting Canonical Script" : "—";
  const downstream = state.child_lock_state === "CHILD_LOCK_REVIEW_REQUESTED" && state.mother_lock_state === "MOTHER_LOCK_REVIEW_REQUESTED"
    ? "[TEST] REVIEW_PENDING — NOT PRODUCTION READY"
    : "BLOCKED — exact lock review not complete";

  return {
    refs: {
      project_id: state.project_id,
      project_version_ref: state.project_version_ref,
      topic_id: state.topic_id,
      topic_version_ref: state.topic_version_ref,
      dna_version_ref: state.dna_version_ref,
      blueprint_version_ref: state.blueprint_version_ref,
      conversation_id: state.conversation_id,
      candidate_ref: state.candidate_ref,
    },
    work_item: state.work_item,
    projects: state.projects.map((item) => ({
      project_id: item.project_id,
      project_version_ref: item.project_version_ref,
      label: item.label,
    })),
    topics: state.topics
      .filter((item) => !state.project_id || item.project_id === state.project_id)
      .map((item) => ({ topic_id: item.topic_id, topic_version_ref: item.topic_version_ref, label: item.label })),
    work_items: (topicMode
      ? ["TOPIC_SCOPE", "PRODUCTION_SCRIPT"]
      : ["STORY", "CHAPTER", "WORLD_SETTING", "DNA", "BLUEPRINT"])
      .map((work_item) => ({ work_item, label: work_item })),
    threads: state.threads
      .filter((thread) => !state.project_id || thread.project_id === state.project_id)
      .filter((thread) => !state.topic_id || thread.topic_id === state.topic_id)
      .filter((thread) => !state.work_item || thread.work_item === state.work_item)
      .map((thread) => ({ conversation_id: thread.conversation_id, label: thread.label })),
    display_values: {
      test_mode: "TEST_ONLY",
      test_data_classification: "TEST_ONLY",
      runtime_state: "CONTROLLED_TEST_RUNTIME",
      page_mode: topicMode ? "TOPIC_PRODUCTION" : "PROJECT_CORE",
      assigned_ai_set: "[TEST] ACPOS_SHARED_ROUTER / TEST_ASSIGNED_AI_SET",
      project_state: project ? `[TEST] ${project.state}` : "—",
      story_candidate_set: state.story_candidate_set_ref ? `[TEST] ${state.story_candidate_set_ref}` : "—",
      dna_state: state.dna_version_ref ? `[TEST] ${state.dna_version_ref}${state.dna_lock_state ? ` / ${state.dna_lock_state}` : ""}` : "—",
      blueprint_state: blueprint ? `[TEST] ${blueprint.state} / ${blueprint.blueprint_version_ref}` : "—",
      assistant_summary: state.assistant_summary ?? "—",
      evaluation: state.evaluation ?? "—",
      structured_decision: state.structured_decision ?? "—",
      runtime_stage: runtimeStage(),
      topic_scope: state.topic_id ? `[TEST] TOPIC_SCOPE / ${state.topic_id}` : "—",
      canonical_script: state.canonical_script_ref ? `[TEST] ${state.canonical_script_ref}` : "—",
      package: packageState,
      downstream_asset: downstream,
      downstream_video: downstream,
      downstream_edit: downstream,
      version_state: candidate ? `[TEST] ${candidate.state} / ${candidate.candidate_ref}` : state.project_version_ref ? `[TEST] ${state.project_version_ref}` : "—",
      candidate_compare: state.comparison_state ?? "—",
      lock_review: lockReviewDisplay(),
      audit_count: String(state.audit.length),
    },
  };
}

function requireTestPayload(request: CoreRuntimeRequest): Record<string, unknown> {
  const payload = asRecord(request.payload);
  if (payload.data_classification !== "TEST_ONLY" || payload.synthetic !== true || payload.production_eligible !== false) {
    throw new Error("CONTROLLED_TEST_METADATA_REQUIRED");
  }
  return payload;
}

function requireProjectByVersion(ref: string | undefined): TestProject {
  const project = state.projects.find((item) => item.project_version_ref === ref);
  if (!project) throw new Error("TEST_PROJECT_VERSION_NOT_FOUND");
  return project;
}

function requireCurrentThread(conversation_id: string | undefined): TestThread {
  const thread = state.threads.find((item) => item.conversation_id === conversation_id);
  if (!thread) throw new Error("TEST_CONVERSATION_NOT_FOUND");
  return thread;
}

async function execute(request: CoreRuntimeRequest): Promise<unknown> {
  switch (request.port_uid) {
    case "CORE-01-PORT-PROJECTION":
      return projection();

    case "CORE-01-PORT-PROJECT-CREATE": {
      const payload = requireTestPayload(request);
      const project_id = token("TEST-PROJ");
      const project_version_ref = `${project_id}-V1`;
      const label = text(payload.fixture_label) ?? `[TEST] Project ${project_id.slice(-8)}`;
      state.projects.push({ project_id, project_version_ref, label, state: "DRAFT" });
      state.project_id = project_id;
      state.project_version_ref = project_version_ref;
      state.topic_id = null;
      state.topic_version_ref = null;
      state.dna_version_ref = null;
      state.blueprint_version_ref = null;
      state.conversation_id = null;
      state.candidate_ref = null;
      state.work_item = "STORY";
      state.story_candidate_set_ref = null;
      state.canonical_script_ref = null;
      state.assistant_summary = null;
      state.evaluation = null;
      state.structured_decision = null;
      state.core_review_state = null;
      state.dna_lock_state = null;
      state.mother_lock_state = null;
      state.child_lock_state = null;
      state.comparison_state = null;
      return { data_classification: "TEST_ONLY", project_id, project_version_ref, state: "DRAFT" };
    }

    case "CORE-01-PORT-PROJECT-VALIDATE": {
      const project = requireProjectByVersion(request.path_params?.projectVersionId);
      if (project.state !== "DRAFT") throw new Error("TEST_PROJECT_NOT_IN_DRAFT");
      project.state = "VALIDATED";
      return { data_classification: "TEST_ONLY", project_version_ref: project.project_version_ref, state: project.state };
    }

    case "CORE-01-PORT-PROJECT-CONFIRM": {
      const project = requireProjectByVersion(request.path_params?.id);
      if (project.state !== "VALIDATED") throw new Error("TEST_PROJECT_NOT_VALIDATED");
      project.state = "CORE_MODELING";
      state.project_id = project.project_id;
      state.project_version_ref = project.project_version_ref;
      state.dna_version_ref ??= `${project.project_id}-TEST-DNA-V1`;
      return {
        data_classification: "TEST_ONLY",
        project_id: project.project_id,
        project_version_ref: project.project_version_ref,
        dna_version_ref: state.dna_version_ref,
        state: project.state,
      };
    }

    case "CORE-01-PORT-STORY-CANDIDATE": {
      if (!state.project_id || request.path_params?.projectId !== state.project_id) throw new Error("TEST_PROJECT_CONTEXT_MISMATCH");
      const project = currentProject();
      if (!project || project.state !== "CORE_MODELING") throw new Error("TEST_PROJECT_CORE_NOT_CONFIRMED");
      state.story_candidate_set_ref = token("TEST-STORY-SET");
      return { data_classification: "TEST_ONLY", story_candidate_set_ref: state.story_candidate_set_ref, project_id: state.project_id };
    }

    case "CORE-01-PORT-TOPIC-CREATE": {
      const payload = requireTestPayload(request);
      const project_id = request.path_params?.projectId;
      const project = state.projects.find((item) => item.project_id === project_id);
      if (!project) throw new Error("TEST_PROJECT_NOT_FOUND");
      if (project.state !== "CORE_MODELING") throw new Error("TEST_PROJECT_SOURCE_NOT_CONFIRMED");
      const topic_id = token("TEST-TOPIC");
      const topic_version_ref = `${topic_id}-V1`;
      const label = text(payload.fixture_label) ?? `[TEST] Topic ${topic_id.slice(-8)}`;
      state.topics.push({ topic_id, topic_version_ref, project_id: project.project_id, label });
      state.project_id = project.project_id;
      state.project_version_ref = project.project_version_ref;
      state.topic_id = topic_id;
      state.topic_version_ref = topic_version_ref;
      state.blueprint_version_ref = null;
      state.conversation_id = null;
      state.candidate_ref = null;
      state.work_item = "TOPIC_SCOPE";
      state.canonical_script_ref = null;
      state.child_lock_state = null;
      return { data_classification: "TEST_ONLY", topic_id, topic_version_ref, project_id: project.project_id };
    }

    case "CORE-01-PORT-THREAD-CREATE": {
      const payload = requireTestPayload(request);
      const project_id = request.path_params?.projectId;
      if (!project_id || project_id !== state.project_id) throw new Error("TEST_PROJECT_CONTEXT_MISMATCH");
      const workItem = text(payload.work_item) ?? state.work_item;
      if (!workItem) throw new Error("TEST_WORK_ITEM_REQUIRED");
      const allowedWorkItems = state.topic_id ? ["TOPIC_SCOPE", "PRODUCTION_SCRIPT"] : ["STORY", "CHAPTER", "WORLD_SETTING", "DNA", "BLUEPRINT"];
      if (!allowedWorkItems.includes(workItem)) throw new Error("TEST_WORK_ITEM_MODE_MISMATCH");
      const parent_conversation_id = text(payload.parent_conversation_id) ?? undefined;
      const source_message_id = text(payload.source_message_id) ?? undefined;
      if (payload.relation_kind === "BRANCH") {
        if (!parent_conversation_id || !state.threads.some((item) => item.conversation_id === parent_conversation_id)) throw new Error("TEST_PARENT_THREAD_NOT_FOUND");
        if (!source_message_id || !state.messages.some((item) => item.message_ref === source_message_id && item.conversation_id === parent_conversation_id)) throw new Error("TEST_BRANCH_SOURCE_MESSAGE_NOT_FOUND");
      }
      const conversation_id = token("TEST-CONV");
      const thread: TestThread = {
        conversation_id,
        project_id,
        topic_id: state.topic_id,
        work_item: workItem,
        label: payload.relation_kind === "BRANCH" ? `[TEST] Branch ${workItem}` : `[TEST] ${workItem} Thread`,
        parent_conversation_id,
        source_message_id,
      };
      state.threads.push(thread);
      state.conversation_id = conversation_id;
      state.work_item = workItem;
      return { data_classification: "TEST_ONLY", conversation_id, project_id, work_item: workItem, relation_kind: payload.relation_kind ?? "ROOT" };
    }

    case "CORE-01-PORT-MESSAGE-SEND": {
      const payload = requireTestPayload(request);
      const conversation_id = request.path_params?.conversationId;
      requireCurrentThread(conversation_id);
      const message = text(payload.message);
      if (!message) throw new Error("TEST_MESSAGE_REQUIRED");
      const source_message_id = text(payload.source_message_id) ?? undefined;
      if (source_message_id && !state.messages.some((item) => item.message_ref === source_message_id && item.conversation_id === conversation_id)) {
        throw new Error("TEST_SOURCE_MESSAGE_NOT_FOUND");
      }
      const instruction_kind = payload.instruction_kind === "ANALYZE" ? "ANALYZE" : "MESSAGE";
      const message_ref = token("TEST-MSG");
      state.messages.push({ message_ref, conversation_id: conversation_id!, message, instruction_kind, source_message_id });
      state.assistant_summary = `[TEST][SIMULATED_EXTERNAL] Summary for ${message_ref}`;
      state.evaluation = `[TEST] CORE evaluation fixture / evidence=${list(payload.reference_refs).length + list(payload.attachment_refs).length}`;
      const simulated_response_ref = token("TEST-AI-MSG");
      const simulated_response_text = instruction_kind === "ANALYZE"
        ? `[TEST][SIMULATED_EXTERNAL] Analysis response for ${source_message_id}`
        : `[TEST][SIMULATED_EXTERNAL] Response for ${message_ref}`;
      state.messages.push({ message_ref: simulated_response_ref, conversation_id: conversation_id!, message: simulated_response_text, instruction_kind: "MESSAGE" });
      return {
        data_classification: "TEST_ONLY",
        conversation_id,
        message_ref,
        accepted: true,
        simulated_ai_execution: true,
        simulation_classification: "SIMULATED_EXTERNAL",
        simulated_response_ref,
        simulated_response_text,
        mention_tokens: list(payload.mention_tokens),
      };
    }

    case "CORE-01-PORT-CANDIDATE-CREATE": {
      const payload = requireTestPayload(request);
      const human_decision = text(payload.human_decision);
      if (!human_decision) throw new Error("TEST_HUMAN_DECISION_REQUIRED");
      if (!state.assistant_summary || !state.evaluation) throw new Error("TEST_SUMMARY_EVALUATION_NOT_READY");
      const candidate_ref = token("TEST-CANDIDATE");
      const candidate: TestCandidate = { candidate_ref, human_decision, state: "CANDIDATE" };
      state.candidates.push(candidate);
      state.candidate_ref = candidate_ref;
      state.structured_decision = `[TEST] Structured human decision: ${human_decision}`;
      state.comparison_state = null;
      return { data_classification: "TEST_ONLY", candidate_ref, state: candidate.state, structured_decision: state.structured_decision };
    }

    case "CORE-01-PORT-CANDIDATE-COMPARE": {
      const exactRefs = (request.query?.candidate_refs ?? "").split(",").map((item) => item.trim()).filter(Boolean);
      if (!exactRefs.length) throw new Error("TEST_EXACT_CANDIDATE_SET_REQUIRED");
      const candidates = exactRefs.map((ref) => state.candidates.find((item) => item.candidate_ref === ref)).filter((item): item is TestCandidate => Boolean(item));
      if (candidates.length !== exactRefs.length) throw new Error("TEST_CANDIDATE_SET_MISMATCH");
      state.comparison_state = `[TEST] Compared ${candidates.length} exact candidate(s): ${candidates.map((item) => `${item.candidate_ref}:${item.state}`).join(" | ")}`;
      return { data_classification: "TEST_ONLY", exact_candidate_refs: exactRefs, comparison: candidates.map((item) => ({ candidate_ref: item.candidate_ref, state: item.state })) };
    }

    case "CORE-01-PORT-CANDIDATE-DECIDE": {
      const payload = requireTestPayload(request);
      const candidate_ref = request.path_params?.id;
      const candidate = state.candidates.find((item) => item.candidate_ref === candidate_ref);
      if (!candidate) throw new Error("TEST_CANDIDATE_NOT_FOUND");
      const decision = text(payload.decision);
      if (decision !== "ACCEPT" && decision !== "RETURN") throw new Error("TEST_CANDIDATE_DECISION_INVALID");
      candidate.state = decision === "ACCEPT" ? "ACCEPTED" : "RETURNED";
      state.candidate_ref = candidate.candidate_ref;
      return { data_classification: "TEST_ONLY", candidate_ref, decision, state: candidate.state };
    }

    case "CORE-01-PORT-DNA-LOCK": {
      requireTestPayload(request);
      if (!state.dna_version_ref) throw new Error("TEST_DNA_VERSION_NOT_FOUND");
      state.dna_lock_state = "DNA_LOCK_REVIEW_REQUESTED";
      return { data_classification: "TEST_ONLY", dna_version_ref: state.dna_version_ref, lock_state: "REVIEW_REQUESTED", final_lock_granted: false };
    }

    case "CORE-01-PORT-CORE-REVIEW": {
      requireTestPayload(request);
      if (!state.project_version_ref) throw new Error("TEST_PROJECT_VERSION_NOT_FOUND");
      if (!state.story_candidate_set_ref) throw new Error("TEST_PROJECT_CORE_CANDIDATE_REFS_INCOMPLETE");
      state.core_review_state = "CORE_REVIEW_REQUESTED";
      return { data_classification: "TEST_ONLY", project_version_ref: state.project_version_ref, request_ref: token("TEST-CORE-REVIEW"), final_approval_granted: false };
    }

    case "CORE-01-PORT-MOTHER-LOCK": {
      requireTestPayload(request);
      if (!state.project_version_ref) throw new Error("TEST_PROJECT_VERSION_NOT_FOUND");
      if (state.core_review_state !== "CORE_REVIEW_REQUESTED") throw new Error("TEST_CORE_REVIEW_REQUIRED_BEFORE_MOTHER_LOCK");
      state.mother_lock_state = "MOTHER_LOCK_REVIEW_REQUESTED";
      return { data_classification: "TEST_ONLY", project_version_ref: state.project_version_ref, request_ref: token("TEST-MOTHER-LOCK"), final_lock_granted: false };
    }

    case "CORE-01-PORT-BLUEPRINT-CREATE": {
      const topic_id = request.path_params?.id;
      if (!topic_id || topic_id !== state.topic_id) throw new Error("TEST_TOPIC_CONTEXT_MISMATCH");
      const blueprint_version_ref = token("TEST-BLUEPRINT-V1");
      state.blueprints.push({ blueprint_version_ref, topic_id, state: "BLUEPRINT_DRAFT" });
      state.blueprint_version_ref = blueprint_version_ref;
      state.child_lock_state = null;
      return { data_classification: "TEST_ONLY", topic_id, blueprint_version_ref, state: "BLUEPRINT_DRAFT" };
    }

    case "CORE-01-PORT-BLUEPRINT-VALIDATE": {
      const ref = request.path_params?.id;
      const blueprint = state.blueprints.find((item) => item.blueprint_version_ref === ref);
      if (!blueprint) throw new Error("TEST_BLUEPRINT_VERSION_NOT_FOUND");
      if (blueprint.state !== "BLUEPRINT_DRAFT") throw new Error("TEST_BLUEPRINT_NOT_DRAFT");
      blueprint.state = "BLUEPRINT_REVIEW";
      return { data_classification: "TEST_ONLY", blueprint_version_ref: ref, state: blueprint.state };
    }

    case "CORE-01-PORT-BLUEPRINT-APPROVE": {
      const ref = request.path_params?.id;
      const blueprint = state.blueprints.find((item) => item.blueprint_version_ref === ref);
      if (!blueprint) throw new Error("TEST_BLUEPRINT_VERSION_NOT_FOUND");
      if (blueprint.state !== "BLUEPRINT_REVIEW") throw new Error("TEST_BLUEPRINT_NOT_IN_REVIEW");
      blueprint.state = "READY_FOR_CHILD_REVIEW";
      return { data_classification: "TEST_ONLY", blueprint_version_ref: ref, state: blueprint.state };
    }

    case "CORE-01-PORT-CHILD-LOCK": {
      requireTestPayload(request);
      const blueprint = currentBlueprint();
      if (!blueprint) throw new Error("TEST_BLUEPRINT_VERSION_NOT_FOUND");
      if (blueprint.state !== "READY_FOR_CHILD_REVIEW") throw new Error("TEST_BLUEPRINT_NOT_READY_FOR_CHILD_REVIEW");
      state.child_lock_state = "CHILD_LOCK_REVIEW_REQUESTED";
      return { data_classification: "TEST_ONLY", blueprint_version_ref: blueprint.blueprint_version_ref, lock_state: "REVIEW_REQUESTED", final_lock_granted: false };
    }

    case "CORE-01-PORT-CANONICAL-SCRIPT": {
      const topic_id = request.path_params?.id;
      if (!topic_id || topic_id !== state.topic_id) throw new Error("TEST_TOPIC_CONTEXT_MISMATCH");
      state.canonical_script_ref ??= token("TEST-CANONICAL-SCRIPT");
      return {
        data_classification: "TEST_ONLY",
        topic_id,
        canonical_script_ref: state.canonical_script_ref,
        status: "TEST_ONLY_READ_MODEL",
        provider_execution: false,
      };
    }
  }
}

export function isControlledCoreServerTestMode(): boolean {
  return process.env.ACPOS_RUNTIME_MODE !== "PRODUCTION";
}

export function getControlledCoreTestRuntimeBindings(): CoreRuntimeBindings {
  return {
    authorize: async () => ({ allowed: true }),
    execute,
    audit: async (entry) => {
      state.audit.push({ ...entry, data_classification: "TEST_ONLY", recorded_at: new Date().toISOString() });
      if (state.audit.length > 500) state.audit.splice(0, state.audit.length - 500);
    },
  };
}
