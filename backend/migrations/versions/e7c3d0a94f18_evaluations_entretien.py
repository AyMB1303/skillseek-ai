"""evaluations d'entretien

Revision ID: e7c3d0a94f18
Revises: d4a91b6e35c2
Create Date: 2026-08-13 23:10:00.000000

La table consigne l'appreciation portee apres l'entretien, a cote de la note
calculee avant. `score_systeme` y est recopie a la premiere saisie : figer
cette valeur permet de comparer plus tard, meme si la candidature est
reanalysee entre-temps — sans quoi la comparaison porterait sur une note qui
n'est plus celle qu'avait le recruteur sous les yeux.

La contrainte d'unicite garantit un compte rendu par candidature : une
revision se fait par modification, non par accumulation.
"""
from alembic import op
import sqlalchemy as sa


revision = 'e7c3d0a94f18'
down_revision = 'd4a91b6e35c2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.JSON(), nullable=False),
        sa.Column('verdict', sa.String(length=20), nullable=False),
        sa.Column('commentaire', sa.Text(), nullable=True),
        sa.Column('score_systeme', sa.Float(), nullable=True),
        sa.Column('evaluateur_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluateur_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id', name='uq_evaluation_candidature'),
    )
    op.create_index('ix_evaluations_application_id', 'evaluations',
                    ['application_id'])


def downgrade():
    op.drop_index('ix_evaluations_application_id', table_name='evaluations')
    op.drop_table('evaluations')
