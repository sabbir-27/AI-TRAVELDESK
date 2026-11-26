"""Service managing agency widget tokens, origin allowlists, and REST API keys."""

import uuid
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import apply_rls_context
from app.core.security import generate_opaque_token, hash_token
from app.models.engagement import AuditLog
from app.models.enums import AgencyStatus, IntegrationType
from app.models.identity import Agency, User
from app.models.integration import AgencyIntegration, AgentConfiguration, IntegrationCredential
from app.schemas.integrations import (
    AgencyIntegrationRead,
    ApiKeyIssuedResponse,
    IntegrationCredentialSummary,
    WidgetPublicConfigResponse,
    WidgetTokenIssuedResponse,
)


def _normalize_origin(origin: str) -> str:
    parsed = urlparse(origin.strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    return origin.strip().rstrip("/").lower()


class IntegrationService:
    """Handles widget token provisioning, REST API keys, and white-label config."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_integrations(self, agency_id: uuid.UUID) -> list[AgencyIntegrationRead]:
        integrations = (
            await self.session.execute(
                select(AgencyIntegration)
                .where(AgencyIntegration.agency_id == agency_id)
                .order_by(AgencyIntegration.created_at.asc())
            )
        ).scalars().all()

        results: list[AgencyIntegrationRead] = []
        for item in integrations:
            creds = (
                await self.session.execute(
                    select(IntegrationCredential)
                    .where(
                        IntegrationCredential.integration_id == item.id,
                        IntegrationCredential.agency_id == agency_id,
                    )
                    .order_by(IntegrationCredential.created_at.desc())
                )
            ).scalars().all()
            results.append(
                AgencyIntegrationRead(
                    id=item.id,
                    agency_id=item.agency_id,
                    integration_type=item.integration_type,
                    provider_name=item.provider_name,
                    is_enabled=item.is_enabled,
                    allowed_origins=list(item.allowed_origins or []),
                    config=dict(item.config or {}),
                    credentials=[
                        IntegrationCredentialSummary(
                            id=c.id,
                            key_prefix=c.key_prefix,
                            is_active=c.is_active,
                            created_at=c.created_at,
                        )
                        for c in creds
                    ],
                )
            )
        return results

    async def issue_widget_token(
        self,
        *,
        agency: Agency,
        actor: User,
        allowed_origins: list[str] | None = None,
    ) -> WidgetTokenIssuedResponse:
        integration = await self._get_or_create_integration(
            agency_id=agency.id,
            integration_type=IntegrationType.WIDGET,
            provider_name="ai_traveldesk_widget",
        )
        if allowed_origins is not None:
            integration.allowed_origins = [
                _normalize_origin(o) for o in allowed_origins if o.strip()
            ]

        # Deactivate prior widget tokens on rotation.
        old_creds = (
            await self.session.execute(
                select(IntegrationCredential).where(
                    IntegrationCredential.integration_id == integration.id,
                    IntegrationCredential.is_active.is_(True),
                )
            )
        ).scalars().all()
        for c in old_creds:
            c.is_active = False

        raw_token = f"atd_wgt_{generate_opaque_token(24)}"
        cred = IntegrationCredential(
            agency_id=agency.id,
            integration_id=integration.id,
            key_prefix=raw_token[:16],
            key_hash=hash_token(raw_token),
            is_active=True,
        )
        self.session.add(cred)
        self.session.add(
            AuditLog(
                agency_id=agency.id,
                actor_user_id=actor.id,
                action="integration.widget_token_rotated",
                resource_type="agency_integration",
                resource_id=str(integration.id),
                details={"key_prefix": cred.key_prefix},
            )
        )
        await self.session.flush()

        snippet = (
            f'<script\n  src="http://localhost:8000/widget.js"\n'
            f'  data-agency-id="{agency.id}"\n'
            f'  data-widget-token="{raw_token}"\n></script>'
        )
        return WidgetTokenIssuedResponse(
            agency_id=agency.id,
            widget_token=raw_token,
            allowed_origins=list(integration.allowed_origins or []),
            embed_snippet=snippet,
        )

    async def update_widget_origins(
        self,
        *,
        agency_id: uuid.UUID,
        allowed_origins: list[str],
    ) -> list[str]:
        integration = await self._get_or_create_integration(
            agency_id=agency_id,
            integration_type=IntegrationType.WIDGET,
            provider_name="ai_traveldesk_widget",
        )
        cleaned = [_normalize_origin(o) for o in allowed_origins if o.strip()]
        integration.allowed_origins = cleaned
        await self.session.flush()
        return cleaned

    async def create_api_key(
        self,
        *,
        agency: Agency,
        actor: User,
        label: str,
    ) -> ApiKeyIssuedResponse:
        integration = await self._get_or_create_integration(
            agency_id=agency.id,
            integration_type=IntegrationType.REST_API,
            provider_name="ai_traveldesk_rest_api",
        )
        raw_key = f"atd_live_{generate_opaque_token(32)}"
        cred = IntegrationCredential(
            agency_id=agency.id,
            integration_id=integration.id,
            key_prefix=raw_key[:16],
            key_hash=hash_token(raw_key),
            is_active=True,
        )
        self.session.add(cred)
        integration.config = {**(integration.config or {}), "last_key_label": label}
        self.session.add(
            AuditLog(
                agency_id=agency.id,
                actor_user_id=actor.id,
                action="integration.api_key_created",
                resource_type="integration_credential",
                resource_id=str(cred.id),
                details={"label": label, "key_prefix": cred.key_prefix},
            )
        )
        await self.session.flush()
        await self.session.refresh(cred)
        return ApiKeyIssuedResponse(
            credential_id=cred.id,
            label=label,
            key_prefix=cred.key_prefix or raw_key[:16],
            api_key=raw_key,
            created_at=cred.created_at,
        )

    async def revoke_credential(
        self,
        *,
        agency_id: uuid.UUID,
        credential_id: uuid.UUID,
        actor: User,
    ) -> None:
        cred = (
            await self.session.execute(
                select(IntegrationCredential).where(
                    IntegrationCredential.id == credential_id,
                    IntegrationCredential.agency_id == agency_id,
                )
            )
        ).scalar_one_or_none()
        if cred is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found."
            )
        cred.is_active = False
        self.session.add(
            AuditLog(
                agency_id=agency_id,
                actor_user_id=actor.id,
                action="integration.credential_revoked",
                resource_type="integration_credential",
                resource_id=str(cred.id),
            )
        )
        await self.session.flush()

    async def verify_widget_token(
        self,
        *,
        widget_token: str,
        claimed_agency_id: uuid.UUID | None,
        request_origin: str | None,
    ) -> Agency:
        token_hash = hash_token(widget_token)
        await apply_rls_context(
            self.session,
            agency_id=claimed_agency_id,
            is_super_admin=(claimed_agency_id is None),
        )
        try:
            row = (
                await self.session.execute(
                    select(IntegrationCredential, AgencyIntegration, Agency)
                    .join(
                        AgencyIntegration,
                        IntegrationCredential.integration_id == AgencyIntegration.id,
                    )
                    .join(Agency, AgencyIntegration.agency_id == Agency.id)
                    .where(
                        IntegrationCredential.key_hash == token_hash,
                        IntegrationCredential.is_active.is_(True),
                        AgencyIntegration.integration_type == IntegrationType.WIDGET,
                        AgencyIntegration.is_enabled.is_(True),
                        Agency.deleted_at.is_(None),
                    )
                )
            ).first()
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or inactive widget token.",
                )
            _, integration, agency = row
        except Exception:
            await apply_rls_context(self.session, agency_id=None, is_super_admin=False)
            raise
        await apply_rls_context(self.session, agency_id=agency.id, is_super_admin=False)
        if claimed_agency_id is not None and claimed_agency_id != agency.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Widget token does not match the specified agency.",
            )
        if agency.status != AgencyStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agency widget is inactive until approved.",
            )
        allowed = [_normalize_origin(o) for o in (integration.allowed_origins or [])]
        if allowed and request_origin:
            normalized_req = _normalize_origin(request_origin)
            if normalized_req not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Origin not authorized for this agency widget.",
                )
        return agency

    async def verify_api_key(self, api_key: str) -> Agency:
        key_hash = hash_token(api_key)
        await apply_rls_context(self.session, agency_id=None, is_super_admin=True)
        try:
            row = (
                await self.session.execute(
                    select(IntegrationCredential, AgencyIntegration, Agency)
                    .join(
                        AgencyIntegration,
                        IntegrationCredential.integration_id == AgencyIntegration.id,
                    )
                    .join(Agency, AgencyIntegration.agency_id == Agency.id)
                    .where(
                        IntegrationCredential.key_hash == key_hash,
                        IntegrationCredential.is_active.is_(True),
                        AgencyIntegration.integration_type == IntegrationType.REST_API,
                        AgencyIntegration.is_enabled.is_(True),
                        Agency.deleted_at.is_(None),
                    )
                )
            ).first()
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or revoked API key.",
                )
            _, _, agency = row
        except Exception:
            await apply_rls_context(self.session, agency_id=None, is_super_admin=False)
            raise
        await apply_rls_context(self.session, agency_id=agency.id, is_super_admin=False)
        if agency.status != AgencyStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agency account is not active.",
            )
        return agency

    async def get_widget_public_config(self, agency: Agency) -> WidgetPublicConfigResponse:
        cfg = (
            await self.session.execute(
                select(AgentConfiguration).where(AgentConfiguration.agency_id == agency.id)
            )
        ).scalar_one_or_none()
        return WidgetPublicConfigResponse(
            agency_id=agency.id,
            brand_name=agency.name,
            logo_url=agency.logo_url,
            primary_color=agency.primary_color,
            secondary_color=agency.secondary_color,
            agent_name=cfg.agent_name if cfg else f"{agency.name} AI",
            welcome_message=(
                cfg.welcome_message
                if cfg
                else f"Welcome to {agency.name}! How can I help with your flight?"
            ),
            supported_languages=list(cfg.supported_languages) if cfg else ["en", "bn", "banglish"],
            contact_email=agency.contact_email,
            contact_phone=agency.contact_phone,
        )

    async def _get_or_create_integration(
        self,
        *,
        agency_id: uuid.UUID,
        integration_type: IntegrationType,
        provider_name: str,
    ) -> AgencyIntegration:
        row = (
            await self.session.execute(
                select(AgencyIntegration).where(
                    AgencyIntegration.agency_id == agency_id,
                    AgencyIntegration.integration_type == integration_type,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = AgencyIntegration(
                agency_id=agency_id,
                integration_type=integration_type,
                provider_name=provider_name,
                is_enabled=True,
                allowed_origins=[],
                config={},
            )
            self.session.add(row)
            await self.session.flush()
        return row
