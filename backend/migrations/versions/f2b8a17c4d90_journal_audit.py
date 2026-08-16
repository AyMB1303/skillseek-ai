"""journal d'audit

Revision ID: f2b8a17c4d90
Revises: e7c3d0a94f18
Create Date: 2026-08-14 00:20:00.000000

L'objet vise est decrit par un couple type/identifiant plutot que par une cle
etrangere. Une cle etrangere imposerait la suppression en cascade des traces
lorsque l'objet disparait — exactement l'inverse de ce qu'on attend d'un
audit : c'est souvent apres la suppression qu'on a besoin de savoir qui l'a
ordonnee.

Le nom de l'auteur est recopie a cote de sa cle : si le compte est efface, la
trace reste lisible plutot que de renvoyer un identifiant orphelin.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f2b8a17c4d90'
down_revision = 'e7c3d0a94f18'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'journal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=40), nullable=False),
        sa.Column('objet_type', sa.String(length=30), nullable=True),
        sa.Column('objet_id', sa.Integer(), nullable=True),
        sa.Column('objet_libelle', sa.String(length=200), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('auteur_id', sa.Integer(), nullable=True),
        sa.Column('auteur_nom', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['auteur_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_journal_action', 'journal', ['action'])
    op.create_index('ix_journal_objet_type', 'journal', ['objet_type'])
    op.create_index('ix_journal_objet_id', 'journal', ['objet_id'])
    op.create_index('ix_journal_created_at', 'journal', ['created_at'])


def downgrade():
    op.drop_index('ix_journal_created_at', table_name='journal')
    op.drop_index('ix_journal_objet_id', table_name='journal')
    op.drop_index('ix_journal_objet_type', table_name='journal')
    op.drop_index('ix_journal_action', table_name='journal')
    op.drop_table('journal')
