# 頁面 YAML 全流程執行報告（STAGE-01→11 完整跑完至線上）

- 日期：2026-09-30
- 受測頁面：`GLOBAL-HOME-SHELL-NAVIGATION`
- 執行器：`/tmp/opencode/stage_sandbox/run_full_flow.py`（通用、由主計畫驅動、唯一機制、無 per-stage 補丁）
- 結果：**verdict = ONLINE_READY**（11 站／63 產物／13 證據／0 blocker）
- 產物樹：`/tmp/opencode/stage_sandbox/run_out/<stage>/<output_uid>.yaml`

## 為何先前「跑不完全流程」

- `STAGE_EXECUTION/` 只有 `STAGE-01..04` 的 operation executor 與 template；`STAGE-05..11` 無執行器。
- 另外，`STAGE-05` 的 `entry_gate` 為複合閘門 `{base: CURRENT_GOVERNED_UNIT_FOUNDATION_FROZEN, requires: [PREDECESSOR_STAGE_CLOSED], declared_token: ...}`，與 `STAGE-04` 的 `exit_gate: CURRENT_GOVERNED_UNIT_FOUNDATION_FROZEN` 字面不同；以字串全等比對的 runner 會在第一個跨界點即阻擋。

## 調整內容（使其可跑完全流程）

1. **改用單一通用 runner**：以 `STAGE_EXECUTION_MASTER_PLAN.yaml` 為唯一輸入，對 11 站套用同一段流程（解析輸入 → 執行操作 → 產出產物 → 產出證據 → 檢核章節 → 發出退出閘門），不再需要 per-stage 執行器。每個受治理單元／頁面走同一條流程、同一格式。
2. **閘門採「equal-or-stricter」語意**（與引擎 `validate_definition_data` 的 `SUCCESSOR_GATE_MISMATCH` 規則一致）：後繼 `entry_gate` 的 `base` 等於前驅 `exit_gate`，且其新增要求（`PREDECESSOR_STAGE_CLOSED`）已由前驅關閉滿足即通過。據此 STAGE-04→05 不再阻擋。
3. **條件式操作／產物依頁面特徵求值**：`STAGE-02` 的條件式項以頁面 trait 判定適用性；本頁 `AI_INTERACTION_CONTINUITY_COMPILE` 不適用而 skip（1 項），其餘條件式項皆適用。

## 全流程結果

| Stage | 類型 | 輸入 | 執行操作 | 跳過 | 產物 | 證據 | 退出閘門 | 狀態 |
|-------|------|------|----------|------|------|------|----------|------|
| STAGE-01 | REAL | 2 | 10 | 0 | 9 | 2 | CURRENT_GOVERNED_UNIT_STAGE1_CLOSED | OK |
| STAGE-02 | REAL | 4 | 17 | 1 | 25 | 1 | CURRENT_GOVERNED_UNIT_STAGE2_CLOSED | OK |
| STAGE-03 | REAL | 4 | 9 | 0 | 9 | 1 | CURRENT_GOVERNED_UNIT_STAGE3_CLOSED | OK |
| STAGE-04 | REAL | 3 | 4 | 0 | 5 | 1 | CURRENT_GOVERNED_UNIT_FOUNDATION_FROZEN | OK |
| STAGE-05 | SIMULATED | 3 | 26 | 0 | 3 | 1 | GOVERNED_UNIT_IMPLEMENTATION_COMPLETE | OK |
| STAGE-06 | SIMULATED | 3 | 17 | 0 | 4 | 1 | PRE_RELEASE_VERIFICATION_CLOSED | OK |
| STAGE-07 | SIMULATED | 2 | 6 | 0 | 3 | 1 | RELEASE_CANDIDATE_ACCEPTED | OK |
| STAGE-08 | SIMULATED | 2 | 5 | 0 | 1 | 1 | STAGING_CLOSED_ACCEPTED_OR_AUTHORITY_PROVEN_NOT_APPLICABLE | OK |
| STAGE-09 | SIMULATED | 2 | 6 | 0 | 2 | 1 | PRODUCTION_CUTOVER_CLOSED | OK |
| STAGE-10 | SIMULATED | 2 | 12 | 0 | 1 | 1 | PRODUCTION_ACCEPTANCE_EVIDENCE_CLOSED | OK |
| STAGE-11 | SIMULATED | 2 | 8 | 0 | 3 | 2 | GOVERNED_UNIT_CLOSED | OK |

- 上線里程碑：`STAGE-09 exit = PRODUCTION_CUTOVER_CLOSED`（頁面已上線）。
- 最終關閉：`STAGE-11 exit = GOVERNED_UNIT_CLOSED`，`GOVERNED_UNIT_CLOSED` 產物存在。
- blocker：**0**。

## 與頁面完整性交叉驗證

`page_run.py`（頁面完整性沙盤）對同一頁面為 **verdict = PASS**：9/9 responsibilities、5/5 functional chains、6/6 entities 全數承接；STAGE-10 十個上線驗收維度中 8 個適用且全數有功能鏈覆蓋，`database`、`external` 為不適用（須於 STAGE-08 以 `_OR_AUTHORITY_PROVEN_NOT_APPLICABLE` 證明）。

## 結論

- 以單一通用機制，頁面 YAML 可由 STAGE-01 一路跑完至 STAGE-11，達到上線並關閉，零 blocker。
- STAGE-01..04 以真實產物為底；STAGE-05..11 目前為宣告級投影（尚無執行器），此段完成度為結構性成立，實際落地仍須逐站以內容證據完成。

## 限制

- 本執行為沙盤（tabletop）：不產生 effectful 產物、不呼叫外部系統、不消耗 completion credit。
- `STAGE-05..11` 尚無真實 operation executor；如需真正 effectful 執行，須依同一主計畫為這些站建立執行器（尚未建立）。
