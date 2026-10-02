import unittest

from backend.app.models import Base


class SchemaDefinitionTests(unittest.TestCase):
    def test_required_relational_tables_are_registered(self) -> None:
        expected = {
            "users",
            "profiles",
            "roles",
            "user_roles",
            "skills",
            "user_skills",
            "organizations",
            "opportunity_categories",
            "opportunities",
            "opportunity_skills",
            "opportunity_sources",
            "opportunity_documents",
            "saved_opportunities",
            "applications",
            "notifications",
            "notification_preferences",
            "career_paths",
            "career_skills",
            "legal_topics",
            "legal_documents",
            "chat_sessions",
            "chat_messages",
            "knowledge_documents",
            "document_chunks",
            "source_fetch_logs",
            "ingestion_jobs",
            "recommendations",
            "audit_logs",
        }

        self.assertEqual(set(Base.metadata.tables), expected)

    def test_opportunity_table_covers_discovery_and_provenance_fields(self) -> None:
        columns = set(Base.metadata.tables["opportunities"].columns.keys())
        required = {
            "title",
            "organization_id",
            "category_id",
            "description",
            "opportunity_type",
            "qualification",
            "branch",
            "experience_required",
            "age_limit",
            "location",
            "work_mode",
            "salary_min",
            "salary_max",
            "stipend_amount",
            "application_fee",
            "opening_date",
            "closing_date",
            "exam_date",
            "result_date",
            "eligibility",
            "documents_required",
            "selection_process",
            "application_steps",
            "official_url",
            "source_url",
            "source_name",
            "source_type",
            "status",
            "published_at",
            "last_verified_at",
            "expires_at",
            "created_at",
            "updated_at",
        }

        self.assertTrue(required.issubset(columns))


if __name__ == "__main__":
    unittest.main()