"""initial schema: locations, location_aliases, weather_readings

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country", sa.String(100), nullable=False, server_default=""),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("name", "country", "latitude", "longitude", name="uq_location_identity"),
    )
    op.create_table(
        "location_aliases",
        sa.Column("alias", sa.String(200), primary_key=True),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("ix_location_aliases_location_id", "location_aliases", ["location_id"])
    op.create_table(
        "weather_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("temperature", sa.Float, nullable=False),
        sa.Column("temperature_unit", sa.String(16), nullable=False),
        sa.Column("wind_speed", sa.Float, nullable=False),
        sa.Column("wind_speed_unit", sa.String(16), nullable=False),
        sa.Column("humidity", sa.Integer, nullable=True),
        sa.Column("weather_code", sa.Integer, nullable=False),
        sa.Column("description", sa.String(100), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_weather_location_fetched", "weather_readings", ["location_id", "fetched_at"]
    )


def downgrade() -> None:
    op.drop_table("weather_readings")
    op.drop_table("location_aliases")
    op.drop_table("locations")
