"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('total_chunks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('summary_embedding', Vector(768), nullable=True),
        sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR(), nullable=True),
        sa.Column('metadata', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on documents
    op.create_index('idx_documents_file_hash', 'documents', ['file_hash'])
    op.create_index('idx_documents_status', 'documents', ['status'])
    op.create_index('idx_documents_is_deleted', 'documents', ['is_deleted'])
    op.create_index('idx_documents_created_at', 'documents', ['created_at'])
    
    # Create chunks table
    op.create_table(
        'chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False, server_default='text'),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR(), nullable=True),
        sa.Column('metadata', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE')
    )
    
    # Create indexes on chunks
    op.create_index('idx_chunks_document_id', 'chunks', ['document_id'])
    op.create_index('idx_chunks_page_number', 'chunks', ['page_number'])
    op.create_index('idx_chunks_chunk_index', 'chunks', ['chunk_index'])
    
    # Create GIN index for full-text search on chunks
    op.execute(
        "CREATE INDEX idx_chunks_search_vector ON chunks USING GIN (search_vector)"
    )
    
    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('active_branch', sa.String(100), nullable=False, server_default='main'),
        sa.Column('branches', sa.dialects.postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settings', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on chats
    op.create_index('idx_chats_is_deleted', 'chats', ['is_deleted'])
    op.create_index('idx_chats_updated_at', 'chats', ['updated_at'])
    op.create_index('idx_chats_last_message_at', 'chats', ['last_message_at'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.UUID(), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('branch', sa.String(100), nullable=False, server_default='main'),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False, server_default='text'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('tool_name', sa.String(100), nullable=True),
        sa.Column('tool_params', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('tool_call_id', sa.String(100), nullable=True),
        sa.Column('attachments', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('sources', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('metadata', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['messages.id'], ondelete='SET NULL')
    )
    
    # Create indexes on messages
    op.create_index('idx_messages_chat_id', 'messages', ['chat_id'])
    op.create_index('idx_messages_parent_id', 'messages', ['parent_id'])
    op.create_index('idx_messages_branch', 'messages', ['branch'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])
    op.create_index('idx_messages_is_deleted', 'messages', ['is_deleted'])


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('chats')
    op.drop_table('chunks')
    op.drop_table('documents')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
    op.execute('DROP EXTENSION IF EXISTS vector')
