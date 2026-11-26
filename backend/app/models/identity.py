"""Identity, multi-tenant agency, RBAC, and refresh token models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    JSONBType,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import AgencyStatus, UserRole


class Agency(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Travel agency tenant entity."""

    __tablename__ = "agencies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    status: Mapped[AgencyStatus] = mapped_column(
        SAEnum(AgencyStatus, name="agency_status", native_enum=False),
        nullable=False,
        default=AgencyStatus.PENDING,
        index=True,
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="BD")
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # White-label branding
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(20), nullable=False, default="#0F172A")
    secondary_color: Mapped[str] = mapped_column(String(20), nullable=False, default="#2563EB")
    service_fee_flat: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    service_fee_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    settings: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)

    members: Mapped[list["AgencyMember"]] = relationship(back_populates="agency")


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Platform user account (Super Admin, Agency Staff, or Customer)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.CUSTOMER,
        index=True,
    )
    default_agency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agencies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    memberships: Mapped[list["AgencyMember"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """RBAC role definition (system-wide or agency-customized)."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("agency_id", "name", name="uq_roles_agency_name"),)

    agency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agencies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Granular RBAC permission."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class RolePermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Join table assigning permissions to roles."""

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    )


class AgencyMember(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Maps a user to a tenant agency with a specific RBAC role."""

    __tablename__ = "agency_members"
    __table_args__ = (UniqueConstraint("agency_id", "user_id", name="uq_agency_member_user"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="agency_member_role", native_enum=False),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    agency: Mapped["Agency"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Hashed refresh token record supporting rotation and reuse detection."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
