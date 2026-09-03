import type { DashboardReadModel } from "@/domain/dashboard/readModelContract";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";

export const CONTROLLED_DASHBOARD_TEST_METADATA = Object.freeze({
  data_classification: "TEST_ONLY" as const,
  synthetic: true,
  test_dataset_id: "TEST-WB-01",
  test_run_id: "TEST-RUN-WB-01-CONTROLLED",
  created_for_validation: true,
  production_eligible: false,
});

export function isControlledDashboardServerTestMode(): boolean {
  return isControlledTestMode();
}

export function readControlledDashboardTestProjection(correlation_id: string): DashboardReadModel {
  return {
    read_model_version: "TEST_ONLY-WB01-RM-001",
    correlation_id,
    company_project_count: { company_project_count: { value: 8 } },
    company_running_project_count: { company_running_project_count: { value: 3 } },
    company_pending_action_count: { company_pending_action_count: { value: 5 } },
    company_pending_review_count: { company_pending_review_count: { value: 2 } },
    company_completed_project_count: { company_completed_project_count: { value: 4 } },
    company_average_progress: { company_average_progress: { value: 67 } },
    project_progress_overview: {
      project_progress_overview: {
        projects: [{
          project_id: "TEST-PROJECT-001",
          display_name: "[TEST] ORANGE ONE Demo Project",
          status: "RUNNING",
          progress_percentage: 67,
          topics: [{
            topic_id: "TEST-TOPIC-001",
            display_name: "[TEST] Topic Alpha",
            status: "RUNNING",
            progress_percentage: 72,
            total_operation_time_seconds: 93784,
            tasks: [{ task_id: "TEST-TASK-001", display_name: "[TEST] Task One", task_state: "RUNNING" }],
          }],
        }],
      },
    },
    company_progress_summary: {
      company_progress_summary: {
        overall_progress_percentage: 67,
        running_count: 3,
        pending_action_count: 5,
        pending_review_count: 2,
        completed_count: 4,
      },
    },
    production_summary: {
      production_summary: {
        units: [{ unit_key: "TEST-UNIT-EDIT", unit_label: "[TEST] Editing", state: "RUNNING", running_count: 2, pending_count: 1, review_count: 1, completed_count: 3 }],
      },
    },
    notifications: { notifications: { items: [{ notification_id: "TEST-NOTIFY-001", title: "[TEST] Review required", category: "QA", created_at: "2026-09-02T12:00:00Z", read_state: "UNREAD" }] } },
    company_announcements: { company_announcements: { items: [{ announcement_id: "TEST-ANN-001", title: "[TEST] Company announcement", summary: "Controlled validation announcement", published_at: "2026-09-02T11:00:00Z" }] } },
    industry_news: { industry_news: { items: [{ news_id: "TEST-NEWS-001", title: "[TEST] AI industry update", source_name: "[TEST] Source", summary: "Controlled validation news summary", published_at: "2026-09-02T10:00:00Z" }] } },
    system_status_summary: { system_status_summary: { overall_status: "[TEST] OPERATIONAL", summary: "Controlled validation status", checked_at: "2026-09-02T12:30:00Z" } },
    recent_completions: { recent_completions: { items: [{ completion_id: "TEST-COMPLETE-001", project_label: "[TEST] Demo Project", topic_label: "[TEST] Topic Alpha", item_label: "[TEST] Output One", completion_kind: "VIDEO", completed_at: "2026-09-02T09:00:00Z" }] } },
  };
}
