# ACPOS Current Stage Flow

此目錄只保留「執行規格所需的最小產品端資料」，不得再建立第二套 Stage 規範、第二份 Current State、重複 transition matrix、重複 permission matrix、rearm request 或 workflow-owned authority。

## 單一真相來源

1. Current Governance：
   `STAGE_EXECUTION/SHARED_AUTHORITY/CURRENT_GOVERNANCE_SELECTION.yaml`
2. Stage 01→11 的正式規格：
   Current Governance 內的 `GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml` 與 Mother 01→04。
3. 本次執行範圍：
   `FULL_STAGE_LIFECYCLE_AUTHORIZATION_CONTRACT.yaml`。此檔只允許保存執行範圍，不得複製 Mother 的 Stage topology、Stage contract、permission 或 closure 規格。
4. 每個 Work Unit 的唯一執行／續作狀態：
   `EXECUTION_STATE.yaml`。
   `WORK_UNIT.yaml.current_status` 僅為目前 Governance Engine 的相容投影，不得作為第二 Resume Authority。
5. Stage successor 的 exact runtime binding：
   `EXACT_OPERATION_BINDING_SOURCES/`，到達該 Stage 前必須完整。
6. 執行中由 predecessor 解析出的 successor binding：
   `GENERATED_BINDINGS/`。
7. Stage-01 原始來源選擇：
   `SOURCE_REVIEW_INPUTS/`。

## 固定執行主鏈

`Mother specification`
→ `stage_lifecycle_gate.py`
→ `current_stage_execute.py`
→ operation checkpoint
→ `common_stage_human_gate.py`（只有 Mother 定義的正式人工 Gate 才可暫停）
→ `common_stage_preterminal.py`
→ read-only validation
→ `common_stage_terminalizer.py`
→ `common_successor_work_unit_builder.py`
→ 下一個 registered Stage。

正常 PASS 必須在使用者要求的 inclusive Stage range 內自動繼續，不再依賴 branch-local workflow dispatch、external rearm、第二個 Current Resume request 或另一個 workflow 的 exact-head handshake。

## Workflow 最小集合

- `product-stage-lifecycle-driver.yml`：唯一 effectful Stage-01→11 lifecycle driver。
- `product-full-stage-lifecycle-validation.yml`：純讀取的 Stage 規格/結構稽核，不得執行 operation 或 materialize successor。
- `product-clean-bootstrap-validation.yml`：Stage-01 clean materialization 的純驗證。
- `product-stage03-human-review.yml`：Mother 定義的 Stage-03 正式人工視覺審查。

任何新增 workflow 若只是包裝上述流程、複製 Current State、重新 dispatch 同一 Stage、重複 validation 或建立 stage-local authority，均視為不必要治理層，不得加入。

## Closure 規則

Stage closure 只由目前 Work Unit 的實體內容與稽核結果決定：

- registered operations 全部有 terminal receipt；
- required outputs 實際存在、可解析且 REQUIRED fields 完整；
- scanner / validator / hidden-defect result 符合 Mother；
- normalized evidence PASS；
- Work Unit / EXECUTION_STATE / matrix 一致；
- cross-stage handoff 與 successor binding 可用；
- 若 Mother 定義 human gate，必須有正式 approval evidence。

Git HEAD、workflow 名稱或歷史 PASS 只能作為 evidence identity，不能取代內容稽核本身。

## 禁止重新引入

不得重新建立：

- CURRENT_EXECUTION_RESOLUTION
- CURRENT_REMEDIATION_STATE
- CURRENT_STAGE*_RESUME_REQUEST
- CURRENT_STAGE_EXECUTION_REQUEST
- CURRENT_STAGE_RESUME.yaml
- CLOSURE_RESUME_POINT.yaml
- EXACT_HEAD_GATE_RECEIPTS.yaml
- FULL_STAGE_DEFECT_LEDGER
- product-side transition/permission/runtime-adapter projection matrices
- product-side common closure/successor protocol copies
- thin successor/materialize wrapper scripts that only re-dispatch another owner
- Stage-specific resume/materialize/validation/execute wrapper workflows
- push → wait another workflow → rearm 的控制鏈

如果真正缺少的是 operation executor、scanner、validator、required input 或 runtime target，應直接標示為該 Stage 的 specification/runtime readiness gap；不得再用新的狀態檔或 workflow 包住缺口。
