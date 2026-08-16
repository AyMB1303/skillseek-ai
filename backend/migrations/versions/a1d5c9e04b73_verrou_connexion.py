"""Verrou temporaire du compte apres echecs de connexion repetes.

Le compteur d'echecs existait deja et servait a prevenir le titulaire du
compte. Il n'empechait rien : un essai systematique de mots de passe pouvait
se poursuivre indefiniment. Cette colonne porte l'instant jusqu'auquel les
tentatives sont refusees.

Nullable sans valeur par defaut : l'absence de verrou est l'etat normal, et
`NULL` l'exprime plus justement qu'une date passee arbitraire.

Revision ID: a1d5c9e04b73
Revises: f2b8a17c4d90
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1d5c9e04b73'
down_revision = 'f2b8a17c4d90'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'locked_until')
