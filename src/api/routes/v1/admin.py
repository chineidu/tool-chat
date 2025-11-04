"""Admin-only endpoints for role and user management."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src import create_logger
from src.api.core.auth import get_current_admin_user
from src.api.core.cache import cached
from src.api.core.rate_limit import limiter
from src.db.crud import (
    assign_role_to_user,
    create_role,
    get_all_roles,
    get_role_by_name,
    get_user_by_username,
)
from src.db.models import get_db
from src.schemas import RoleSchema, UserWithHashSchema
from src.schemas.types import RoleType

logger = create_logger(name="admin")

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/roles", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_new_role(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    role: RoleSchema,
    current_admin: UserWithHashSchema = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> RoleSchema:
    """
    Create a new role. Admin access required.

    Parameters
    ----------
        role:
            Role data to create
        current_admin:
            Current authenticated admin user
        db:
            Database session

    Returns
    -------
        Created role information
    """
    try:
        # Validate role name is a valid RoleType
        if role.name not in [r.value for r in RoleType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role name. Must be one of: {', '.join([r.value for r in RoleType])}",
            )

        db_role = create_role(db=db, role=role)

        logger.info(f"Admin {current_admin.username} created role: {db_role.name}")

        return RoleSchema(
            id=db_role.id,
            name=db_role.name,
            description=db_role.description,
            created_at=db_role.created_at.isoformat(timespec="seconds"),
            updated_at=db_role.updated_at.isoformat(timespec="seconds")
            if db_role.updated_at
            else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create role: {str(e)}",
        ) from e


@router.post("/users/{username}/roles/{role_name}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def assign_role_to_user_endpoint(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    username: str,
    role_name: str,
    current_admin: UserWithHashSchema = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Assign a role to a user. Admin access required.

    Parameters
    ----------
        username:
            Username to assign role to
        role_name:
            Role name to assign
        current_admin:
            Current authenticated admin user
        db:
            Database session

    Returns
    -------
        Success message
    """
    try:
        # Validate role name
        if role_name not in [r.value for r in RoleType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role name. Must be one of: {', '.join([r.value for r in RoleType])}",
            )

        # Check if user exists
        db_user = get_user_by_username(db=db, username=username)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {username!r} not found",
            )

        # Check if role exists
        db_role = get_role_by_name(db=db, name=role_name)
        if not db_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_name!r} not found",
            )

        # Assign role
        assign_role_to_user(db=db, username=username, role=RoleType(role_name))

        logger.info(
            f"Admin {current_admin.username} assigned role {role_name} to user {username!r}"
        )

        return {
            "message": f"Successfully assigned role {role_name!r} to user {username!r}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign role: {str(e)}",
        ) from e


@router.delete("/users/{username}/roles/{role_name}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def remove_role_from_user(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    username: str,
    role_name: str,
    current_admin: UserWithHashSchema = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Remove a role from a user. Admin access required.

    Parameters
    ----------
        username: Username to remove role from
        role_name: Role name to remove
        current_admin: Current authenticated admin user
        db: Database session

    Returns
    -------
        Success message
    """
    try:
        # Validate role name
        if role_name not in [r.value for r in RoleType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role name. Must be one of: {', '.join([r.value for r in RoleType])}",
            )

        # Check if user exists
        db_user = get_user_by_username(db=db, username=username)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

        # Check if role exists
        db_role = get_role_by_name(db=db, name=role_name)
        if not db_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_name}' not found",
            )

        # Check if user has the role
        if db_user not in db_role.users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{username}' does not have role '{role_name}'",
            )

        # Remove role
        db_role.users.remove(db_user)
        db.commit()

        logger.info(
            f"Admin {current_admin.username} removed role '{role_name}' from user '{username}'"
        )

        return {
            "message": f"Successfully removed role '{role_name}' from user '{username}'"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove role: {str(e)}",
        ) from e


@router.get("/roles", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
@cached(ttl=600, key_prefix="roles")  # type: ignore
async def list_roles(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    current_admin: UserWithHashSchema = Depends(get_current_admin_user),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List all roles in the system. Admin access required."""
    all_roles = get_all_roles(db=db)
    if all_roles:
        roles_list: list[RoleSchema] = [
            RoleSchema(
                id=role.id,
                name=role.name,
                description=role.description,
                created_at=role.created_at.isoformat(timespec="seconds"),
                updated_at=role.updated_at.isoformat(timespec="seconds")
                if role.updated_at
                else None,
            )
            for role in all_roles
        ]
        return {"roles": roles_list}

    return {"roles": []}
