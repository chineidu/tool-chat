#!/usr/bin/env python3
"""
Bootstrap script to create the first admin user.

Usage: uv run -m scripts.create_admin --username admin --email admin@example.com --password mypassword
"""

import argparse
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.api.auth.auth import get_password_hash
from src.db.crud import (
    assign_role_to_user,
    create_role,
    create_user,
    get_role_by_name,
    get_user_by_username,
)
from src.db.models import get_db_session
from src.schemas import UserWithHashSchema
from src.schemas.input_schema import RoleSchema
from src.schemas.types import RoleType


def create_admin_user(
    username: str, email: str, password: str, firstname: str = "", lastname: str = ""
) -> None:
    """Create the first admin user."""
    with get_db_session() as db:
        # Check if admin users already exist
        admin_role = get_role_by_name(db=db, name=RoleType.ADMIN)
        if admin_role and admin_role.users:
            print("❌ Admin users already exist. This script should only be run once.")
            return

        # Check if user already exists
        existing_user = get_user_by_username(db=db, username=username)
        if existing_user:
            print(f"❌ User '{username}' already exists.")
            return

        # Create roles
        admin_role = create_role(
            db=db,
            role=RoleSchema(
                name=RoleType.ADMIN, description="Administrator with full system access"
            ),
        )
        create_role(
            db=db,
            role=RoleSchema(
                name=RoleType.USER, description="Regular user with standard access"
            ),
        )
        create_role(
            db=db,
            role=RoleSchema(
                name=RoleType.GUEST, description="Guest user with limited access"
            ),
        )

        # Create admin user
        hashed_password = get_password_hash(password)
        user_data = UserWithHashSchema(
            username=username,
            email=email,
            firstname=firstname,
            lastname=lastname,
            hashed_password=hashed_password,
            is_active=True,
        )

        create_user(db=db, user=user_data)
        assign_role_to_user(db=db, username=username, role=RoleType.ADMIN)

        print("🎉 Admin user created successfully!")
        print(f"Username: {username}")
        print(f"Email: {email}")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Create the first admin user")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--firstname", default="", help="Admin first name")
    parser.add_argument("--lastname", default="", help="Admin last name")

    args = parser.parse_args()

    print("🚀 Creating first admin user...")
    create_admin_user(
        username=args.username,
        email=args.email,
        password=args.password,
        firstname=args.firstname,
        lastname=args.lastname,
    )


if __name__ == "__main__":
    main()
