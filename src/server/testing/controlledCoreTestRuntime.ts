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
  label: string;
};

type TestState = {
  projects: TestProject[];
  topics: TestTopic[];
  threads: TestThread[];
  project_id: string | null;
  project_version_ref: string | null;
  topic_id: string | null;
  topic_version_ref: string | null;
  dna_version_ref: string | null;
  blueprint_version_ref: string | null;
  conversation_id: string | null;
  candidate_ref: string | null;
  work_item: string | null;
  audit: Array<Record<string, unknown>>;
};

const state: TestState = {
  projects: [],
  topics: [],
  threads: [],
  project_id: null,
  project_version_ref: null,
  topic_id: null,
  topic_version_ref: null,
  dna_version_ref: null,
  blueprint_version_ref: null,
  conversation_id: null,
  candidate_ref: null,
  work_item: null,
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

function projection() {
  const topicMode = Boolean(state.topic_id);
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
    projects: state.projects.map((project) => ({
      project_id: project.project_id,
      project_version_ref: project.project_version_ref,
      label: project.label,
    })),
    topics: state.topics
      .filter((topic) => !state.project_id || topic.project_id === state.project_id)
      .map((topic) => ({ topic_id: topic.topic_id, topic_version_ref: topic.topic_version_ref, label: topic.label })),
    work_items: (topicMode
      ? ["TOPIC_SCOPE", "PRODUCTION_SCRIPT"]
      : ["STORY", "CHAPTER", "WORLD_SETTING", "DNA", "BLUEPRINT"])
      .map((work_item) => ({ work_item, label: work_item })),
    threads: state.threads
      .filter((thread) => !state.project_id || thread.project_id === state.project_id)
      .filter((thread) => !state.topic_id || thread.topic_id === state.topic_id)
      .map((thread) => ({ conversation_id: thread.conversation_id, label: thread.label })),
    display_values: {
      test_mode: "TEST_ONLY",
      test_data_classification: "TEST_ONLY",
      runtime_state: "CONTROLLED_TEST_RUNTIME",
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
      return { data_classification: "TEST_ONLY", project_id, project_version_ref, state: "DRAFT" };
    }

    case "CORE-01-PORT-PROJECT-VALIDATE": {
      const ref = request.path_params?.projectVersionId;
      const project = state.projects.find((item) => item.project_version_ref === ref);
      if (!project) throw new Error("TEST_PROJECT_VERSION_NOT_FOUND");
      project.state = "VALIDATED";
      return { data_classification: "TEST_ONLY", project_version_ref: project.project_version_ref, state: project.state };
    }

    case "CORE-01-PORT-PROJECT-CONFIRM": {
      const ref = request.path_params?.id;
      const project = state.projects.find((item) => item.project_version_ref === ref);
      if (!project) throw new Error("TEST_PROJECT_VERSION_NOT_FOUND");
      project.state = "CORE_MODELING";
      state.project_id = project.project_id;
      state.project_version_ref = project.project_version_ref;
      state.dna_version_ref ??= `${project.project_id}-DNA-V1`;
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
      return { data_classification: "TEST_ONLY", story_candidate_set_ref: token("TEST-STORY-SET"), project_id: state.project_id };
    }

    case "CORE-01-PORT-TOPIC-CREATE": {
      const payload = requireTestPayload(request);
      const project_id = request.path_params?.projectId;
      if (!project_id || !state.projects.some((item) => item.project_id === project_id)) throw new Error("TEST_PROJECT_NOT_FOUND");
      const topic_id = token("TEST-TOPIC");
      const topic_version_ref = `${topic_id}-V1`;
      const label = text(payload.fixture_label) ?? `[TEST] Topic ${topic_id.slice(-8)}`;
      state.topics.push({ topic_id, topic_version_ref, project_id, label });
      state.project_id = project_id;
      state.topic_id = topic_id;
      state.topic_version_ref = topic_version_ref;
      state.blueprint_version_ref = null;
      state.conversation_id = null;
      state.candidate_ref = null;
      state.work_item = "TOPIC_SCOPE";
      return { data_classification: "TEST_ONLY", topic_id, topic_version_ref, project_id };
    }

    case "CORE-01-PORT-THREAD-CREATE": {
      const payload = requireTestPayload(request);
      const project_id = request.path_params?.projectId;
      if (!project_id || project_id !== state.project_id) throw new Error("TEST_PROJECT_CONTEXT_MISMATCH");
      const conversation_id = token("TEST-CONV");
      const workItem = text(payload.work_item) ?? state.work_item ?? "STORY";
      const thread: TestThread = {
        conversation_id,
        project_id,
        topic_id: text(payload.topic_id),
        label: `[TEST] ${workItem} Thread`,
      };
      state.threads.push(thread);
      state.conversation_id = conversation_id;
      state.work_item = workItem;
      return { data_classification: "TEST_ONLY", conversation_id, project_id, work_item: workItem };
    }

    case "CORE-01-PORT-MESSAGE-SEND": {
      const payload = requireTestPayload(request);
      const conversation_id = request.path_params?.conversationId;
      if (!conversation_id || !state.threads.some((item) => item.conversation_id === conversation_id)) throw new Error("TEST_CONVERSATION_NOT_FOUND");
      return {
        data_classification: "TEST_ONLY",
        conversation_id,
        message_ref: token("TEST-MSG"),
        accepted: true,
        simulated_ai_execution: true,
        simulation_classification: "SIMULATED_EXTERNAL",
        message: text(payload.message),
      };
    }

    case "CORE-01-PORT-CANDIDATE-CREATE": {
      requireTestPayload(request);
      const candidate_ref = token("TEST-CANDIDATE");
      state.candidate_ref = candidate_ref;
      return { data_classification: "TEST_ONLY", candidate_ref, state: "CANDIDATE" };
    }

    case "CORE-01-PORT-CANDIDATE-COMPARE":
      return { data_classification: "TEST_ONLY", candidate_ref: state.candidate_ref, comparison: "TEST_ONLY" };

    case "CORE-01-PORT-CANDIDATE-DECIDE": {
      const payload = requireTestPayload(request);
      const candidate_ref = request.path_params?.id;
      if (!candidate_ref || candidate_ref !== state.candidate_ref) throw new Error("TEST_CANDIDATE_NOT_FOUND");
      return { data_classification: "TEST_ONLY", candidate_ref, decision: text(payload.decision) ?? "UNRESOLVED" };
    }

    case "CORE-01-PORT-DNA-LOCK": {
      requireTestPayload(request);
      if (!state.dna_version_ref) throw new Error("TEST_DNA_VERSION_NOT_FOUND");
      return { data_classification: "TEST_ONLY", dna_version_ref: state.dna_version_ref, lock_state: "REQUESTED" };
    }

    case "CORE-01-PORT-CORE-REVIEW":
    case "CORE-01-PORT-MOTHER-LOCK": {
      requireTestPayload(request);
      if (!state.project_version_ref) throw new Error("TEST_PROJECT_VERSION_NOT_FOUND");
      return { data_classification: "TEST_ONLY", project_version_ref: state.project_version_ref, request_ref: token("TEST-REQUEST") };
    }

    case "CORE-01-PORT-BLUEPRINT-CREATE": {
      const topic_id = request.path_params?.id;
      if (!topic_id || topic_id !== state.topic_id) throw new Error("TEST_TOPIC_CONTEXT_MISMATCH");
      const blueprint_version_ref = token("TEST-BLUEPRINT-V1");
      state.blueprint_version_ref = blueprint_version_ref;
      return { data_classification: "TEST_ONLY", topic_id, blueprint_version_ref, state: "BLUEPRINT_DRAFT" };
    }

    case "CORE-01-PORT-BLUEPRINT-VALIDATE": {
      const ref = request.path_params?.id;
      if (!ref || ref !== state.blueprint_version_ref) throw new Error("TEST_BLUEPRINT_VERSION_NOT_FOUND");
      return { data_classification: "TEST_ONLY", blueprint_version_ref: ref, state: "BLUEPRINT_REVIEW" };
    }

    case "CORE-01-PORT-BLUEPRINT-APPROVE": {
      const ref = request.path_params?.id;
      if (!ref || ref !== state.blueprint_version_ref) throw new Error("TEST_BLUEPRINT_VERSION_NOT_FOUND");
      return { data_classification: "TEST_ONLY", blueprint_version_ref: ref, state: "BLUEPRINT_APPROVED" };
    }

    case "CORE-01-PORT-CHILD-LOCK": {
      requireTestPayload(request);
      if (!state.blueprint_version_ref) throw new Error("TEST_BLUEPRINT_VERSION_NOT_FOUND");
      return { data_classification: "TEST_ONLY", blueprint_version_ref: state.blueprint_version_ref, lock_state: "REQUESTED" };
    }

    case "CORE-01-PORT-CANONICAL-SCRIPT": {
      const topic_id = request.path_params?.id;
      if (!topic_id || topic_id !== state.topic_id) throw new Error("TEST_TOPIC_CONTEXT_MISMATCH");
      return {
        data_classification: "TEST_ONLY",
        topic_id,
        canonical_script_ref: token("TEST-CANONICAL-SCRIPT"),
        status: "TEST_ONLY_READ_MODEL",
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
