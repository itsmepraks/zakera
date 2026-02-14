"""
Custom metrics for conversation and database monitoring.

This module provides detailed metrics collection for:
- Conversation lifecycle
- Message persistence
- Database operations
- Search performance
- User activity
"""
from prometheus_client import Counter, Histogram, Gauge, Summary
from typing import Optional
import time
from contextlib import contextmanager

# ============================================================================
# Conversation Metrics
# ============================================================================

# Conversation lifecycle
conversations_created = Counter(
    'zakera_conversations_created_total',
    'Total conversations created',
    ['model', 'has_system_prompt']
)

conversations_started = Counter(
    'zakera_conversations_started_total',
    'Total conversations started (first message)',
    ['model']
)

conversations_completed = Counter(
    'zakera_conversations_completed_total',
    'Total conversations completed successfully',
    ['model']
)

conversations_failed = Counter(
    'zakera_conversations_failed_total',
    'Total conversations failed',
    ['model', 'error_type']
)

conversations_archived = Counter(
    'zakera_conversations_archived_total',
    'Total conversations archived'
)

conversations_deleted = Counter(
    'zakera_conversations_deleted_total',
    'Total conversations deleted',
    ['hard_delete']
)

conversations_active = Gauge(
    'zakera_conversations_active_total',
    'Current number of active conversations'
)

conversation_duration = Histogram(
    'zakera_conversation_duration_seconds',
    'Time from first to last message in conversation',
    buckets=[10, 30, 60, 300, 600, 1800, 3600, 7200]
)

conversation_messages_count = Histogram(
    'zakera_conversation_messages_count',
    'Number of messages per conversation',
    buckets=[1, 5, 10, 20, 50, 100, 200, 500]
)

conversation_load_duration = Histogram(
    'zakera_conversation_load_duration_seconds',
    'Time to load conversation from database',
    ['has_messages'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

conversation_token_limit_exceeded = Counter(
    'zakera_conversation_token_limit_exceeded_total',
    'Number of times token limit was exceeded',
    ['model']
)

conversations_by_tag = Gauge(
    'zakera_conversations_by_tag',
    'Number of conversations by tag',
    ['tag']
)

# ============================================================================
# Message Metrics
# ============================================================================

messages_total = Counter(
    'zakera_messages_total',
    'Total messages created',
    ['role', 'model']
)

messages_successful = Counter(
    'zakera_messages_successful_total',
    'Total successful messages',
    ['role', 'model']
)

messages_failed = Counter(
    'zakera_messages_failed_total',
    'Total failed messages',
    ['role', 'model', 'error_type']
)

message_save_duration = Histogram(
    'zakera_message_save_duration_seconds',
    'Time to save message to database',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

message_save_errors = Counter(
    'zakera_message_save_errors_total',
    'Total message save errors',
    ['error_type']
)

message_length = Histogram(
    'zakera_message_length_characters',
    'Message length in characters',
    ['role'],
    buckets=[10, 50, 100, 500, 1000, 5000, 10000]
)

# ============================================================================
# Database Metrics
# ============================================================================

db_queries_total = Counter(
    'zakera_db_queries_total',
    'Total database queries',
    ['operation', 'table']
)

db_query_duration = Histogram(
    'zakera_db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

db_connections_active = Gauge(
    'zakera_db_connections_active',
    'Number of active database connections'
)

db_connections_idle = Gauge(
    'zakera_db_connections_idle',
    'Number of idle database connections'
)

db_connections_overflow = Gauge(
    'zakera_db_connections_overflow',
    'Number of overflow database connections'
)

db_pool_size = Gauge(
    'zakera_db_pool_size',
    'Database connection pool size'
)

db_transactions_total = Counter(
    'zakera_db_transactions_total',
    'Total database transactions'
)

db_transactions_committed = Counter(
    'zakera_db_transactions_committed_total',
    'Total committed transactions'
)

db_transactions_rolled_back = Counter(
    'zakera_db_transactions_rolled_back_total',
    'Total rolled back transactions'
)

db_errors = Counter(
    'zakera_db_errors_total',
    'Database errors',
    ['error_type', 'operation']
)

db_size_bytes = Gauge(
    'zakera_db_size_bytes',
    'Database size in bytes'
)

db_table_rows = Gauge(
    'zakera_db_table_rows',
    'Number of rows in table',
    ['table']
)

db_cache_hits = Counter(
    'zakera_db_cache_hits_total',
    'Database query cache hits'
)

db_cache_misses = Counter(
    'zakera_db_cache_misses_total',
    'Database query cache misses'
)

# ============================================================================
# Search Metrics
# ============================================================================

search_queries_total = Counter(
    'zakera_search_queries_total',
    'Total search queries',
    ['search_type']  # messages, conversations, all
)

search_duration = Histogram(
    'zakera_search_duration_seconds',
    'Search query duration',
    ['search_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

search_results_count = Histogram(
    'zakera_search_results_count',
    'Number of search results returned',
    ['search_type'],
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

search_no_results = Counter(
    'zakera_search_no_results_total',
    'Searches returning no results',
    ['search_type']
)

# ============================================================================
# User Activity Metrics
# ============================================================================

active_users = Gauge(
    'zakera_active_users_total',
    'Number of active users in last 5 minutes'
)

user_sessions_active = Gauge(
    'zakera_user_sessions_active',
    'Number of active user sessions'
)

user_sessions_created = Counter(
    'zakera_user_sessions_created_total',
    'Total user sessions created'
)

user_sessions_expired = Counter(
    'zakera_user_sessions_expired_total',
    'Total user sessions expired'
)

# ============================================================================
# Sharing Metrics
# ============================================================================

shares_created = Counter(
    'zakera_shares_created_total',
    'Total shares created',
    ['is_public']
)

shares_accessed = Counter(
    'zakera_shares_accessed_total',
    'Total share accesses',
    ['is_public']
)

share_creation_errors = Counter(
    'zakera_share_creation_errors_total',
    'Share creation errors',
    ['error_type']
)

# ============================================================================
# Bulk Operations Metrics
# ============================================================================

bulk_operations_total = Counter(
    'zakera_bulk_operations_total',
    'Total bulk operations',
    ['operation_type']  # archive, delete
)

bulk_operation_items = Histogram(
    'zakera_bulk_operation_items_count',
    'Number of items in bulk operation',
    ['operation_type'],
    buckets=[1, 5, 10, 20, 50, 100]
)

bulk_operation_duration = Histogram(
    'zakera_bulk_operation_duration_seconds',
    'Bulk operation duration',
    ['operation_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

bulk_operation_errors = Counter(
    'zakera_bulk_operation_errors_total',
    'Bulk operation errors',
    ['operation_type', 'error_type']
)

# ============================================================================
# Memory System Metrics
# ============================================================================

memory_cache_hits = Counter(
    'zakera_memory_cache_hits_total',
    'Memory system cache hits'
)

memory_cache_misses = Counter(
    'zakera_memory_cache_misses_total',
    'Memory system cache misses'
)

memory_load_duration = Histogram(
    'zakera_memory_load_duration_seconds',
    'Time to load conversation into memory',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

# ============================================================================
# Helper Functions and Context Managers
# ============================================================================

@contextmanager
def track_conversation_creation(model: str, has_system_prompt: bool):
    """Context manager to track conversation creation."""
    start_time = time.time()
    try:
        yield
        conversations_created.labels(
            model=model,
            has_system_prompt=str(has_system_prompt)
        ).inc()
    except Exception as e:
        conversations_failed.labels(
            model=model,
            error_type=type(e).__name__
        ).inc()
        raise
    finally:
        duration = time.time() - start_time
        # Track creation time if needed

@contextmanager
def track_message_save(role: str, model: str):
    """Context manager to track message saving."""
    start_time = time.time()
    try:
        yield
        messages_successful.labels(role=role, model=model).inc()
    except Exception as e:
        messages_failed.labels(
            role=role,
            model=model,
            error_type=type(e).__name__
        ).inc()
        message_save_errors.labels(error_type=type(e).__name__).inc()
        raise
    finally:
        duration = time.time() - start_time
        message_save_duration.observe(duration)

@contextmanager
def track_db_query(operation: str, table: str):
    """Context manager to track database queries."""
    start_time = time.time()
    try:
        yield
        db_queries_total.labels(operation=operation, table=table).inc()
    except Exception as e:
        db_errors.labels(
            error_type=type(e).__name__,
            operation=operation
        ).inc()
        raise
    finally:
        duration = time.time() - start_time
        db_query_duration.labels(operation=operation, table=table).observe(duration)

@contextmanager
def track_search(search_type: str):
    """Context manager to track search operations."""
    start_time = time.time()
    results_count = None
    try:
        yield lambda count: nonlocal_setter(count)
        search_queries_total.labels(search_type=search_type).inc()
    finally:
        duration = time.time() - start_time
        search_duration.labels(search_type=search_type).observe(duration)

def nonlocal_setter(count):
    """Helper for setting results count in context manager."""
    search_results_count.labels(search_type=search_type).observe(count)
    if count == 0:
        search_no_results.labels(search_type=search_type).inc()

@contextmanager
def track_bulk_operation(operation_type: str, item_count: int):
    """Context manager to track bulk operations."""
    start_time = time.time()
    try:
        yield
        bulk_operations_total.labels(operation_type=operation_type).inc()
        bulk_operation_items.labels(operation_type=operation_type).observe(item_count)
    except Exception as e:
        bulk_operation_errors.labels(
            operation_type=operation_type,
            error_type=type(e).__name__
        ).inc()
        raise
    finally:
        duration = time.time() - start_time
        bulk_operation_duration.labels(operation_type=operation_type).observe(duration)

def update_active_conversations(count: int):
    """Update active conversations gauge."""
    conversations_active.set(count)

def update_active_users(count: int):
    """Update active users gauge."""
    active_users.set(count)

def update_db_pool_stats(active: int, idle: int, overflow: int, size: int):
    """Update database connection pool statistics."""
    db_connections_active.set(active)
    db_connections_idle.set(idle)
    db_connections_overflow.set(overflow)
    db_pool_size.set(size)

def update_table_rows(table: str, count: int):
    """Update table row count."""
    db_table_rows.labels(table=table).set(count)

def update_db_size(size_bytes: int):
    """Update database size."""
    db_size_bytes.set(size_bytes)

def track_conversation_tag(tag: str, count: int):
    """Track conversations by tag."""
    conversations_by_tag.labels(tag=tag).set(count)
