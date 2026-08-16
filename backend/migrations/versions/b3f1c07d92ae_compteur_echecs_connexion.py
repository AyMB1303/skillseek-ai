"""compteur d'echecs de connexion

Revision ID: b3f1c07d92ae
Revises: 67a28927ae20
Create Date: 2026-08-11 09:40:00.000000

Le compteur porte sur le compte vise, non sur l'auteur des tentatives : il
permet d'avertir le titulaire d'un compte pris pour cible sans rien reveler
a qui essaie de deviner un mot de passe.

Le `server_default` est indispensable : PostgreSQL refuse d'ajouter une
colonne NOT NULL a une table peuplee sans valeur par defaut.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b3f1c07d92ae'
down_revision = '67a28927ae20'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('failed_logins', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade():
    op.drop_column('users', 'failed_logins')
