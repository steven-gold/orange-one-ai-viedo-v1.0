# 頁面 YAML 全流程沙盤推演報告

- 日期：2026-09-30
- 受測頁面：`GLOBAL-HOME-SHELL-NAVIGATION`（governed unit）
- 沙盤器：`/tmp/opencode/stage_sandbox/page_run.py`（唯讀、非 effectful）
- 頁面定義：`/tmp/opencode/stage_sandbox/page_global_home.yaml`（由真實產物彙整）
- 推演問題：以此頁面 YAML 從 STAGE-01 跑到 STAGE-11，是否符合「完整頁面上線使用完整功能」

## 推演方法

1. 以真實產物為權威需求來源：`GOVERNED_UNIT_BASE_BLUEPRINT`（9 responsibilities）、`FUNCTIONAL_CHAIN_SPEC`（5 chains）、`GOVERNED_ENTITY_INVENTORY`（6 entities）。
2. 以 `STAGE_EXECUTION_MASTER_PLAN.yaml` 逐站走訪 STAGE-01..11，記錄每站的產物數與角色。
3. 以 STAGE-10 的 10 個上線驗收操作作為「完整功能」維度，逐維度檢查是否有功能鏈覆蓋。
4. 對頁面定義與真實產物做對稱比對，任何一邊缺項即 fail-closed。

## 正向結果（真實頁面）：verdict = PASS

- 走訪 11 站；9/9 responsibilities、5/5 functional chains、6/6 entities 全數承接。
- STAGE-01..04 為 RUNTIME（有真實產物）；STAGE-05..11 為 DECLARED（僅主計畫投影，尚無執行產物）。

| Stage | 類型 | 角色 | 產物數 |
|-------|------|------|--------|
| STAGE-01 | RUNTIME | responsibilities | 9 |
| STAGE-02 | RUNTIME | functional_contract | 25 |
| STAGE-03 | RUNTIME | visual_design | 9 |
| STAGE-04 | RUNTIME | foundation_freeze | 5 |
| STAGE-05 | DECLARED | implementation | 3 |
| STAGE-06 | DECLARED | verification | 4 |
| STAGE-07 | DECLARED | build | 3 |
| STAGE-08 | DECLARED | staging | 1 |
| STAGE-09 | DECLARED | production_cutover | 2 |
| STAGE-10 | DECLARED | production_acceptance | 1 |
| STAGE-11 | DECLARED | closure_operations | 3 |

### STAGE-10 上線驗收維度覆蓋

| 維度 | 驗收操作 | 適用 | 狀態 | 覆蓋功能鏈 |
|------|----------|------|------|------------|
| browser | `OP-43-PRODUCTION_BROWSER_ACCEPTANCE` | 是 | COVERED | FC-NAV-ITEM-OPEN, FC-NAV-VISIBILITY, FC-LANGUAGE-SELECT, FC-QUICK-STATUS, FC-WORKSPACE-SYNC |
| governed_unit | `OP-44-PRODUCTION_GOVERNED_UNIT_ACCEPTANCE` | 是 | COVERED | 全部 5 條 |
| control | `OP-45-PRODUCTION_CONTROL_ACCEPTANCE` | 是 | COVERED | FC-NAV-ITEM-OPEN, FC-NAV-VISIBILITY, FC-LANGUAGE-SELECT |
| database | `OP-46-PRODUCTION_DATABASE_ACCEPTANCE` | 否 | NOT_APPLICABLE_PENDING_AUTHORITY | - |
| effectful | `OP-47-PRODUCTION_EFFECTFUL_ACCEPTANCE` | 是 | COVERED | FC-NAV-ITEM-OPEN, FC-LANGUAGE-SELECT, FC-WORKSPACE-SYNC |
| external | `OP-48-EXTERNAL_INTEGRATION_ACCEPTANCE` | 否 | NOT_APPLICABLE_PENDING_AUTHORITY | - |
| async | `OP-49-ASYNC_RUNTIME_ACCEPTANCE` | 是 | COVERED | FC-QUICK-STATUS |
| visual_geometry | `PRODUCTION_VISUAL_GEOMETRY_ACCEPTANCE` | 是 | COVERED | 全部 5 條 |
| stale_render | `PRODUCTION_STALE_RENDER_ACCEPTANCE` | 是 | COVERED | FC-NAV-VISIBILITY, FC-LANGUAGE-SELECT |
| cross_unit | `PRODUCTION_CROSS_GOVERNED_UNIT_SLICE_ACCEPTANCE` | 是 | COVERED | FC-NAV-ITEM-OPEN, FC-WORKSPACE-SYNC |

`database` 與 `external` 依此 shell/導覽頁的自身宣告為不適用，須於 STAGE-08 進入時以 `_OR_AUTHORITY_PROVEN_NOT_APPLICABLE` 提供權威不適用證明，否則不得關閉。

## 反向注入測試（fail-closed）：verdict = FAIL

於頁面定義注入缺陷：移除 `FC-WORKSPACE-SYNC` 與 `WORKSPACE_MOUNT`。結果：

```
PAGE GLOBAL-HOME-SHELL-NAVIGATION  verdict=FAIL
[HIGH] PAGE-DEF: page definition DROPS required responsibility: WORKSPACE_MOUNT (present in artifacts)
[HIGH] PAGE-DEF: page definition DROPS required functional_chain: FC-WORKSPACE-SYNC (present in artifacts)
exit=1
```

沙盤能攔下「頁面定義缺件」，且對稱比對同時偵測「擅加未落地項」。

## 結論

- 以現行主計畫與真實頁面產物推演，`GLOBAL-HOME-SHELL-NAVIGATION` 可完整走完 STAGE-01..11，9 責任／5 功能鏈／6 實體全數承接，具備完整頁面上線使用所需的功能覆蓋。
- 10 個上線驗收維度中，8 個適用且全數有功能鏈覆蓋；2 個不適用維度須補權威不適用證明（STAGE-08 閘門既有機制）。
- STAGE-05..11 尚無執行產物，該段為宣告級投影；實際關閉仍需逐站以內容證據落地。

## 限制

- 功能鏈→驗收維度映射為 MODELED（依鏈語意推得），非頁面事實；如需定案，須以 STAGE-06/10 的實際驗收矩陣覆核。
- 沙盤為宣告級靜態推演，不執行、不產生 effectful 產物、不消耗 completion credit。
