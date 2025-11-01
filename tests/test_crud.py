"""
Tests for CRUD operations in the database.
"""

import pytest
from sqlalchemy.orm.session import Session

from src.db.crud import (
    assign_role_to_user,
    convert_userdb_to_schema,
    create_feedback,
    create_role,
    create_user,
    get_feedback_by_username,
    get_role_by_name,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)
from src.schemas import FeedbackRequestSchema, RoleSchema, UserWithHashSchema
from src.schemas.types import Feedback, RoleType


class TestUserCRUD:
    """Test user CRUD operations."""

    def test_get_user_by_email_not_found(self, db_session: Session) -> None:
        """Test getting a user by email when user doesn't exist."""
        user = get_user_by_email(db_session, "nonexistent@example.com")
        assert user is None

    def test_get_user_by_username_not_found(self, db_session: Session) -> None:
        """Test getting a user by username when user doesn't exist."""
        user = get_user_by_username(db_session, "nonexistent")
        assert user is None

    def test_get_user_by_id_not_found(self, db_session: Session) -> None:
        """Test getting a user by ID when user doesn't exist."""
        user = get_user_by_id(db_session, 999)
        assert user is None

    def test_create_user_success(self, db_session: Session) -> None:
        """Test creating a new user successfully."""
        user_data = UserWithHashSchema(
            firstname="John",
            lastname="Doe",
            username="johndoe",
            email="john.doe@example.com",
            hashed_password="hashed_password_123",
            is_active=True,
        )

        user = create_user(db_session, user_data)

        assert user is not None
        assert user.firstname == "John"
        assert user.lastname == "Doe"
        assert user.username == "johndoe"
        assert user.email == "john.doe@example.com"
        assert user.hashed_password == "hashed_password_123"
        assert user.is_active is True

    def test_create_user_duplicate_email(self, db_session: Session) -> None:
        """Test creating a user with duplicate email raises ValueError."""
        user_data = UserWithHashSchema(
            firstname="Johnny",
            lastname="Doey",
            username="johndoe_duplicate",
            email="duplicate@example.com",
            hashed_password="hashed_password_123",
        )

        # Create first user
        create_user(db_session, user_data)

        # Try to create user with same email
        duplicate_user = UserWithHashSchema(
            firstname="Jane",
            lastname="Smith",
            username="janesmith_duplicate",
            email="duplicate@example.com",  # Same email
            hashed_password="hashed_password_456",
        )

        with pytest.raises(ValueError, match="Email .* is already registered"):
            create_user(db_session, duplicate_user)

    def test_get_user_by_email_found(self, db_session: Session) -> None:
        """Test getting a user by email when user exists."""
        user_data = UserWithHashSchema(
            firstname="Jane",
            lastname="Smith",
            username="janesmith",
            email="jane.smith@example.com",
            hashed_password="hashed_password_456",
        )

        created_user = create_user(db_session, user_data)
        retrieved_user = get_user_by_email(db_session, "jane.smith@example.com")

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == "jane.smith@example.com"

    def test_get_user_by_username_found(self, db_session: Session) -> None:
        """Test getting a user by username when user exists."""
        user_data = UserWithHashSchema(
            firstname="Bob",
            lastname="Johnson",
            username="bobjohnson",
            email="bob.johnson@example.com",
            hashed_password="hashed_password_789",
        )

        created_user = create_user(db_session, user_data)
        retrieved_user = get_user_by_username(db_session, "bobjohnson")

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == "bobjohnson"

    def test_get_user_by_id_found(self, db_session: Session) -> None:
        """Test getting a user by ID when user exists."""
        user_data = UserWithHashSchema(
            firstname="Alice",
            lastname="Brown",
            username="alicebrown",
            email="alice.brown@example.com",
            hashed_password="hashed_password_101",
        )

        created_user = create_user(db_session, user_data)
        retrieved_user = get_user_by_id(db_session, created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id

    def test_convert_userdb_to_schema(self, db_session: Session) -> None:
        """Test converting DBUser to UserWithHashSchema."""
        user_data = UserWithHashSchema(
            firstname="Charlie",
            lastname="Wilson",
            username="charliewilson",
            email="charlie.wilson@example.com",
            hashed_password="hashed_password_202",
        )

        db_user = create_user(db_session, user_data)
        schema_user = convert_userdb_to_schema(db_user)

        assert schema_user is not None
        assert schema_user.id == db_user.id
        assert schema_user.firstname == db_user.firstname
        assert schema_user.lastname == db_user.lastname
        assert schema_user.username == db_user.username
        assert schema_user.email == db_user.email
        assert schema_user.hashed_password == db_user.hashed_password
        assert schema_user.is_active == db_user.is_active
        assert schema_user.roles == []  # No roles assigned yet


class TestFeedbackCRUD:
    """Test feedback CRUD operations."""

    def test_get_feedback_by_username_not_found(self, db_session: Session) -> None:
        """Test getting feedback when it doesn't exist."""
        feedback = get_feedback_by_username(
            db_session, "session123", 1, "nonexistent_user"
        )
        assert feedback is None

    def test_create_feedback_success(self, db_session: Session) -> None:
        """Test creating feedback successfully."""
        # First create a user
        user_data = UserWithHashSchema(
            firstname="David",
            lastname="Miller",
            username="davidmiller",
            email="david.miller@example.com",
            hashed_password="hashed_password_303",
        )
        user = create_user(db_session, user_data)

        feedback_data = FeedbackRequestSchema(
            user_name="davidmiller",
            user_id=user.id,
            session_id="session123",
            message_index=1,
            user_message="What is AI?",
            assistant_message="AI stands for Artificial Intelligence.",
            sources=["https://example.com"],
            feedback=Feedback.POSITIVE,
        )

        feedback = create_feedback(db_session, feedback_data)

        assert feedback is not None
        assert feedback.user_name == "davidmiller"
        assert feedback.session_id == "session123"
        assert feedback.message_index == 1
        assert feedback.user_message == "What is AI?"
        assert feedback.assistant_message == "AI stands for Artificial Intelligence."
        assert feedback.sources == '["https://example.com"]'  # JSON string
        assert feedback.feedback == "positive"

    def test_get_feedback_by_username_found(self, db_session: Session) -> None:
        """Test getting feedback when it exists."""
        # First create a user
        user_data = UserWithHashSchema(
            firstname="Feedback",
            lastname="User",
            username="johndoe_feedback",
            email="john.doe.feedback@example.com",
            hashed_password="hashed_password_123",
        )
        user = create_user(db_session, user_data)

        feedback_data = FeedbackRequestSchema(
            user_name="johndoe_feedback",
            user_id=user.id,
            session_id="session456",
            message_index=1,
            user_message="What is machine learning?",
            assistant_message="AI stands for Artificial Intelligence. It's a field of computer science.",
            feedback=Feedback.POSITIVE,
        )

        created_feedback = create_feedback(db_session, feedback_data)
        retrieved_feedback = get_feedback_by_username(
            db_session, "session456", 1, "johndoe_feedback"
        )

        assert retrieved_feedback is not None
        assert retrieved_feedback.id == created_feedback.id
        assert retrieved_feedback.session_id == "session456"
        assert retrieved_feedback.message_index == 1
        assert retrieved_feedback.user_name == "johndoe_feedback"


class TestRoleCRUD:
    """Test role CRUD operations."""

    def test_get_role_by_name_not_found(self, db_session: Session) -> None:
        """Test getting a role by name when it doesn't exist."""
        role = get_role_by_name(db_session, "nonexistent_role")  # type: ignore
        assert role is None

    def test_create_role_success(self, db_session: Session) -> None:
        """Test creating a new role successfully."""
        role_data = RoleSchema(
            name=RoleType.ADMIN,
            description="Administrator role",
        )

        role = create_role(db_session, role_data)

        assert role is not None
        assert role.name == "admin"
        # Since ADMIN role already exists from initialization, it should return existing role
        assert role.description == "Administrator with full access"

    def test_create_role_duplicate(self, db_session: Session) -> None:
        """Test creating a role that already exists returns existing role."""
        role_data = RoleSchema(
            name=RoleType.ADMIN,
            description="Administrator role",
        )

        # Create first role
        first_role = create_role(db_session, role_data)

        # Try to create the same role again
        second_role = create_role(db_session, role_data)

        # Should return the same role
        assert first_role.id == second_role.id
        assert first_role.name == second_role.name

    def test_get_role_by_name_found(self, db_session: Session) -> None:
        """Test getting a role by name when it exists."""
        role_data = RoleSchema(
            name=RoleType.ADMIN,
            description="Administrator role",
        )

        created_role = create_role(db_session, role_data)
        retrieved_role = get_role_by_name(db_session, RoleType.ADMIN)

        assert retrieved_role is not None
        assert retrieved_role.id == created_role.id
        assert retrieved_role.name == "admin"

    def test_assign_role_to_user_success(self, db_session: Session) -> None:
        """Test assigning a role to a user successfully."""
        # Create user
        user_data = UserWithHashSchema(
            firstname="Frank",
            lastname="Taylor",
            username="frank_taylor",
            email="frank.taylor@example.com",
            hashed_password="hashed_password_505",
        )
        user = create_user(db_session, user_data)

        # Create role
        role_data = RoleSchema(
            name=RoleType.USER,
            description="User role",
        )
        role = create_role(db_session, role_data)

        # Assign role to user
        assign_role_to_user(db_session, "frank_taylor", RoleType.USER)

        # Refresh user from database
        db_session.refresh(user)
        db_session.refresh(role)

        # Check that role was assigned
        assert len(user.roles) == 1
        assert user.roles[0].name == "user"
        assert role in user.roles

    def test_assign_role_to_user_nonexistent_user(self, db_session: Session) -> None:
        """Test assigning role to nonexistent user raises ValueError."""
        # Create role first
        role_data = RoleSchema(
            name=RoleType.ADMIN,
            description="Administrator role",
        )
        create_role(db_session, role_data)

        with pytest.raises(ValueError, match="User nonexistent does not exist"):
            assign_role_to_user(db_session, "nonexistent", RoleType.ADMIN)

    def test_assign_role_to_user_nonexistent_role(self, db_session: Session) -> None:
        """Test assigning nonexistent role to user raises ValueError."""
        # Create user
        user_data = UserWithHashSchema(
            firstname="Grace",
            lastname="Lee",
            username="gracelee",
            email="grace.lee@example.com",
            hashed_password="hashed_password_606",
        )
        create_user(db_session, user_data)

        with pytest.raises(ValueError, match="Role nonexistent does not exist"):
            assign_role_to_user(db_session, "gracelee", "nonexistent")  # type: ignore

    def test_assign_role_to_user_already_assigned(self, db_session: Session) -> None:
        """Test assigning already assigned role doesn't duplicate."""
        # Create user
        user_data = UserWithHashSchema(
            firstname="Henry",
            lastname="Clark",
            username="henryclark",
            email="henry.clark@example.com",
            hashed_password="hashed_password_707",
        )
        user = create_user(db_session, user_data)

        # Create role
        role_data = RoleSchema(
            name=RoleType.GUEST,
            description="Guest role",
        )
        create_role(db_session, role_data)

        # Assign role first time
        assign_role_to_user(db_session, "henryclark", RoleType.GUEST)

        # Assign same role again
        assign_role_to_user(db_session, "henryclark", RoleType.GUEST)

        # Refresh user from database
        db_session.refresh(user)

        # Should still have only one role
        assert len(user.roles) == 1
        assert user.roles[0].name == "guest"
