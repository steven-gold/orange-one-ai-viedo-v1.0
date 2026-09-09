-- ACPOS migration 0043: remove the historical TEST_ONLY production lineage fixture.
-- This is a governed cleanup only. It creates no business data and is a safe no-op when the fixture is absent.

DO $$
DECLARE
  v_project uuid;
  v_project_version uuid;
  v_mother_lock uuid;
  v_mother_review uuid;
  v_topic uuid;
  v_topic_version uuid;
  v_contract uuid;
  v_goal uuid;
  v_output_contract uuid;
  v_topic_blueprint uuid;
  v_master_blueprint uuid;
  v_blueprint_version uuid;
  v_child_lock uuid;
  v_child_review uuid;
  v_work_package uuid;
  v_dag_snapshot uuid;
  v_dag_node uuid;
  v_task_template uuid;
  v_task uuid;
  v_count integer;
BEGIN
  SELECT project_id,active_version_id
    INTO v_project,v_project_version
  FROM public.projects
  WHERE project_code='TEST-PRJ-001';

  IF v_project IS NULL THEN
    RETURN;
  END IF;

  SELECT count(*) INTO v_count FROM public.projects WHERE project_code='TEST-PRJ-001';
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_PROJECT_CARDINALITY_INVALID'; END IF;

  SELECT count(*) INTO v_count FROM public.topics WHERE project_id=v_project;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_TOPIC_CARDINALITY_INVALID'; END IF;
  SELECT topic_id,active_version_id,mother_lock_id INTO v_topic,v_topic_version,v_mother_lock
  FROM public.topics WHERE project_id=v_project;

  SELECT lock_review_id INTO v_mother_review
  FROM public.mother_locks
  WHERE mother_lock_id=v_mother_lock AND project_id=v_project AND project_version_id=v_project_version;
  IF v_mother_review IS NULL THEN RAISE EXCEPTION 'CLEANUP0043_TEST_MOTHER_LOCK_LINEAGE_INVALID'; END IF;

  SELECT count(*) INTO v_count FROM public.topic_production_contracts pc
  JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
  WHERE tv.topic_id=v_topic;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_CONTRACT_CARDINALITY_INVALID'; END IF;
  SELECT pc.topic_production_contract_id INTO v_contract
  FROM public.topic_production_contracts pc
  JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
  WHERE tv.topic_id=v_topic;

  SELECT count(*) INTO v_count FROM public.topic_production_goals WHERE topic_production_contract_id=v_contract;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_GOAL_CARDINALITY_INVALID'; END IF;
  SELECT production_goal_id,output_contract_id INTO v_goal,v_output_contract
  FROM public.topic_production_goals
  WHERE topic_production_contract_id=v_contract;

  SELECT count(*) INTO v_count FROM public.topic_blueprints WHERE topic_production_contract_id=v_contract;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_BLUEPRINT_CARDINALITY_INVALID'; END IF;
  SELECT topic_blueprint_id,master_blueprint_id
    INTO v_topic_blueprint,v_master_blueprint
  FROM public.topic_blueprints
  WHERE topic_production_contract_id=v_contract;

  SELECT count(*) INTO v_count
  FROM public.blueprint_versions
  WHERE topic_blueprint_id=v_topic_blueprint;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_BLUEPRINT_VERSION_CARDINALITY_INVALID'; END IF;
  SELECT blueprint_version_id INTO v_blueprint_version
  FROM public.blueprint_versions
  WHERE topic_blueprint_id=v_topic_blueprint
    AND blueprint_document->>'purpose'='TEST_ONLY';
  IF v_blueprint_version IS NULL THEN
    RAISE EXCEPTION 'CLEANUP0043_TEST_BLUEPRINT_VERSION_MARKER_INVALID';
  END IF;

  SELECT count(*) INTO v_count
  FROM public.child_locks
  WHERE topic_id=v_topic AND topic_production_contract_id=v_contract AND blueprint_version_id=v_blueprint_version;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_CHILD_LOCK_CARDINALITY_INVALID'; END IF;
  SELECT child_lock_id,lock_review_id INTO v_child_lock,v_child_review
  FROM public.child_locks
  WHERE topic_id=v_topic AND topic_production_contract_id=v_contract AND blueprint_version_id=v_blueprint_version;

  SELECT count(*) INTO v_count FROM public.work_packages WHERE child_lock_id=v_child_lock;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_WORK_PACKAGE_CARDINALITY_INVALID'; END IF;
  SELECT work_package_id,dag_snapshot_id INTO v_work_package,v_dag_snapshot
  FROM public.work_packages
  WHERE child_lock_id=v_child_lock
    AND input_snapshot->>'purpose'='TEST_ONLY';

  IF v_work_package IS NULL OR v_dag_snapshot IS NULL THEN
    RAISE EXCEPTION 'CLEANUP0043_TEST_WORK_PACKAGE_MARKER_INVALID';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.dag_snapshots
    WHERE dag_snapshot_id=v_dag_snapshot
      AND work_package_id=v_work_package
      AND compiler_version='TEST-1'
      AND snapshot_document->>'purpose'='TEST_ONLY'
  ) THEN RAISE EXCEPTION 'CLEANUP0043_TEST_DAG_MARKER_INVALID'; END IF;

  SELECT count(*) INTO v_count FROM public.dag_nodes WHERE dag_snapshot_id=v_dag_snapshot;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_DAG_NODE_CARDINALITY_INVALID'; END IF;
  SELECT dag_node_id,task_template_id INTO v_dag_node,v_task_template
  FROM public.dag_nodes
  WHERE dag_snapshot_id=v_dag_snapshot
    AND node_contract->>'purpose'='TEST_ONLY';
  IF v_dag_node IS NULL THEN RAISE EXCEPTION 'CLEANUP0043_TEST_DAG_NODE_MARKER_INVALID'; END IF;

  SELECT count(*) INTO v_count FROM public.department_tasks WHERE dag_node_id=v_dag_node;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0043_TEST_TASK_CARDINALITY_INVALID'; END IF;
  SELECT task_id INTO v_task FROM public.department_tasks WHERE dag_node_id=v_dag_node;

  IF NOT EXISTS (SELECT 1 FROM public.task_templates WHERE task_template_id=v_task_template AND template_key='TEST-TPL-VIDEO') THEN
    RAISE EXCEPTION 'CLEANUP0043_TEST_TEMPLATE_MARKER_INVALID';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.topic_production_goals WHERE production_goal_id=v_goal AND goal_key='TEST-GOAL-001') THEN
    RAISE EXCEPTION 'CLEANUP0043_TEST_GOAL_MARKER_INVALID';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.output_contracts WHERE output_contract_id=v_output_contract AND schema_key='TEST-OUTPUT') THEN
    RAISE EXCEPTION 'CLEANUP0043_TEST_OUTPUT_CONTRACT_MARKER_INVALID';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM public.lock_reviews
    WHERE lock_review_id=v_mother_review
      AND criteria_version_id IS NULL
      AND evidence->>'purpose'='TEST_ONLY'
      AND reviewer_path='[]'::jsonb
  ) THEN RAISE EXCEPTION 'CLEANUP0043_TEST_MOTHER_REVIEW_MARKER_INVALID'; END IF;
  IF NOT EXISTS (
    SELECT 1 FROM public.lock_reviews
    WHERE lock_review_id=v_child_review
      AND criteria_version_id IS NULL
      AND evidence->>'purpose'='TEST_ONLY'
      AND reviewer_path='[]'::jsonb
  ) THEN RAISE EXCEPTION 'CLEANUP0043_TEST_CHILD_REVIEW_MARKER_INVALID'; END IF;

  IF (SELECT count(*) FROM public.dag_nodes WHERE task_template_id=v_task_template)<>1 THEN
    RAISE EXCEPTION 'CLEANUP0043_TEST_TEMPLATE_SHARED';
  END IF;
  IF (SELECT count(*) FROM public.topic_production_goals WHERE output_contract_id=v_output_contract)<>1 THEN
    RAISE EXCEPTION 'CLEANUP0043_TEST_OUTPUT_CONTRACT_SHARED';
  END IF;
  IF (SELECT count(*) FROM public.topic_blueprints WHERE master_blueprint_id=v_master_blueprint)<>1 THEN
    RAISE EXCEPTION 'CLEANUP0043_TEST_MASTER_BLUEPRINT_SHARED';
  END IF;

  -- Break circular active-version pointers first.
  UPDATE public.work_packages SET dag_snapshot_id=NULL WHERE work_package_id=v_work_package;
  UPDATE public.topic_blueprints SET active_version_id=NULL WHERE topic_blueprint_id=v_topic_blueprint;
  UPDATE public.topics SET active_version_id=NULL WHERE topic_id=v_topic;
  UPDATE public.projects SET active_version_id=NULL WHERE project_id=v_project;

  -- Downstream execution chain.
  DELETE FROM public.dag_edges WHERE dag_snapshot_id=v_dag_snapshot OR from_node_id=v_dag_node OR to_node_id=v_dag_node;
  DELETE FROM public.department_tasks WHERE task_id=v_task;
  DELETE FROM public.dag_nodes WHERE dag_node_id=v_dag_node;
  DELETE FROM public.dag_snapshots WHERE dag_snapshot_id=v_dag_snapshot;
  DELETE FROM public.work_packages WHERE work_package_id=v_work_package;
  DELETE FROM public.task_templates WHERE task_template_id=v_task_template;

  -- Child lock / blueprint / production contract chain.
  DELETE FROM public.child_locks WHERE child_lock_id=v_child_lock;
  DELETE FROM public.blueprint_versions WHERE blueprint_version_id=v_blueprint_version;
  DELETE FROM public.topic_blueprints WHERE topic_blueprint_id=v_topic_blueprint;
  DELETE FROM public.master_blueprints WHERE master_blueprint_id=v_master_blueprint;
  DELETE FROM public.topic_production_goals WHERE production_goal_id=v_goal;
  DELETE FROM public.output_contracts WHERE output_contract_id=v_output_contract;
  DELETE FROM public.topic_production_contracts WHERE topic_production_contract_id=v_contract;
  DELETE FROM public.topic_versions WHERE topic_version_id=v_topic_version;
  DELETE FROM public.topics WHERE topic_id=v_topic;

  -- Mother lock / reviews / project chain.
  DELETE FROM public.mother_locks WHERE mother_lock_id=v_mother_lock;
  DELETE FROM public.lock_reviews WHERE lock_review_id IN (v_mother_review,v_child_review);
  DELETE FROM public.project_versions WHERE project_version_id=v_project_version;
  DELETE FROM public.projects WHERE project_id=v_project;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0043_production_test_only_lineage_cleanup',
  '569f0130d2c10b6cb75060a7269b3c82c7bee7682edf8068566a5be442efce2b',
  'migration-runner',
  'CR-RUNTIME-0043'
)
ON CONFLICT(migration_id) DO NOTHING;
