# v2.2.33 重新對齊包（STAGE-01..04 / 首頁 + 儀表頁）

- 目標治理：`GOV-REV-20260927-GOVERNANCE-IDENTITY-NEGATIVE-TRACE-AUDITOR-INDEPENDENCE-HARDENING`（`v2.2.33`，head `4eb7163f`）
- 授權：issue #59（`STAGE04_TO_STAGE05_REENTRY` 等）
- 對齊對象：`GLOBAL-HOME-SHELL-NAVIGATION`（首頁）、`workspace:WB-01`（儀表頁）
- 性質：重新對齊投影包（non-normative，`status: PLANNED`）。本包**不修改**任何原始階段產物，只提供可套用的目標內容；落地須在取得授權的 work unit 內逐步執行。

## 檔案清單（每檔皆含實際內容）
| 檔案 | 內容 |
|---|---|
| `target_governance.yaml` | 目標治理身分（UID/revision/bundle digest/head）與授權範圍 |
| `matrix_realignment.yaml` | 8 個 WU 的矩陣身分重簽、section/artifact delta、目標 coverage 數字 |
| `output_rename_map.yaml` | `PAGE_*` → `GOVERNED_UNIT_*` 的 operation/output 逐筆對照 |
| `operation_binding_realignment.yaml` | 8 個 WU 的完整新 operation_bindings（含 applicability/protocol/receipt） |
| `s083a_scope_authority.yaml` | S083A 適用範圍權威（S02/S03 = NA、S04 = REQUIRED） |
| `s083a_matrix_rows.yaml` | S083A 實際矩陣列（S04 每單位 13 個 domain 列）＋ checkpoint schema |
| `realignment_plan.yaml` | 30 條逐項對齊清單（類別/現值/目標值/目標檔） |
| `realignment_execution_steps.yaml` | 7 步逐步執行流程與驗證器 |

## 一、已合規（無須變更的實質內容）
- 兩單位的 STAGE-01..04 產物實體齊備，階段閉環完成。
- STAGE-03、STAGE-04 operation 身分與現行 profile 一致。
- STAGE-02 業務實體完整性（`BUSINESS_ENTITY_INVENTORY` / `BUSINESS_ENTITY_OPERATION_MATRIX` / `ENTITY_HIERARCHY_MATRIX` / `FUNCTION_ADMISSION_SCORECARD`）齊備。
- STAGE-01 `source_projection_admission` 已符合 v2.2.33 schema，且 `SOURCE_PROJECTION_FREEZE_RECEIPT` 實體存在。
- STAGE-04 `BASIC_DESIGN_PACKAGE` 以 UID+hash 綁定 13 個 domain、`BASIC_DESIGN_FROZEN`、人工核准、`hidden_defect_sweep` 零缺口。

## 二、需對齊的漂移（本包已給出目標內容）

### 2.1 矩陣身分與節覆蓋
每個 WU：`governance_uid` 由 `GOV-REV-20260925-NORMATIVE-EXECUTION-MATRIX` 重簽為當前 UID。
`WEB-GOV-01-S083A` 缺口與處置：

| Stage | 適用性 | 內容 |
|---|---|---|
| STAGE-02 | `NOT_APPLICABLE_WITH_AUTHORITY` | Basic Design stepwise 由 STAGE-04 擁有；權威檔 `s083a_scope_authority.yaml` |
| STAGE-03 | `NOT_APPLICABLE_WITH_AUTHORITY` | 同上 |
| STAGE-04 | `REQUIRED` | 每單位 13 個 domain 各一列，`required_artifact_type = BASIC_DESIGN_DOMAIN_STEPWISE_CHECKPOINT`，`evidence_state: TO_MATERIALIZE` |

矩陣目標 coverage（section / artifact）：
| Stage | 現行 required 節數 | 目標 artifact 數 | 需新增 |
|---|---|---|---|
| STAGE-01 | 22 | 11 | artifact `GOVERNED_UNIT_BASE_BLUEPRINT` |
| STAGE-02 | 25 | 20 | section `S083A`、artifact `GOVERNED_UNIT_CONSTRUCTION_SPEC_PACKAGE`、`GOVERNED_UNIT_FUNCTIONAL_REVIEW_EVIDENCE` |
| STAGE-03 | 30 | 10 | section `S083A` |
| STAGE-04 | 27 | 5 | section `S083A` |

### 2.2 PAGE → GOVERNED_UNIT 身分重簽
| Stage | 現行 operation | 目標 operation | 現行 output | 目標 output |
|---|---|---|---|---|
| STAGE-01 | `PAGE_BASE_BLUEPRINT_COMPILE` | `GOVERNED_UNIT_BASE_BLUEPRINT_COMPILE` | `PAGE_BASE_BLUEPRINT` | `GOVERNED_UNIT_BASE_BLUEPRINT` |
| STAGE-02 | `PAGE_CONSTRUCTION_SPEC_COMPILE` | `GOVERNED_UNIT_CONSTRUCTION_SPEC_COMPILE` | `PAGE_CONSTRUCTION_SPEC_PACKAGE` | `GOVERNED_UNIT_CONSTRUCTION_SPEC_PACKAGE` |

### 2.3 operation binding schema 補齊
所有 8 個 WU 的每個 operation 綁定補上：
`applicability: REQUIRED`、`executor_protocol: PYTHON_STAGE_OPERATION_V1`、`operation_receipt_ref: .../EVIDENCE/OPERATION_RECEIPTS/<OP>.yaml`。

### 2.4 executor owner 合法化
STAGE-01、STAGE-03 綁定 `governance/ci/stage_execution_engine.py`（觸發 `COMMON_ENGINE_RECURSIVE_EXECUTOR_FORBIDDEN`），目標改為專用 executor：
`.github/scripts/stage01_op_NN_<op>.py`、`stage03_op_NN_<op>.py`（狀態 `TO_CREATE`）。

## 三、執行前提
`CURRENT_GOVERNED_UNIT_FOUNDATION_FROZEN` + `PREDECESSOR_STAGE_CLOSED` + issue #59 授權；採 `STEPWISE_ONE_OPERATION_PER_INVOCATION`，`bulk_stage_materialization: FORBIDDEN`。
