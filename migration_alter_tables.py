# migration_alter_tables.py
# Run this ONCE after creating new flow tables
# Purpose: Add new columns to existing tables for flow support

from db import engine

print("=" * 70)
print("DATABASE MIGRATION: Adding Flow Support to Existing Tables")
print("=" * 70)
print("")
print("This will add new columns to:")
print("  - questionnaire_instances")
print("  - questionnaire_answers")
print("  - questionnaire_assignments")
print("")
print("⚠️  Make sure you have a backup before proceeding!")
print("")

response = input("Continue? (yes/no): ")
if response.lower() != "yes":
    print("Migration cancelled.")
    exit()

print("")
print("Starting migration...")
print("")

sql_statements = [
    # questionnaire_instances - Add flow support
    ("ALTER TABLE questionnaire_instances ADD COLUMN IF NOT EXISTS flow_id INTEGER REFERENCES questionnaire_flows(id);", "Add flow_id to instances"),
    ("ALTER TABLE questionnaire_instances ADD COLUMN IF NOT EXISTS flow_version INTEGER;", "Add flow_version to instances"),
    ("ALTER TABLE questionnaire_instances ADD COLUMN IF NOT EXISTS current_node_key VARCHAR(50);", "Add current_node_key to instances"),
    ("ALTER TABLE questionnaire_instances ADD COLUMN IF NOT EXISTS navigation_path JSONB;", "Add navigation_path to instances"),
    ("ALTER TABLE questionnaire_instances ADD COLUMN IF NOT EXISTS final_severity VARCHAR(10);", "Add final_severity to instances"),
    ("ALTER TABLE questionnaire_instances ADD COLUMN IF NOT EXISTS total_news2_score INTEGER DEFAULT 0;", "Add total_news2_score to instances"),
    ("ALTER TABLE questionnaire_instances ADD COLUMN IF NOT EXISTS total_seriousness_points INTEGER DEFAULT 0;", "Add total_seriousness_points to instances"),
    ("ALTER TABLE questionnaire_instances ADD COLUMN IF NOT EXISTS alert_events JSONB;", "Add alert_events to instances"),
    
    # questionnaire_answers - Add flow support
    ("ALTER TABLE questionnaire_answers ADD COLUMN IF NOT EXISTS node_key VARCHAR(50);", "Add node_key to answers"),
    ("ALTER TABLE questionnaire_answers ADD COLUMN IF NOT EXISTS flow_node_id INTEGER REFERENCES flow_nodes(id);", "Add flow_node_id to answers"),
    ("ALTER TABLE questionnaire_answers ADD COLUMN IF NOT EXISTS option_severity VARCHAR(10);", "Add option_severity to answers"),
    ("ALTER TABLE questionnaire_answers ADD COLUMN IF NOT EXISTS option_news2_score INTEGER DEFAULT 0;", "Add option_news2_score to answers"),
    ("ALTER TABLE questionnaire_answers ADD COLUMN IF NOT EXISTS option_seriousness_points INTEGER DEFAULT 0;", "Add option_seriousness_points to answers"),
    ("ALTER TABLE questionnaire_answers ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP;", "Add acknowledged_at to answers"),
    
    # questionnaire_assignments - Support both templates and flows
    ("ALTER TABLE questionnaire_assignments ADD COLUMN IF NOT EXISTS flow_id INTEGER REFERENCES questionnaire_flows(id);", "Add flow_id to assignments"),
    ("ALTER TABLE questionnaire_assignments ALTER COLUMN template_id DROP NOT NULL;", "Make template_id nullable"),
    
    # Indexes for performance
    ("CREATE INDEX IF NOT EXISTS idx_instance_flow ON questionnaire_instances(flow_id);", "Index: instance flow_id"),
    ("CREATE INDEX IF NOT EXISTS idx_instance_node ON questionnaire_instances(current_node_key);", "Index: instance current_node_key"),
    ("CREATE INDEX IF NOT EXISTS idx_answer_node_key ON questionnaire_answers(node_key);", "Index: answer node_key"),
    ("CREATE INDEX IF NOT EXISTS idx_answer_flow_node ON questionnaire_answers(flow_node_id);", "Index: answer flow_node_id"),
    ("CREATE INDEX IF NOT EXISTS idx_assignment_flow ON questionnaire_assignments(flow_id);", "Index: assignment flow_id"),
]

success_count = 0
error_count = 0
errors = []

with engine.connect() as conn:
    for sql, description in sql_statements:
        try:
            conn.execute(sql)
            print(f"✓ {description}")
            success_count += 1
        except Exception as e:
            print(f"✗ {description} - ERROR: {str(e)}")
            errors.append((description, str(e)))
            error_count += 1
    
    conn.commit()

print("")
print("=" * 70)
print("MIGRATION SUMMARY")
print("=" * 70)
print(f"Successful: {success_count}")
print(f"Errors: {error_count}")
print("")

if errors:
    print("⚠️  Errors encountered:")
    for desc, err in errors:
        print(f"  - {desc}: {err}")
    print("")
    print("Note: 'column already exists' errors are safe to ignore.")
else:
    print("✅ All migrations completed successfully!")

print("")
print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("1. Restart your server: uvicorn main:app --reload")
print("2. Test flow creation: curl -X POST http://localhost:8000/flows/demo/seed")
print("3. Check API docs: http://localhost:8000/docs")
print("")