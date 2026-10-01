# STAGE-01..11 全線缺陷與 Bug 登錄（Defect Register）

- 版本：2026-09-30 / rev-1
- 適用：`GLOBAL-HOME-SHELL-NAVIGATION`（governed unit）於 `rebuild-v2.1.1` 治理權威下的 STAGE-01..11 全生命週期
- 資料來源：`GOVERNANCE_LIFECYCLE_STAGE_REGISTRY.yaml`、`STAGE_EXECUTION_INVARIANT_REGISTRY.yaml`、`SECTION_NUMBER_REGISTRY.yaml`、`governance/ci/stage_execution_semantic_adapters.yaml`、`governance/ci/stage_execution_engine.py`、`09_TESTS/governance/validate_stage_execution_invariants.py`，以及本輪 STAGE-01..04 實作與閉環的實證。
- 原則：**明細條件不減，只重建邏輯**。本清單保留每一條既有條件，新增的是缺漏的檢查與統一聲明機制。

---

## 1. 方法與「缺陷」定義

本次以四份權威資料 + 引擎程式碼交叉比對，找出三類不一致：

1. **登錄自洽缺陷（intra-registry）**：單一 stage 列內，被引用的操作／輸出／適用性識別未出現在該列自身的 `operations`／`outputs`。
2. **跨階段連貫缺陷（cross-stage）**：相鄰 stage 的 `exit_gate` → `entry_gate`、`next_stage_uid`、交接輸入集合不連續。
3. **強制性缺口（enforcement gap）**：規範宣告了條件，但在定義期沒有任何驗證器會攔截其違反，導致「跑得過、卻缺件」。

修正後應由定義期單一次校驗全部攔截，而非等到執行期或閉環期才由人工補件。

## 2. 缺陷分級與統計

| 級別 | 定義 | 數量 |
|------|------|------|
| HIGH | 會直接造成產物缺件、階段無法閉環、或跨階段無法接手 | 9 |
| MEDIUM | 宣告與強制不一致，現階段可被既有流程掩蓋，但屬結構性缺漏 | 4 類 |
| LOW/INFO | 可追溯性與可讀性問題 | 2 |

> 修正前盤點曾以「invariant 是否被 `stage_execution_engine.py` 引用」得到 62 筆 MEDIUM。經複核，該指標為誤導：`validate_stage_execution_invariants.py`（VAL-GOV-035）驗證的是**invariant registry 自身與其綁定文件的宣告一致性**，而非產品資料對 invariant 的符合性。真正缺陷已在下節重新分類，不重複計數。

---

## 3. 缺陷清單

### 3.1 HIGH

#### D-01 STAGE-05 `entry_gate` 與 STAGE-04 `exit_gate` 不相等
- 現況：STAGE-04 `exit_gate=CURRENT_GOVERNED_UNIT_FOUNDATION_FROZEN`；STAGE-05 `entry_gate=CURRENT_GOVERNED_UNIT_FOUNDATION_FROZEN_AND_PREDECESSOR_STAGE_CLOSED`。
- 影響：閘門鏈在字面上不連續。引擎未做 entry/exit 鏈校驗，故靜默通過；此為跨階段接手風險。
- 條件保留：STAGE-05 之 entry 語意（foundation frozen **且** predecessor stage closed）須完整保留，需以顯式建模表達「複合閘門」，而非簡化字串。

#### D-02 STAGE-02 `conditional_operations` 引用未登錄操作
- 現況：`conditional_operations.AI_INTERACTION_CONTINUITY_COMPILE` 不在 `operations`（13 項）內。
- 影響：條件式操作無 producer 綁定，條件成立時無法被執行／驗證。

#### D-03 STAGE-02 `conditional_outputs` 引用未登錄輸出
- 現況：`conditional_outputs.AI_INTERACTION_CONTINUITY_CONTRACT`（producer=`AI_INTERACTION_CONTINUITY_COMPILE`）不在 `outputs`（19 項）內。
- 影響：條件式輸出無 output row、無 producer、無 matrix 綁定。

#### D-04 STAGE-02 `required_output_applicability` 引用 5 個未登錄輸出
- 現況：`when_governed_governed_entity_scope_present` → `GOVERNED_ENTITY_INVENTORY`、`GOVERNED_ENTITY_OPERATION_MATRIX`；`when_entity_hierarchy_applies` → `ENTITY_HIERARCHY_MATRIX`；`when_continuous_work_unit_applies` → `INTERACTION_TOPOLOGY_MATRIX`；`when_user_visible_or_observable_required_operation_applies` → `FUNCTION_VISUAL_IMPACT_MATRIX`。（另 `when_ai_interaction_profile_applies` → `AI_INTERACTION_CONTINUITY_CONTRACT` 與 D-03 同一識別。）
- 影響：7 個適用性引用中 5 個輸出未登錄，條件式 denominator 無實體可對帳。
- 條件保留：全部 `when_*` 條件與其輸出集合一字不動保留，缺的是把這些輸出納入 `outputs` 與 `output_producers`。

#### D-05..D-09（同屬 STAGE-02 conditional 家族）
- 上列 D-02..D-04 的 7 個懸空識別，各自為獨立可追溯缺陷（`AI_INTERACTION_CONTINUITY_COMPILE`、`AI_INTERACTION_CONTINUITY_CONTRACT`、`GOVERNED_ENTITY_INVENTORY`、`GOVERNED_ENTITY_OPERATION_MATRIX`、`ENTITY_HIERARCHY_MATRIX`、`INTERACTION_TOPOLOGY_MATRIX`、`FUNCTION_VISUAL_IMPACT_MATRIX`），合計 8 筆 HIGH（1 continuity + 7 registry 引用，其中 contract 重複計為 1）。
- 說明：此家族是「缺東缺西」最典型來源——宣告了條件輸出，卻未在登錄中生成對應 row 與 producer。

### 3.2 MEDIUM（結構性強制缺口）

#### D-10 引擎定義期不校驗 intra-stage 引用自洽
- 位置：`stage_execution_engine.py:259 validate_definition_data`。
- 問題：不檢查 `conditional_operations`／`conditional_outputs`／`required_output_applicability`／`output_producers` 的識別是否屬於本 stage 的 `operations`／`outputs`。故 D-02..D-04 靜默通過。
- 修正邏輯：新增定義期校驗（見 design.md C2），一次攔截所有懸空引用。

#### D-11 引擎不校驗 entry/exit/next 閘門鏈
- 問題：無函式檢查 `STAGE(n).exit_gate` 與 `STAGE(n+1).entry_gate` 的相容性，也不檢查 `next_stage_uid` 指向。
- 修正邏輯：新增跨階段閘門鏈校驗（C3），並要求複合閘門以結構化欄位宣告（C1 schema）。

#### D-12 孤兒 invariant
- 現況：`SINGLE_STATE_SINGLE_ORCHESTRATOR_STAGE_CORE` 僅出現於 `STAGE_EXECUTION_INVARIANT_REGISTRY.yaml:48`，未在 VAL-GOV-035 的 `required` 列舉（line 32）中，也未在任何引擎／驗證器被引用。
- 影響：宣告了一條 invariant 但不具任何強制力，且未被列舉清單納管。
- 修正邏輯：將此 invariant 納入 required 列舉，或明確標記其為文件性並移除強制期待。

#### D-13 各 stage `required_evidence` 未與 operation/output 綁定
- 現況：每個 stage 皆宣告 `required_evidence`（如 STAGE-02 `GOVERNED_UNIT_FUNCTIONAL_REVIEW_EVIDENCE`），但登錄中無欄位聲明「由哪個 operation 產生、對應哪個 output」。
- 影響：證據是否被實體化，無法由定義期判定；閉環期易出現「evidence not in outputs」。
- 修正邏輯：新增 `evidence_producers` 綁定並納入 matrix 的 `every_required_evidence_type_must_be_represented` 校驗（C5）。

#### D-14 invariant 的「強制力」未綁定到 closure operation
- 現況：STAGE closure 契約（`governance/execution-domains/STAGE/STEPS.yaml`）含 `VERIFY_INVARIANTS`，但沒有機械化綁定證明「哪個 invariant 由哪個 closure operation/receipt 覆蓋」。
- 影響：多數 invariant（如 `RELATION_SEMANTIC_SEPARATION`、`FUNCTIONAL_CONTRACT_COMPLETENESS`…）僅在宣告層被驗證，產品層是否遵守無客觀證據。
- 修正邏輯：master plan 為每條 invariant 宣告 `enforcement_owner`（validator id 或 closure operation uid），並在定義期檢查無孤兒、無未覆蓋。

### 3.3 LOW / INFO

#### D-15 STAGE-02 `required_normative_section_uids` 與 mother-spec 的相對覆蓋
- 現況：S083A（Basic Design Stepwise Authoring and Review Flow）已被 STAGE-02/03/04 正確列入 required sections（`WEB-GOV-01-S083A`=True）。先前「矩陣少 24 節」屬先驗資料缺漏，已於本輪修正。
- 殘留：STAGE-01 及 STAGE-05..11 未列 S083A（多數語意上不適用），需在 master plan 明確標記 `applicable`／`AUTHORIZED_NOT_APPLICABLE`，避免「未列＝缺漏」的判讀歧義。

#### D-16 缺少單一機器可讀的全線計畫檔
- 現況：STAGE-01..11 的契約散落在 registry、adapters、invariants、sections、engine 四處；無單一檔可一次宣告並自檢。
- 修正邏輯：新增 `STAGE_EXECUTION_MASTER_PLAN.yaml`（C1），為 C2–C7 校驗的唯一輸入。

---

## 4. 不減條件的修復邏輯重建原則

1. 既有 `operations`／`outputs`／`required_normative_section_uids`／`required_evidence`／`validators`／`output_producers` 與全部 `when_*` 條件**一字不改地保留**。
2. 對懸空引用（D-02..D-04）：只**新增**對應的 output row 與 producer 綁定，及對應 operation 的登錄；不改動條件式宣告。
3. 對閘門鏈（D-01）：以結構化欄位保留複合語意，例如 `entry_gate_terms` 列出複合項，另存 `entry_gate` 顯示字串；不刪除任一詞。
4. 新增的校驗全部 fail-closed，且可在 `--definition-audit-all` 一次攔截，不新增執行期負擔。
5. 一律新增檔案／欄位，不刪除、不覆寫既有權威內容（符合 no-delete 原則）。

## 5. 一次性完整規劃可行性（結論）

**可行。** 現行架構已具備一次性規劃所需的全部素材，缺的只是「單一宣告 + 定義期全線閉合校驗」：

- 引擎已有 `plan_range(start,end)`（`stage_execution_engine.py:396`）與 `EXPLICIT_STAGE_RANGE_EXECUTION` invariant（requested range 即執行授權、inclusive、不許系統自行擴縮跳過）。
- 但 `plan_range` 只做 per-stage `plan()` 串接，**不做跨階段連貫與完整性校驗**，也不要求先有全線宣告。

實作路徑（見 `design.md` C1–C7）：

1. **C1**：建立 `STAGE_EXECUTION_MASTER_PLAN.yaml`，一次宣告 STAGE-01..11 的 entry/exit/next、operations、outputs+producers、conditional 引用、required sections、required evidence+producers、validator、invariant enforcement owner。
2. **C2–C7**：於 `validate_definition_data` 串入 6 組校驗：引用自洽（C2）、閘門/next 鏈（C3）、交接輸入集合（C4）、evidence/section 覆蓋（C5）、invariant 覆蓋（C6）、上線就緒閘門（C7）。
3. 以 `--definition-audit-all` 於**執行前**一次攔截全部缺漏；通過後才允許 `--plan-range STAGE-01 STAGE-11` 產出可執行計畫。
4. 全線連貫性由 C3/C4 保證「前一階段 exit 條件 = 後一階段 entry 前提、交接輸入集合完備」，避免某階段漏洞導致後續無法執行。

如此即可在「一個規劃階段」內定義所有 stage 契約並驗證跨階段連貫，執行期只做「逐 operation 落地」。
