"""signalements de controle des candidatures

Revision ID: c8e2fa41d7b9
Revises: b3f1c07d92ae
Create Date: 2026-08-13 20:10:00.000000

Deux ajouts :

  * la table `signalements`, qui porte les anomalies relevees sur une
    candidature ainsi que la decision humaine prise a leur sujet ;
  * la colonne `applications.cv_empreinte`, empreinte du texte du document.
    Elle permet de reperer un meme curriculum depose sous deux identites par
    simple comparaison d'index, la ou une comparaison deux a deux des textes
    couterait un temps quadratique.

La suppression d'une candidature entraine celle de ses signalements
(`ondelete=CASCADE`) : une observation sans son objet n'a plus de sens.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c8e2fa41d7b9'
down_revision = 'b3f1c07d92ae'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'applications',
        sa.Column('cv_empreinte', sa.String(length=64), nullable=True),
    )
    op.create_index(
        'ix_applications_cv_empreinte', 'applications', ['cv_empreinte'],
    )

    op.create_table(
        'signalements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=40), nullable=False),
        sa.Column('severite', sa.String(length=20), nullable=False,
                  server_default='attention'),
        sa.Column('message', sa.String(length=400), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('statut', sa.String(length=20), nullable=False,
                  server_default='nouveau'),
        sa.Column('commentaire', sa.String(length=400), nullable=True),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_signalements_application_id', 'signalements',
                    ['application_id'])
    op.create_index('ix_signalements_type', 'signalements', ['type'])
    op.create_index('ix_signalements_statut', 'signalements', ['statut'])
    op.create_index('ix_signalements_created_at', 'signalements', ['created_at'])


def downgrade():
    op.drop_index('ix_signalements_created_at', table_name='signalements')
    op.drop_index('ix_signalements_statut', table_name='signalements')
    op.drop_index('ix_signalements_type', table_name='signalements')
    op.drop_index('ix_signalements_application_id', table_name='signalements')
    op.drop_table('signalements')
    op.drop_index('ix_applications_cv_empreinte', table_name='applications')
    op.drop_column('applications', 'cv_empreinte')
