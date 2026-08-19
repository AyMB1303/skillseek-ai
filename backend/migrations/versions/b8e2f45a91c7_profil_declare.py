"""Profil declare par le candidat.

Colonne JSON plutot que trois colonnes distinctes : la forme du profil suit
celle qu'attend deja le moteur de score (`skills`, `experience_years`,
`degree`), et la faire evoluer ne doit pas couter une migration a chaque fois.
Nullable : un candidat n'est jamais tenu de la renseigner.

Revision ID: b8e2f45a91c7
Revises: a1d5c9e04b73
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8e2f45a91c7'
down_revision = 'a1d5c9e04b73'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('profil_declare', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('users', 'profil_declare')
