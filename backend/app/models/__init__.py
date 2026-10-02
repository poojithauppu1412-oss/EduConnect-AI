from backend.app.models.base import Base
from backend.app.models.communication import (
    AuditLog,
    ChatMessage,
    ChatSession,
    Notification,
    NotificationPreference,
    Recommendation,
)
from backend.app.models.content import (
    CareerPath,
    CareerSkill,
    DocumentChunk,
    KnowledgeDocument,
    LegalDocument,
    LegalTopic,
)
from backend.app.models.identity import Profile, Role, Skill, User, UserRole, UserSkill
from backend.app.models.ingestion import IngestionJob, SourceFetchLog
from backend.app.models.opportunity import (
    Application,
    Opportunity,
    OpportunityCategory,
    OpportunityDocument,
    OpportunitySkill,
    OpportunitySource,
    Organization,
    SavedOpportunity,
)

__all__ = [
    "Application",
    "AuditLog",
    "Base",
    "CareerPath",
    "CareerSkill",
    "ChatMessage",
    "ChatSession",
    "DocumentChunk",
    "IngestionJob",
    "KnowledgeDocument",
    "LegalDocument",
    "LegalTopic",
    "Notification",
    "NotificationPreference",
    "Opportunity",
    "OpportunityCategory",
    "OpportunityDocument",
    "OpportunitySkill",
    "OpportunitySource",
    "Organization",
    "Profile",
    "Recommendation",
    "Role",
    "SavedOpportunity",
    "Skill",
    "SourceFetchLog",
    "User",
    "UserRole",
    "UserSkill",
]