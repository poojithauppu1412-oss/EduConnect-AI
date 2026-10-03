import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.auth.clerk import ClerkIdentity, get_current_clerk_identity
from backend.app.db.session import engine, get_db
from backend.app.main import app
from backend.app.models.identity import Profile, Role, User, UserRole


class ProfileApiTests(unittest.TestCase):
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
        self.identity = {"user_id": "clerk_profile_alpha"}
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

    def test_profile_is_created_persisted_and_reports_completion(self) -> None:
        initial = self.client.get("/api/v1/profile")

        self.assertEqual(initial.status_code, 200)
        self.assertEqual(initial.json()["email"], "clerk_profile_alpha@example.test")
        self.assertEqual(initial.json()["completion_percent"], 0)

        updated = self.client.put(
            "/api/v1/profile",
            json={
                "name": "Alex Student",
                "education": "Undergraduate",
                "degree": "BSc",
                "branch": "Computer Science",
                "graduation_year": 2027,
                "skills": ["Python", "Data analysis", " python "],
                "certifications": ["Cloud foundations"],
                "experience_summary": "Course and personal projects",
                "experience_years": 0,
                "preferred_career": "Data analyst",
                "preferred_industry": "Technology",
                "preferred_location": "Pune",
                "work_mode": "hybrid",
                "government_private_preference": "both",
                "internship_preference": True,
                "exam_preferences": {"exams": ["GATE"]},
            },
        )

        self.assertEqual(updated.status_code, 200, updated.text)
        saved = updated.json()
        self.assertEqual(saved["completion_percent"], 100)
        self.assertEqual(
            [skill.casefold() for skill in saved["skills"]],
            ["data analysis", "python"],
        )
        self.assertEqual(saved["experience_years"], 0)
        self.assertEqual(saved["exam_preferences"], {"exams": ["GATE"]})

        reread = self.client.get("/api/v1/profile")
        self.assertEqual(reread.status_code, 200)
        self.assertEqual(reread.json()["name"], "Alex Student")
        self.assertEqual(
            [skill.casefold() for skill in reread.json()["skills"]],
            ["data analysis", "python"],
        )

        with self.session_factory() as db:
            user = db.scalar(select(User).where(User.auth_provider_user_id == "clerk_profile_alpha"))
            self.assertIsNotNone(user)
            self.assertTrue(user.is_verified)
            self.assertIsNotNone(
                db.scalar(select(Profile).where(Profile.user_id == user.id))
            )
            role_names = set(
                db.scalars(
                    select(Role.name)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user.id)
                ).all()
            )
            self.assertEqual(role_names, {"USER"})

    def test_profile_updates_are_scoped_to_the_signed_in_user(self) -> None:
        first = self.client.put(
            "/api/v1/profile",
            json={"name": "First account", "skills": ["Python"]},
        )
        self.assertEqual(first.status_code, 200, first.text)

        self.identity["user_id"] = "clerk_profile_beta"
        second = self.client.get("/api/v1/profile")
        self.assertEqual(second.status_code, 200)
        self.assertIsNone(second.json()["name"])
        self.assertEqual(second.json()["skills"], [])

        rejected = self.client.put(
            "/api/v1/profile",
            json={"name": "Attempted overwrite", "user_id": "clerk_profile_alpha"},
        )
        self.assertEqual(rejected.status_code, 422)

        self.identity["user_id"] = "clerk_profile_alpha"
        first_again = self.client.get("/api/v1/profile")
        self.assertEqual(first_again.status_code, 200)
        self.assertEqual(first_again.json()["name"], "First account")
        self.assertEqual(
            [skill.casefold() for skill in first_again.json()["skills"]],
            ["python"],
        )

    def test_profile_rejects_invalid_years_and_experience(self) -> None:
        response = self.client.put(
            "/api/v1/profile",
            json={"graduation_year": 2200, "experience_years": -1},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()