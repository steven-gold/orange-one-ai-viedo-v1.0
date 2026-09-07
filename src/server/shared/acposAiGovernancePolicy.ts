export const ACPOS_AI_GOVERNANCE_POLICY_VERSION = "ACPOS_AI_GOVERNANCE_V1.0" as const;

export const ACPOS_AI_RESPONSE_POLICY = [
  "You are the governed ACPOS AI Conversation Core, not a generic chat assistant.",
  "Preserve the exact current conversation/thread/change/project/topic context supplied by ACPOS.",
  "Current System Truth, Authority, registered owners, permissions, evidence and explicit human decisions outrank model inference.",
  "Never present an inference, estimate, assumption, or another AI response as a verified fact.",
  "Never invent project facts, runtime state, deployment state, permissions, provider health, source content, identifiers, versions, hashes, evidence, or approval.",
  "Before proposing a system change, review dependencies, conflicts, missing information, risks, alternatives and existing ACPOS owners.",
  "Resolve existing-system questions in this order: PAGE_UI -> SERVICE_RUNTIME -> API_OPERATION -> DATABASE_DATA_OWNER -> PROVIDER_PROFILE_ADAPTER -> PERMISSION_AUTHORITY -> WORKFLOW_LIFECYCLE -> AUTHORITY_VERSION.",
  "When a capability already has an ACPOS owner, choose REUSE before EXTEND, MODIFY, REPLACE, or CREATE_NEW. CREATE_NEW requires an explicit existing-system gap.",
  "Decision priority: P0 = architecture/legal/safety blocker; P1 = changes main workflow/data/permission/runtime/deploy behavior; P2 = resolvable from existing ACPOS truth/authority; P3 = safe existing default/standard.",
  "Ask the human only for true P0/P1 decisions. Resolve P2 from supplied ACPOS truth. Apply P3 only from supplied safe standards and label it as a recorded assumption.",
  "Do not treat an AI answer as a human decision, approval, Candidate, canon lock, production mutation, deployment approval, or provider approval.",
  "For explicit user decisions, preserve the exact user wording as a quote and mark the decision status. Never mark a decision CONFIRMED unless the quoted text is present in the current user message.",
  "If required evidence or context is absent, say it is unresolved. Do not silently fill the gap.",
  "Facts must cite one or more supplied evidence/source/context refs. If no ref exists, classify the statement as inference or unresolved.",
  "Confidence may only be stated when supplied evidence/projection logic provides it. Never invent a confidence score.",
  "Answer in the user's language unless the user explicitly requests another language.",
  "Keep answers actionable and scoped to the current ACPOS context. Do not create a parallel system, provider registry, queue, permission model, audit model, conversation backend, or data owner.",
  "Provider/model selection is system-owned. Never ask the user to manually pick a Provider unless Current Authority explicitly requires it.",
  "Raw AI responses are discussion material only. Formal ACPOS changes remain gated by Assistant Summary -> Evaluation -> Human Decision -> Structured Decision -> Candidate/Review where that page Authority requires it.",
] as const;

export const ACPOS_AI_RESPONSE_SCHEMA = {
  type: "object",
  required: [
    "answer",
    "assistant_summary",
    "facts",
    "inferences",
    "open_questions",
    "resolved_items",
    "decision_updates",
    "candidate_ready",
    "response_mode",
  ],
  additionalProperties: false,
  properties: {
    answer: { type: "string" },
    assistant_summary: { type: "string" },
    facts: {
      type: "array",
      items: {
        type: "object",
        required: ["statement", "evidence_refs"],
        additionalProperties: false,
        properties: {
          statement: { type: "string" },
          evidence_refs: { type: "array", items: { type: "string" } },
        },
      },
    },
    inferences: {
      type: "array",
      items: {
        type: "object",
        required: ["statement", "basis"],
        additionalProperties: false,
        properties: {
          statement: { type: "string" },
          basis: { type: "string" },
        },
      },
    },
    open_questions: {
      type: "array",
      items: {
        type: "object",
        required: ["priority", "question", "reason"],
        additionalProperties: false,
        properties: {
          priority: { enum: ["P0", "P1"] },
          question: { type: "string" },
          reason: { type: "string" },
        },
      },
    },
    resolved_items: {
      type: "array",
      items: {
        type: "object",
        required: ["priority", "item", "resolution", "basis_refs"],
        additionalProperties: false,
        properties: {
          priority: { enum: ["P2", "P3"] },
          item: { type: "string" },
          resolution: { type: "string" },
          basis_refs: { type: "array", items: { type: "string" } },
        },
      },
    },
    decision_updates: {
      type: "array",
      items: {
        type: "object",
        required: ["decision_key", "status", "statement", "user_quote"],
        additionalProperties: false,
        properties: {
          decision_key: { type: "string" },
          status: { enum: ["CONFIRMED", "REJECTED", "OPEN_P0", "OPEN_P1", "SUPERSEDED"] },
          statement: { type: "string" },
          user_quote: { type: ["string", "null"] },
        },
      },
    },
    candidate_ready: { type: "boolean" },
    response_mode: { enum: ["DIRECT", "REVIEW", "DECISION_REQUIRED", "BLOCKED"] },
  },
} as const;

export type AcposDecisionStatus = "CONFIRMED" | "REJECTED" | "OPEN_P0" | "OPEN_P1" | "SUPERSEDED";

export type AcposGovernedAiResponse = {
  answer: string;
  assistant_summary: string;
  facts: Array<{ statement: string; evidence_refs: string[] }>;
  inferences: Array<{ statement: string; basis: string }>;
  open_questions: Array<{ priority: "P0" | "P1"; question: string; reason: string }>;
  resolved_items: Array<{ priority: "P2" | "P3"; item: string; resolution: string; basis_refs: string[] }>;
  decision_updates: Array<{
    decision_key: string;
    status: AcposDecisionStatus;
    statement: string;
    user_quote: string | null;
  }>;
  candidate_ready: boolean;
  response_mode: "DIRECT" | "REVIEW" | "DECISION_REQUIRED" | "BLOCKED";
};

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function stringList(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const values = value.map(text);
  return values.every((item): item is string => Boolean(item)) ? values : null;
}

function stripJsonFence(raw: string): string {
  const trimmed = raw.trim();
  const match = trimmed.match(/^\`\`\`(?:json)?\s*([\s\S]*?)\s*\`\`\`$/i);
  return match ? match[1].trim() : trimmed;
}

export function parseAcposGovernedAiResponse(raw: string): AcposGovernedAiResponse | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(stripJsonFence(raw));
  } catch {
    return null;
  }
  const root = record(parsed);
  if (!root) return null;
  const answer = text(root.answer);
  const assistantSummary = text(root.assistant_summary);
  if (!answer || !assistantSummary || typeof root.candidate_ready !== "boolean") return null;
  if (!["DIRECT", "REVIEW", "DECISION_REQUIRED", "BLOCKED"].includes(String(root.response_mode))) return null;

  if (!Array.isArray(root.facts) || !Array.isArray(root.inferences) || !Array.isArray(root.open_questions)
      || !Array.isArray(root.resolved_items) || !Array.isArray(root.decision_updates)) return null;

  const facts = root.facts.flatMap((value) => {
    const item = record(value);
    const statement = text(item?.statement);
    const evidenceRefs = stringList(item?.evidence_refs);
    return statement && evidenceRefs && evidenceRefs.length > 0 ? [{ statement, evidence_refs: evidenceRefs }] : [];
  });
  if (facts.length !== root.facts.length) return null;

  const inferences = root.inferences.flatMap((value) => {
    const item = record(value);
    const statement = text(item?.statement);
    const basis = text(item?.basis);
    return statement && basis ? [{ statement, basis }] : [];
  });
  if (inferences.length !== root.inferences.length) return null;

  const openQuestions: AcposGovernedAiResponse["open_questions"] = root.open_questions.flatMap((value) => {
    const item = record(value);
    const priority = item?.priority;
    const question = text(item?.question);
    const reason = text(item?.reason);
    return (priority === "P0" || priority === "P1") && question && reason
      ? [{ priority, question, reason }]
      : [];
  });
  if (openQuestions.length !== root.open_questions.length) return null;

  const resolvedItems: AcposGovernedAiResponse["resolved_items"] = root.resolved_items.flatMap((value) => {
    const item = record(value);
    const priority = item?.priority;
    const itemText = text(item?.item);
    const resolution = text(item?.resolution);
    const basisRefs = stringList(item?.basis_refs);
    return (priority === "P2" || priority === "P3") && itemText && resolution && basisRefs && basisRefs.length > 0
      ? [{ priority, item: itemText, resolution, basis_refs: basisRefs }]
      : [];
  });
  if (resolvedItems.length !== root.resolved_items.length) return null;

  const decisionUpdates = root.decision_updates.flatMap((value) => {
    const item = record(value);
    const decisionKey = text(item?.decision_key);
    const status = item?.status;
    const statement = text(item?.statement);
    const userQuote = item?.user_quote === null ? null : text(item?.user_quote);
    return decisionKey
      && ["CONFIRMED", "REJECTED", "OPEN_P0", "OPEN_P1", "SUPERSEDED"].includes(String(status))
      && statement
      ? [{
          decision_key: decisionKey,
          status: status as AcposDecisionStatus,
          statement,
          user_quote: userQuote,
        }]
      : [];
  });
  if (decisionUpdates.length !== root.decision_updates.length) return null;

  return {
    answer,
    assistant_summary: assistantSummary,
    facts,
    inferences,
    open_questions: openQuestions,
    resolved_items: resolvedItems,
    decision_updates: decisionUpdates,
    candidate_ready: root.candidate_ready,
    response_mode: root.response_mode as AcposGovernedAiResponse["response_mode"],
  };
}

export function validateDecisionUpdatesAgainstUserMessage(
  response: AcposGovernedAiResponse,
  currentUserMessage: string,
): AcposGovernedAiResponse {
  const decision_updates = response.decision_updates.filter((entry) => {
    if (entry.status === "OPEN_P0" || entry.status === "OPEN_P1") return true;
    return Boolean(entry.user_quote && currentUserMessage.includes(entry.user_quote));
  });

  for (const question of response.open_questions) {
    const status: AcposDecisionStatus = question.priority === "P0" ? "OPEN_P0" : "OPEN_P1";
    const exists = decision_updates.some((entry) =>
      entry.status === status && entry.statement.trim() === question.question.trim()
    );
    if (!exists) {
      decision_updates.push({
        decision_key: `OPEN:${question.priority}:${question.question}`,
        status,
        statement: question.question,
        user_quote: null,
      });
    }
  }

  return { ...response, decision_updates };
}

export function enforceAcposGovernanceEvidence(
  response: AcposGovernedAiResponse,
  allowedRefs: ReadonlySet<string>,
): AcposGovernedAiResponse {
  const facts: AcposGovernedAiResponse["facts"] = [];
  const inferences: AcposGovernedAiResponse["inferences"] = [...response.inferences];
  let evidenceViolation = false;

  for (const fact of response.facts) {
    const valid = fact.evidence_refs.length > 0
      && fact.evidence_refs.every((ref) => allowedRefs.has(ref));
    if (valid) {
      facts.push(fact);
      continue;
    }
    evidenceViolation = true;
    inferences.push({
      statement: fact.statement,
      basis: "EVIDENCE_REFERENCE_NOT_PRESENT_IN_CURRENT_ACPOS_CONTEXT",
    });
  }

  const resolved_items: AcposGovernedAiResponse["resolved_items"] = [];
  for (const item of response.resolved_items) {
    const valid = item.basis_refs.length > 0
      && item.basis_refs.every((ref) => allowedRefs.has(ref));
    if (valid) {
      resolved_items.push(item);
      continue;
    }
    evidenceViolation = true;
    inferences.push({
      statement: `${item.item}: ${item.resolution}`,
      basis: "RESOLUTION_BASIS_REFERENCE_NOT_PRESENT_IN_CURRENT_ACPOS_CONTEXT",
    });
  }

  return {
    ...response,
    facts,
    inferences,
    resolved_items,
    candidate_ready: response.candidate_ready
      && !evidenceViolation
      && response.open_questions.length === 0,
    response_mode: response.open_questions.length > 0
      ? "DECISION_REQUIRED"
      : evidenceViolation && response.response_mode === "DIRECT"
        ? "REVIEW"
        : response.response_mode,
  };
}

export function enforceAcposDecisionConsistency(
  response: AcposGovernedAiResponse,
  existing: ReadonlyArray<{ decision_key: string; status: string; statement: string }>,
): AcposGovernedAiResponse {
  const openQuestions = [...response.open_questions];
  const updates = response.decision_updates.filter((entry) => {
    const prior = [...existing].reverse().find((item) => item.decision_key === entry.decision_key);
    if (!prior) return true;
    if (prior.status !== "CONFIRMED") return true;
    if (entry.status === "SUPERSEDED" && entry.user_quote) return true;
    if (entry.status === "CONFIRMED" && entry.statement.trim() === prior.statement.trim()) return true;

    const question = `既有已確認決策「${prior.statement}」與目前提議「${entry.statement}」衝突；是否明確重新開啟或取代此決策？`;
    if (!openQuestions.some((item) => item.priority === "P1" && item.question === question)) {
      openQuestions.push({
        priority: "P1",
        question,
        reason: "CONFIRMED_DECISION_CONFLICT_REQUIRES_AUTHORIZED_HUMAN_SUPERSESSION",
      });
    }
    return false;
  });

  return {
    ...response,
    open_questions: openQuestions,
    decision_updates: updates,
    candidate_ready: response.candidate_ready && openQuestions.length === 0,
    response_mode: openQuestions.length > 0 ? "DECISION_REQUIRED" : response.response_mode,
  };
}

export function renderAcposGovernedAiResponse(response: AcposGovernedAiResponse): string {
  const parts = [response.answer.trim()];
  if (response.inferences.length) {
    parts.push(
      ["推論（非已驗證事實）：", ...response.inferences.map((item) => `- ${item.statement}`)].join("\n"),
    );
  }
  if (response.open_questions.length) {
    parts.push(
      ["需要你決定：", ...response.open_questions.map((item) => `- [${item.priority}] ${item.question} — ${item.reason}`)].join("\n"),
    );
  }
  return parts.filter(Boolean).join("\n\n");
}
