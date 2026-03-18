"""initial_tables

Revision ID: 36fc86e37717
Revises: 
Create Date: 2026-03-14 15:04:15.244526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '36fc86e37717'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('hashed_password', sa.String(length=200), nullable=False),
    sa.Column('tier', sa.String(length=20), nullable=False),
    sa.Column('preferred_stack', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table('sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('project_name', sa.String(length=200), nullable=False),
    sa.Column('prd_content', sa.Text(), nullable=False),
    sa.Column('chosen_stack', sa.String(length=200), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('pr_url', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)

    op.create_table('hitl_decisions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('checkpoint_name', sa.String(length=100), nullable=False),
    sa.Column('user_decision', sa.Boolean(), nullable=False),
    sa.Column('user_feedback', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hitl_decisions_session_id'), 'hitl_decisions', ['session_id'], unique=False)

    op.create_table('message_history',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('agent_name', sa.String(length=100), nullable=True),
    sa.Column('token_count', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_history_session_id'), 'message_history', ['session_id'], unique=False)

    op.create_table('reflexion_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('retry_number', sa.Integer(), nullable=False),
    sa.Column('error_type', sa.String(length=100), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=False),
    sa.Column('fix_applied', sa.Text(), nullable=False),
    sa.Column('was_successful', sa.Boolean(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reflexion_logs_session_id'), 'reflexion_logs', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reflexion_logs_session_id'), table_name='reflexion_logs')
    op.drop_table('reflexion_logs')
    op.drop_index(op.f('ix_message_history_session_id'), table_name='message_history')
    op.drop_table('message_history')
    op.drop_index(op.f('ix_hitl_decisions_session_id'), table_name='hitl_decisions')
    op.drop_table('hitl_decisions')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')