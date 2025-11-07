"""add_session_support

Revision ID: 7c123436cb2e
Revises: b927dc021cd7
Create Date: 2025-11-05 09:25:49.302433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c123436cb2e'
down_revision: Union[str, None] = 'b927dc021cd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sessions table first (if it doesn't exist)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'sessions' not in tables:
        op.create_table(
            'sessions',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_accessed', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
    
    # Create a default session for existing data (if needed)
    import uuid
    from datetime import datetime
    result = conn.execute(sa.text("SELECT COUNT(*) FROM sessions")).scalar()
    if result == 0:
        default_session_id = str(uuid.uuid4())
        conn.execute(sa.text(f"""
            INSERT INTO sessions (id, name, created_at, last_accessed)
            VALUES ('{default_session_id}', 'Default Session', '{datetime.utcnow().isoformat()}', '{datetime.utcnow().isoformat()}')
        """))
        conn.commit()
        default_session_id_for_migration = default_session_id
    else:
        # Get existing session ID
        result = conn.execute(sa.text("SELECT id FROM sessions LIMIT 1")).fetchone()
        default_session_id_for_migration = result[0] if result else str(uuid.uuid4())
    
    # Add session_id columns (nullable first) - only if they don't exist
    for table_name in ['agents', 'links', 'runs']:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        if 'session_id' not in columns:
            op.add_column(table_name, sa.Column('session_id', sa.String(), nullable=True))
    
    # Migrate existing data to default session
    op.execute(sa.text(f"UPDATE agents SET session_id = '{default_session_id_for_migration}' WHERE session_id IS NULL"))
    op.execute(sa.text(f"UPDATE links SET session_id = '{default_session_id_for_migration}' WHERE session_id IS NULL"))
    op.execute(sa.text(f"UPDATE runs SET session_id = '{default_session_id_for_migration}' WHERE session_id IS NULL"))
    
    # Make columns non-nullable and add constraints (only if columns exist and are nullable)
    for table_name in ['agents', 'links', 'runs']:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        if 'session_id' in columns:
            # Check if nullable
            col_info = next((col for col in inspector.get_columns(table_name) if col['name'] == 'session_id'), None)
            if col_info and col_info.get('nullable', True):
                # Migrate NULL values first
                op.execute(sa.text(f"UPDATE {table_name} SET session_id = '{default_session_id_for_migration}' WHERE session_id IS NULL"))
                op.alter_column(table_name, 'session_id', nullable=False)
            
            # Create index if it doesn't exist
            indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
            index_name = f'ix_{table_name}_session_id'
            if index_name not in indexes:
                op.create_index(index_name, table_name, ['session_id'], unique=False)
            
            # Create foreign key if it doesn't exist
            fk_name = f'fk_{table_name}_session_id'
            fks = [fk['name'] for fk in inspector.get_foreign_keys(table_name)]
            if fk_name not in fks:
                op.create_foreign_key(fk_name, table_name, 'sessions', ['session_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Drop foreign keys and indexes
    op.drop_constraint('fk_runs_session_id', 'runs', type_='foreignkey')
    op.drop_index('ix_runs_session_id', table_name='runs')
    op.drop_column('runs', 'session_id')
    op.drop_constraint('fk_links_session_id', 'links', type_='foreignkey')
    op.drop_index('ix_links_session_id', table_name='links')
    op.drop_column('links', 'session_id')
    op.drop_constraint('fk_agents_session_id', 'agents', type_='foreignkey')
    op.drop_index('ix_agents_session_id', table_name='agents')
    op.drop_column('agents', 'session_id')
    
    # Drop sessions table
    op.drop_table('sessions')
