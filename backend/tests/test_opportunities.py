import unittest
from datetime import date, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.auth.clerk import ClerkIdentity, get_current_clerk_identity
from backend.app.db.session import engine, get_db
from backend.app.main import app
from backend.app.models.identity import Role, User, UserRole
from backend.app.models.opportunity import Opportunity


class OpportunityApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session_factory = sessionmaker(
            bind=self.connection,
            autoflush=False,
            autocommit=False,
            join_transaction_mode="create_savepoint",
        )
        self.previous_overrides = app.dependency_overrides.copy()
        self.identity = {"user_id": "clerk_opportunity_user"}
        self.email_patcher = patch(
            "backend.app.auth.local_user.get_verified_clerk_email",
            side_effect=lambda clerk_user_id: f"{clerk_user_id}@example.test",
        )
        self.email_patcher.start()

        def override_database():
            session = self.session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_database
        app.dependency_overrides[get_current_clerk_identity] = lambda: ClerkIdentity(
            user_id=self.identity["user_id"]
        )
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.email_patcher.stop()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        if self.transaction.is_active:
            self.transaction.rollback()
        self.connection.close()

    def grant_admin(self) -> None:
        with self.session_factory() as db:
            user = db.scalar(
                select(User).where(
                    User.auth_provider_user_id == self.identity["user_id"]
                )
            )
            if user is None:
                user = User(
                    email=f"{self.identity['user_id']}@example.test",
                    auth_provider="clerk",
                    auth_provider_user_id=self.identity["user_id"],
                    is_active=True,
                    is_verified=True,
                )
                db.add(user)
            role = db.scalar(select(Role).where(Role.name == "ADMIN"))
            if role is None:
                role = Role(name="ADMIN", description="Test-only administrator")
                db.add(role)
            db.flush()
            if db.get(UserRole, (user.id, role.id)) is None:
                db.add(UserRole(user_id=user.id, role_id=role.id))
            db.commit()

    def opportunity_payload(
        self,
        *,
        suffix: str,
        title: str,
        opportunity_type: str,
        location: str,
        work_mode: str,
        stipend: int,
        deadline_days: int,
    ) -> dict:
        host = f"{suffix}.example"
        return {
            "title": title,
            "description": "PhaseFiveRegressionNeedle. Verified-source API test record.",
            "organization": {
                "name": f"Organization {suffix}",
                "website_url": f"https://{host}",
                "official_domain": host,
                "location": location,
            },
            "category": {
                "name": "Phase Five Test Programs",
                "slug": "phase-five-test-programs",
            },
            "opportunity_type": opportunity_type,
            "qualification": "B.Tech",
            "branch": "Computer Science",
            "experience_required": "Fresher, 0 years",
            "age_limit": "18-30",
            "location": location,
            "work_mode": work_mode,
            "stipend_amount": stipend,
            "compensation_currency": "INR",
            "closing_date": (date.today() + timedelta(days=deadline_days)).isoformat(),
            "eligibility": {"exam_type": "national"},
            "skills": [
                {"name": "Python", "is_required": True},
                {"name": "SQL", "is_required": False},
                {"name": "python", "is_required": False},
            ],
            "documents_required": ["Resume"],
            "selection_process": ["Application review"],
            "application_steps": ["Read the official notice"],
            "official_url": f"https://{host}/apply",
            "source_url": f"https://{host}/official-notice",
            "source_name": "Official test notice",
            "source_type": "OFFICIAL_PORTAL",
            "status": "OPEN",
            "publish_after_review": True,
        }

    def test_public_search_is_paginated_and_filters_source_verified_records(self) -> None:
        self.grant_admin()
        first_payload = self.opportunity_payload(
            suffix="phase-five-first",
            title="Data Fellowship for Graduates",
            opportunity_type="FELLOWSHIP",
            location="Pune",
            work_mode="hybrid",
            stipend=8000,
            deadline_days=12,
        )
        second_payload = self.opportunity_payload(
            suffix="phase-five-second",
            title="Remote Internship for Analysts",
            opportunity_type="INTERNSHIP",
            location="Hyderabad",
            work_mode="remote",
            stipend=18000,
            deadline_days=24,
        )

        first = self.client.post("/api/v1/admin/opportunities", json=first_payload)
        second = self.client.post("/api/v1/admin/opportunities", json=second_payload)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        first_saved = first.json()
        second_saved = second.json()
        self.assertFalse(first_saved["is_stale"])
        self.assertTrue(first_saved["last_verified_at"])
        self.assertEqual(
            [
                (item["name"].casefold(), item["is_required"])
                for item in first_saved["skills"]
            ],
            [("python", True), ("sql", False)],
        )

        page_one = self.client.get(
            "/api/v1/search",
            params={
                "q": "PhaseFiveRegressionNeedle",
                "sort": "deadline",
                "page": 1,
                "page_size": 1,
            },
        )
        page_two = self.client.get(
            "/api/v1/opportunities",
            params={
                "q": "PhaseFiveRegressionNeedle",
                "sort": "deadline",
                "page": 2,
                "page_size": 1,
            },
        )
        self.assertEqual(page_one.status_code, 200, page_one.text)
        self.assertEqual(page_two.status_code, 200, page_two.text)
        self.assertEqual(page_one.json()["total"], 2)
        self.assertEqual(page_one.json()["page_count"], 2)
        self.assertNotEqual(
            page_one.json()["items"][0]["id"],
            page_two.json()["items"][0]["id"],
        )

        filtered = self.client.get(
            "/api/v1/opportunities",
            params={
                "q": "PhaseFiveRegressionNeedle",
                "opportunity_type": "internship",
                "location": "hyderabad",
                "work_mode": "remote",
                "min_compensation": 10000,
                "compensation_currency": "INR",
                "skill": "python",
                "category": "phase-five-test-programs",
            },
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        self.assertEqual(filtered.json()["total"], 1)
        self.assertEqual(filtered.json()["items"][0]["id"], second_saved["id"])

        category_list = self.client.get("/api/v1/opportunities/categories")
        self.assertEqual(category_list.status_code, 200, category_list.text)
        self.assertIn(
            "phase-five-test-programs",
            {category["slug"] for category in category_list.json()},
        )

        detail = self.client.get(f"/api/v1/opportunities/{first_saved['id']}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["title"], first_payload["title"])

    def test_admin_crud_requires_role_and_unpublishes_on_update(self) -> None:
        denied = self.client.get("/api/v1/admin/opportunities")
        self.assertEqual(denied.status_code, 403)
        denied_create = self.client.post(
            "/api/v1/admin/opportunities",
            json=self.opportunity_payload(
                suffix="unauthorized",
                title="Must not be saved",
                opportunity_type="INTERNSHIP",
                location="Pune",
                work_mode="remote",
                stipend=1000,
                deadline_days=15,
            ),
        )
        self.assertEqual(denied_create.status_code, 403)

        self.identity["user_id"] = "clerk_opportunity_admin"
        self.grant_admin()
        payload = self.opportunity_payload(
            suffix="phase-five-admin",
            title="Admin Managed Opportunity",
            opportunity_type="SCHOLARSHIP",
            location="Mumbai",
            work_mode="on-site",
            stipend=5000,
            deadline_days=18,
        )
        created = self.client.post("/api/v1/admin/opportunities", json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        opportunity_id = created.json()["id"]

        updated_payload = {**payload, "title": "Updated Admin Listing", "publish_after_review": False}
        updated = self.client.put(
            f"/api/v1/admin/opportunities/{opportunity_id}",
            json=updated_payload,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["title"], "Updated Admin Listing")
        self.assertIsNone(updated.json()["published_at"])
        self.assertIsNone(updated.json()["last_verified_at"])

        hidden_from_public = self.client.get(
            f"/api/v1/opportunities/{opportunity_id}"
        )
        self.assertEqual(hidden_from_public.status_code, 404)

        archived = self.client.delete(
            f"/api/v1/admin/opportunities/{opportunity_id}"
        )
        self.assertEqual(archived.status_code, 204)
        with self.session_factory() as db:
            saved = db.scalar(
                select(Opportunity).where(Opportunity.id == opportunity_id)
            )
            self.assertIsNotNone(saved)
            self.assertEqual(saved.status, "CANCELLED")

    def test_saving_is_authenticated_idempotent_and_user_scoped(self) -> None:
        self.grant_admin()
        published_payload = self.opportunity_payload(
            suffix="phase-five-saved",
            title="Saved Opportunity Scope Test",
            opportunity_type="INTERNSHIP",
            location="Chennai",
            work_mode="remote",
            stipend=12000,
            deadline_days=20,
        )
        draft_payload = self.opportunity_payload(
            suffix="phase-five-draft",
            title="Unpublished Opportunity Scope Test",
            opportunity_type="INTERNSHIP",
            location="Chennai",
            work_mode="remote",
            stipend=12000,
            deadline_days=20,
        )
        draft_payload["publish_after_review"] = False
        published = self.client.post(
            "/api/v1/admin/opportunities", json=published_payload
        )
        draft = self.client.post("/api/v1/admin/opportunities", json=draft_payload)
        self.assertEqual(published.status_code, 201, published.text)
        self.assertEqual(draft.status_code, 201, draft.text)
        published_id = published.json()["id"]
        draft_id = draft.json()["id"]

        self.identity["user_id"] = "clerk_saved_opportunity_alpha"
        first_save = self.client.post(
            f"/api/v1/opportunities/{published_id}/save"
        )
        repeated_save = self.client.post(
            f"/api/v1/opportunities/{published_id}/save"
        )
        self.assertEqual(first_save.status_code, 200, first_save.text)
        self.assertEqual(repeated_save.status_code, 200, repeated_save.text)
        self.assertTrue(first_save.json()["saved"])
        self.assertTrue(repeated_save.json()["saved"])
        denied_draft_save = self.client.post(
            f"/api/v1/opportunities/{draft_id}/save"
        )
        self.assertEqual(denied_draft_save.status_code, 404)

        alpha_saved = self.client.get("/api/v1/opportunities/saved")
        self.assertEqual(alpha_saved.status_code, 200, alpha_saved.text)
        self.assertEqual(alpha_saved.json()["total"], 1)
        self.assertEqual(alpha_saved.json()["items"][0]["id"], published_id)
        alpha_ids = self.client.get("/api/v1/opportunities/saved/ids")
        self.assertEqual(alpha_ids.status_code, 200, alpha_ids.text)
        self.assertEqual(alpha_ids.json(), [published_id])

        self.identity["user_id"] = "clerk_saved_opportunity_beta"
        beta_saved = self.client.get("/api/v1/opportunities/saved")
        self.assertEqual(beta_saved.status_code, 200, beta_saved.text)
        self.assertEqual(beta_saved.json()["total"], 0)
        self.assertEqual(
            self.client.get("/api/v1/opportunities/saved/ids").json(), []
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/opportunities/{published_id}/save"
            ).status_code,
            204,
        )

        self.identity["user_id"] = "clerk_saved_opportunity_alpha"
        self.assertEqual(
            self.client.delete(
                f"/api/v1/opportunities/{published_id}/save"
            ).status_code,
            204,
        )
        alpha_saved_after_delete = self.client.get(
            "/api/v1/opportunities/saved"
        )
        self.assertEqual(alpha_saved_after_delete.status_code, 200)
        self.assertEqual(alpha_saved_after_delete.json()["total"], 0)
        self.assertEqual(
            self.client.get("/api/v1/opportunities/saved/ids").json(), []
        )

    def test_invalid_filters_and_opportunity_values_are_rejected(self) -> None:
        invalid_type = self.client.get(
            "/api/v1/opportunities", params={"opportunity_type": "FAKE"}
        )
        self.assertEqual(invalid_type.status_code, 422)

        invalid_compensation = self.client.get(
            "/api/v1/opportunities",
            params={"min_compensation": 5000, "max_compensation": 1000},
        )
        self.assertEqual(invalid_compensation.status_code, 422)
        missing_currency = self.client.get(
            "/api/v1/opportunities",
            params={"min_compensation": 5000},
        )
        self.assertEqual(missing_currency.status_code, 422)

        invalid_write = self.opportunity_payload(
            suffix="invalid",
            title="Invalid Range",
            opportunity_type="INTERNSHIP",
            location="Pune",
            work_mode="remote",
            stipend=1000,
            deadline_days=15,
        )
        invalid_write["salary_min"] = 100000
        invalid_write["salary_max"] = 50000
        self.grant_admin()
        self.assertEqual(
            self.client.post(
                "/api/v1/admin/opportunities",
                json=invalid_write,
            ).status_code,
            422,
        )


if __name__ == "__main__":
    unittest.main()