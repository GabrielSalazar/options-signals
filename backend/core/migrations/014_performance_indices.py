"""Migration 014: Add performance indices for hot queries."""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indices for common query patterns."""
    # Index on ticker for signal queries (WHERE ticker = ?)
    op.create_index(
        "ix_signals_ticker",
        "signals",
        ["ticker"],
        if_not_exists=True,
    )

    # Index on data_sinal for time-based queries
    op.create_index(
        "ix_signals_data_sinal",
        "signals",
        ["data_sinal"],
        if_not_exists=True,
    )

    # Composite index for common filter: ticker + data_sinal
    op.create_index(
        "ix_signals_ticker_data_sinal",
        "signals",
        ["ticker", "data_sinal"],
        if_not_exists=True,
    )

    # Index on cooldown key for lookup
    op.create_index(
        "ix_cooldown_key",
        "cooldown",
        ["key"],
        if_not_exists=True,
    )


def downgrade() -> None:
    """Remove indices."""
    op.drop_index("ix_cooldown_key", if_exists=True)
    op.drop_index("ix_signals_ticker_data_sinal", if_exists=True)
    op.drop_index("ix_signals_data_sinal", if_exists=True)
    op.drop_index("ix_signals_ticker", if_exists=True)
