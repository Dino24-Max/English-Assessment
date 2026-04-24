"""Add semantic_hash, grammar_type, grammar_topic to questions.

Revision ID: 20250424120000
Revises:
Create Date: 2025-04-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250424120000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "questions" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("questions")}

    if "semantic_hash" not in cols:
        op.add_column("questions", sa.Column("semantic_hash", sa.String(length=64), nullable=True))
    if "grammar_type" not in cols:
        op.add_column("questions", sa.Column("grammar_type", sa.String(length=50), nullable=True))
    if "grammar_topic" not in cols:
        op.add_column("questions", sa.Column("grammar_topic", sa.String(length=100), nullable=True))

    insp = sa.inspect(bind)
    indexes = {ix["name"] for ix in insp.get_indexes("questions")}
    uq_names = {uc["name"] for uc in insp.get_unique_constraints("questions")}

    if "ix_questions_grammar_classification" not in indexes:
        op.create_index(
            "ix_questions_grammar_classification",
            "questions",
            ["grammar_type", "grammar_topic", "cefr_level"],
            unique=False,
        )

    if "uq_questions_semantic_hash" not in uq_names and "uq_questions_semantic_hash" not in indexes:
        dialect = bind.dialect.name
        if dialect == "sqlite":
            # SQLite: no ALTER ADD CONSTRAINT — unique index enforces dedupe for non-NULL hashes
            op.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_questions_semantic_hash ON questions (semantic_hash)"
            )
        else:
            op.create_unique_constraint("uq_questions_semantic_hash", "questions", ["semantic_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "questions" not in insp.get_table_names():
        return

    indexes = {ix["name"] for ix in insp.get_indexes("questions")}
    uq_names = {uc["name"] for uc in insp.get_unique_constraints("questions")}

    if "uq_questions_semantic_hash" in uq_names:
        op.drop_constraint("uq_questions_semantic_hash", "questions", type_="unique")
    elif "uq_questions_semantic_hash" in indexes:
        op.drop_index("uq_questions_semantic_hash", table_name="questions")
    if "ix_questions_grammar_classification" in indexes:
        op.drop_index("ix_questions_grammar_classification", table_name="questions")

    cols = {c["name"] for c in insp.get_columns("questions")}
    if "grammar_topic" in cols:
        op.drop_column("questions", "grammar_topic")
    if "grammar_type" in cols:
        op.drop_column("questions", "grammar_type")
    if "semantic_hash" in cols:
        op.drop_column("questions", "semantic_hash")
