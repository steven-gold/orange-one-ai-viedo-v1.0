import type { DbNormalizedProjection } from "@/domain/database/dbClientPort";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";

const TEST_METADATA = {
  data_classification: "TEST_ONLY",
  synthetic: true,
  test_dataset_id: "TEST-DB-01",
  test_run_id: "TEST-RUN-DB-CONTROLLED-01",
  created_for_validation: true,
  production_eligible: false,
} as const;

const item=(ref:string,label:string,meta?:Record<string,unknown>)=>({ref,label,meta});
export function isControlledDbServerTestMode(){return isControlledTestMode();}
export function readControlledDbTestProjection():DbNormalizedProjection&{test_metadata:typeof TEST_METADATA}{
  return {
    page_state:"READ_ONLY",
    values:{
      "DB-01-FLD-ENV":"TEST_ONLY / controlled database read model",
      "DB-01-FLD-SCHEMA-HEAD":"TEST-SCHEMA-HEAD-001 · checksum TEST-SHA256-SCHEMA-001",
      "DB-01-FLD-MIGRATION-HEAD":"TEST-MIGRATION-001 · checksum TEST-SHA256-MIGRATION-001",
      "DB-01-FLD-SCOPE":"TEST-PROJECT-001 · exact authorized scope",
      "DB-01-FLD-HEALTH":"READ_ONLY · controlled integrity source available",
      "DB-01-FLD-ENTITY":"ProjectStructureVersion",
      "DB-01-FLD-TABLE":"project_structure_versions",
      "DB-01-FLD-OWNER":"Canonical Project / Version owner",
      "DB-01-FLD-CLASSIFICATION":"TEST_ONLY · internal",
      "DB-01-FLD-PK":"project_structure_version_id",
      "DB-01-FLD-VERSION-RULE":"New immutable version; no overwrite; exact refs only",
      "DB-01-FLD-REF-INTEGRITY":"PASS · TEST_ONLY exact refs",
      "DB-01-FLD-ORPHAN":"0 TEST_ONLY orphan findings in controlled dataset",
      "DB-01-FLD-IMMUTABLE":"PASS · historical versions preserved",
      "DB-01-FLD-TRACE-COMPLETE":"PASS · controlled lineage complete",
      "DB-01-FLD-MIGRATION-INTEGRITY":"PASS · non-zero checksum recorded",
      "DB-01-FLD-FINDING-REASON":"TEST_ONLY orphan reference example; no silent repair",
      "DB-01-FLD-FINDING-AFFECTED":"TEST-PROVIDER-JOB-ORPHAN-001",
      "DB-01-FLD-FINDING-EVIDENCE":"TEST-EVIDENCE-DB-001",
      "DB-01-FLD-FINDING-OWNER":"System Lifecycle / owning Domain Service",
      "DB-01-FLD-PAGE-STATE":"READ_ONLY",
      "DB-01-FLD-CHANGE-OWNER":"System Lifecycle / Change Management / governed Domain Service",
    },
    lists:{
      "DB-01-LIST-ENTITIES":[
        item("TEST-PROJECT-001","Project · TEST-PROJECT-001",{domain:"CANON",entity_type:"Project"}),
        item("TEST-MOTHER-VERSION-001","Mother Structure Version · TEST-MOTHER-VERSION-001",{domain:"CANON",entity_type:"Version"}),
        item("TEST-TOPIC-001","Production Topic · TEST-TOPIC-001",{domain:"TOPIC_PRODUCTION",entity_type:"Topic"}),
        item("TEST-CHILD-BLUEPRINT-001","Child Blueprint Version · TEST-CHILD-BLUEPRINT-001",{domain:"TOPIC_PRODUCTION",entity_type:"Version"}),
        item("TEST-ASSET-VERSION-001","Asset Output Version · TEST-ASSET-VERSION-001",{domain:"RUNTIME",entity_type:"Output"}),
        item("TEST-QA-REVIEW-001","QA Review Run · TEST-QA-REVIEW-001",{domain:"GOVERNANCE",entity_type:"Review"}),
      ],
      "DB-01-LIST-RELATIONS":[
        item("TEST-REL-PROJECT-MOTHER","Project → Mother Structure Version"),
        item("TEST-REL-TOPIC-CHILD","Topic → Child Blueprint Version"),
        item("TEST-REL-OUTPUT-QA","Output Version → QA Review Run"),
      ],
      "DB-01-LIST-FINDINGS":[item("TEST-FINDING-DB-001","TEST_ONLY · orphan reference finding",{finding_type:"ORPHAN_REF"})],
    },
    tables:{
      "DB-01-TBL-COLUMNS":[
        {ref:"TEST-COL-001",column:"project_structure_version_id",type:"uuid",key:"PK",nullable:false},
        {ref:"TEST-COL-002",column:"project_id",type:"uuid",key:"FK",nullable:false},
        {ref:"TEST-COL-003",column:"source_checksum",type:"text",nullable:false},
      ],
      "DB-01-TBL-CONSTRAINTS":[
        {ref:"TEST-CONSTRAINT-001",kind:"FK",rule:"project_id exact registered ref"},
        {ref:"TEST-CONSTRAINT-002",kind:"IMMUTABLE",rule:"published source refs cannot change"},
      ],
      "DB-01-TBL-MIGRATIONS":[
        {ref:"TEST-MIGRATION-001",checksum:"TEST-SHA256-MIGRATION-001",approval_ref:"TEST-APPROVAL-001",dependency_state:"SATISFIED",status:"APPLIED",applied_by:"TEST_ONLY",applied_at:"2026-08-29T09:00:00Z"},
      ],
    },
    gates:{
      "DB-01-GATE-PAGE":true,
      "DB-01-GATE-CONTEXT":true,
      "DB-01-GATE-ENTITY":true,
      "DB-01-GATE-SCHEMA":true,
      "DB-01-GATE-RELATION":true,
      "DB-01-GATE-TRACE":true,
      "DB-01-GATE-MIGRATION":true,
      "DB-01-GATE-INTEGRITY":true,
      "DB-01-GATE-AUDIT":true,
    },
    filters:{
      "DB-01-SEL-DOMAIN":[item("CANON","CANON"),item("TOPIC_PRODUCTION","TOPIC_PRODUCTION"),item("RUNTIME","RUNTIME"),item("GOVERNANCE","GOVERNANCE"),item("SYSTEM","SYSTEM")],
      "DB-01-SEL-ENTITY-TYPE":[item("Project","Project"),item("Version","Version"),item("Topic","Topic"),item("Output","Output"),item("Review","Review")],
      "DB-01-SEL-TRACE-TYPE":[item("Task","Task"),item("Job","Job"),item("Asset","Asset"),item("Review","Review"),item("Finding","Finding"),item("Decision","Decision"),item("Release","Release")],
      "DB-01-SEL-FINDING-TYPE":[item("ORPHAN_REF","Orphan Reference"),item("VERSION_CONFLICT","Version Conflict"),item("MIGRATION_CHECKSUM","Migration Checksum")],
    },
    graph:[
      item("TEST-PROJECT-001","Project"),item("TEST-MOTHER-VERSION-001","Mother Version"),item("TEST-TOPIC-001","Topic"),item("TEST-CHILD-BLUEPRINT-001","Child Blueprint"),
    ],
    trace:[
      item("TEST-PROJECT-001","Project"),item("TEST-MOTHER-VERSION-001","Mother Structure Version"),item("TEST-TOPIC-001","Topic"),item("TEST-CHILD-BLUEPRINT-001","Child Blueprint Version"),item("TEST-ASSET-VERSION-001","Output Version"),item("TEST-QA-REVIEW-001","QA Review"),
    ],
    audit:[item("TEST-AUDIT-DB-001","TEST_ONLY · read-model query · correlation TEST-CORR-DB-001")],
    source_sync:"TEST_ONLY · controlled read model · no production database binding",
    test_metadata:TEST_METADATA,
  };
}
