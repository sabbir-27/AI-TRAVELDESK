"""Security primitive and normalized schema integrity tests."""

import uuid

from cryptography.fernet import Fernet

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    decrypt_sensitive_value,
    encrypt_sensitive_value,
    hash_password,
    verify_password,
)
from app.models import Base


def test_password_hashing_roundtrip() -> None:
    hashed = hash_password("TopSecretPassword!99")
    assert hashed != "TopSecretPassword!99"
    assert verify_password("TopSecretPassword!99", hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_claims_and_tamper_rejection() -> None:
    uid = uuid.uuid4()
    aid = uuid.uuid4()
    token = create_access_token(user_id=uid, role="AGENCY_OWNER", agency_id=aid)
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["role"] == "AGENCY_OWNER"
    assert payload["agency_id"] == str(aid)

    tampered = token[:-4] + "xxxx"
    try:
        decode_access_token(tampered)
        raise AssertionError("Expected TokenError for tampered token")
    except TokenError:
        pass


def test_sensitive_field_encryption_roundtrip(monkeypatch) -> None:
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        encrypted = encrypt_sensitive_value("P12345678")
        assert encrypted != "P12345678"
        assert decrypt_sensitive_value(encrypted) == "P12345678"
    finally:
        get_settings.cache_clear()


def test_all_required_tables_registered_in_metadata() -> None:
    expected_tables = {
        "users",
        "agencies",
        "agency_members",
        "roles",
        "permissions",
        "role_permissions",
        "refresh_tokens",
        "subscriptions",
        "subscription_plans",
        "agency_integrations",
        "integration_credentials",
        "customers",
        "passengers",
        "conversations",
        "messages",
        "bookings",
        "booking_passengers",
        "flight_offers",
        "payments",
        "invoices",
        "tickets",
        "refunds",
        "cancellations",
        "notifications",
        "audit_logs",
        "agent_configurations",
        "api_usage",
        "supplier_transactions",
        "human_assignments",
        "support_tickets",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))


def test_alembic_upgrade_and_downgrade(tmp_path) -> None:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    db_file = tmp_path / "alembic_test.db"
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file}")

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")

