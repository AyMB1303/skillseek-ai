"""origine et auteur d'un signalement

Revision ID: d4a91b6e35c2
Revises: c8e2fa41d7b9
Create Date: 2026-08-13 21:40:00.000000

Un signalement peut desormais etre ouvert a la main par un recruteur. Deux
colonnes distinguent ce cas :

  * `origine` — « automatique » ou « manuel ». La distinction n'est pas
    cosmetique : elle permet de mesurer ce que les controles automatiques
    laissent passer, en comptant les anomalies que seuls des humains ont vues.
  * `created_by_id` — l'auteur. Un controle automatique n'engage personne ;
    une observation humaine engage celui qui la porte, et doit donc etre
    attribuee.

Les lignes existantes prennent « automatique » par defaut, ce qui correspond
a leur origine reelle.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4a91b6e35c2'
down_revision = 'c8e2fa41d7b9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'signalements',
        sa.Column('origine', sa.String(length=20), nullable=False,
                  server_default='automatique'),
    )
    op.add_column(
        'signalements',
        sa.Column('created_by_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_signalements_created_by', 'signalements', 'users',
        ['created_by_id'], ['id'],
    )


def downgrade():
    op.drop_constraint('fk_signalements_created_by', 'signalements',
                       type_='foreignkey')
    op.drop_column('signalements', 'created_by_id')
    op.drop_column('signalements', 'origine')
