# STAGE-01..11 全流程沙盤推演報告（Sandbox Tabletop）

- 版本：2026-09-30 / rev-1
- 目的：在**不落地任何 effectful 產物**的前提下，對 STAGE-01..11 全線做一次唯讀沙盤推演，證明「一次規劃即可全線閉合、無缺件」，作為撰寫正式 STAGE 完整規範的前置證據。
- 產物：`/tmp/opencode/stage_sandbox/{sandbox.py,tree.py,base_tree.mmd}`

## 1. 沙盤方法

以四份權威（lifecycle registry、invariant registry、section registry、semantic adapters）建構 11 個 stage 的記憶體模型，套用「提議宣告」後執行 9 類校驗（C-A..C-I）。沙盤為唯讀，不呼叫引擎、不產生產品檔、不違反 `operation-by-operation`。

## 2. 校驗類別

| 代號 | 校驗 | 目的 |
|------|------|------|
| C-A | stage 內引用自洽 | 條件式操作/輸出/適用性/生產者皆屬本 stage |
| C-B | 閘門鏈 | `entry_gate[i] == base(exit_gate[i-1])` |
| C-C | 順序鏈 | `next_stage_uid[i-1] == stage_uid[i]` |
| C-D | 輸入可解析 | 每個 input 由更早 stage 產出或為外部來源 |
| C-E | 證據生產者 | 每個 required_evidence 有宣告的生產操作 |
| C-F | 章節可解析 | 每個 required section 存在於 section registry |
| C-G | invariant 錨定 | invariant 不得只存在於 registry（孤兒） |
| C-H | 上線就緒 | 每 stage 至少一個交付物且具 exit_gate |
| C-I | 適配器投影 | 每 stage 有語意/掃描維度 |

## 3. 沙盤結果

| 模式 | HIGH | MEDIUM | 合計 |
|------|------|--------|------|
| CURRENT（現況） | 8 | 10 | 18 |
| FIXED（套用提議宣告後） | 0 | 0 | **0** |

現況 18 筆全數落在 STAGE-02（8 HIGH 懸空引用）與證據/孤兒（10 MEDIUM）；其餘 10 個 stage 之閘門鏈、順序鏈、輸入來源、章節解析**全數通過**。套用提議宣告後，18 筆全數歸零。

## 4. 提議宣告（沙盤證明可閉合）

1. **STAGE-02 條件式成員登錄**：將 `AI_INTERACTION_CONTINUITY_COMPILE`（操作）、`AI_INTERACTION_CONTINUITY_CONTRACT`（輸出）登錄為 stage 成員並綁定生產者。
2. **STAGE-02 適用性輸出登錄 + 命名對齊**：`INTERACTION_TOPOLOGY_MATRIX` 對齊為既有 `INTERACTION_TOPOLOGY_SPEC`；其餘 4 個矩陣（`GOVERNED_ENTITY_INVENTORY`、`GOVERNED_ENTITY_OPERATION_MATRIX`、`ENTITY_HIERARCHY_MATRIX`、`FUNCTION_VISUAL_IMPACT_MATRIX`）登錄為輸出並補上對應生產操作。
3. **STAGE-05 複合閘門結構化**：`entry_gate = {base: CURRENT_GOVERNED_UNIT_FOUNDATION_FROZEN, requires: [PREDECESSOR_STAGE_CLOSED]}`，保留全部語意且與 STAGE-04 exit 對齊。
4. **證據生產者宣告**：為 11 個 stage 的 13 個 required_evidence 各宣告 `evidence_producers`（子操作 → 證據）。
5. **孤兒 invariant 錨定**：`SINGLE_STATE_SINGLE_ORCHESTRATOR_STAGE_CORE` 綁定至 `VAL-GOV-035` 強制驗證範圍。

## 5. 受治理單元基礎樹（Base Tree）

由 registry 推導（套用提議宣告後）：

- stage 總數 11、跨階段銜接邊 27、輸出總數 65、操作總數 121、必要證據 13、必要章節 211。
- 樹頂為 `GOVERNED_UNIT_CLOSED` → `final page usable`；樹根為 `RAW_SOURCE_SET + CURRENT_AUTHORITY_SET`。
- 每個下游 input 皆可追溯至更早 stage 的具名輸出（C-D 全通過）。
- 有 42 個 stage-local 產物未被下游以 input 直接引用，屬**階段內部程序/交接產物**（如 preflight、problem register、visual checkpoint、evidence），非缺件。

> 需在正式規範中明確：**階段內部產物**與**跨階段交接產物**的分類欄位，避免「未被子階段引用」被誤判為缺漏。

## 6. 待權威決策事項（不可由 Agent 捏造）

1. 第 2 項中，`INTERACTION_TOPOLOGY_MATRIX` 與 `INTERACTION_TOPOLOGY_SPEC` 是否同一物件的命名對齊，或為兩個獨立產物。
2. 新增的 4 個矩陣生產操作之正式命名與所屬 phase。
3. 13 個 required_evidence 的正式生產操作與所屬 stage phase。
4. 42 個 stage-local 產物的 `internal vs handoff` 分類。

## 7. 結論

- 沙盤證明：**全線一次性規劃在機制上可行，套用宣告後 0 缺件**，且跨階段連貫性（閘門/順序/輸入來源/章節）全數成立。
- 下一步：在上述 4 項權威決策確認後，將提議宣告正式寫入 `STAGE_EXECUTION_MASTER_PLAN.yaml` 並新增 C2–C7 引擎校驗，使 `--definition-audit-all` 於執行前一輪攔截全部缺漏。
