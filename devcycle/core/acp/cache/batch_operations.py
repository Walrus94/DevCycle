"""
Redis batch operations for improved performance.

This module provides efficient batch operations for Redis to reduce
network round trips and improve overall performance.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ...cache.acp_cache import ACPCache
from ...logging import get_logger

logger = get_logger(__name__)


class BatchOperationType(Enum):
    """Types of batch operations."""

    GET = "get"
    SET = "set"
    DELETE = "delete"
    EXISTS = "exists"
    EXPIRE = "expire"
    TTL = "ttl"


@dataclass
class BatchOperation:
    """Represents a single batch operation."""

    operation_type: BatchOperationType
    key: str
    value: Optional[Any] = None
    ttl: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class BatchResult:
    """Result of a batch operation."""

    operations: List[BatchOperation]
    total_operations: int
    successful_operations: int
    failed_operations: int
    execution_time_ms: float
    throughput_ops_per_second: float


class RedisBatchProcessor:
    """High-performance Redis batch operations processor."""

    def __init__(
        self,
        acp_cache: ACPCache,
        batch_size: int = 100,
        max_concurrent_batches: int = 10,
    ):
        """
        Initialize batch processor.

        Args:
            acp_cache: ACP cache instance
            batch_size: Maximum operations per batch
            max_concurrent_batches: Maximum concurrent batch operations
        """
        self.acp_cache = acp_cache
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.semaphore = asyncio.Semaphore(max_concurrent_batches)

        # Performance tracking
        self.total_batches_processed = 0
        self.total_operations_processed = 0
        self.average_batch_time_ms = 0.0
        self.average_throughput_ops_per_second = 0.0

    async def execute_batch(self, operations: List[BatchOperation]) -> BatchResult:
        """Execute a batch of operations."""
        if not operations:
            return BatchResult(
                operations=[],
                total_operations=0,
                successful_operations=0,
                failed_operations=0,
                execution_time_ms=0.0,
                throughput_ops_per_second=0.0,
            )

        start_time = datetime.now(timezone.utc)

        # Split operations into batches
        batches = self._split_into_batches(operations)

        # Execute batches concurrently
        batch_results = await asyncio.gather(
            *[self._execute_single_batch(batch) for batch in batches],
            return_exceptions=True,
        )

        # Combine results
        all_operations: List[BatchOperation] = []
        successful_ops = 0
        failed_ops = 0

        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch execution failed: {result}")
                failed_ops += len(operations)  # Assume all failed
            else:
                if isinstance(result, list):
                    all_operations.extend(result)
                    successful_ops += len([op for op in result if op.error is None])
                    failed_ops += len([op for op in result if op.error is not None])

        end_time = datetime.now(timezone.utc)
        execution_time_ms = (end_time - start_time).total_seconds() * 1000
        throughput = (
            (len(operations) / execution_time_ms * 1000) if execution_time_ms > 0 else 0
        )

        # Update performance statistics
        self._update_performance_stats(len(operations), execution_time_ms)

        return BatchResult(
            operations=all_operations,
            total_operations=len(operations),
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            execution_time_ms=execution_time_ms,
            throughput_ops_per_second=throughput,
        )

    def _split_into_batches(
        self, operations: List[BatchOperation]
    ) -> List[List[BatchOperation]]:
        """Split operations into batches of appropriate size."""
        batches = []
        for i in range(0, len(operations), self.batch_size):
            batches.append(operations[i : i + self.batch_size])
        return batches

    async def _execute_single_batch(
        self, operations: List[BatchOperation]
    ) -> List[BatchOperation]:
        """Execute a single batch of operations."""
        async with self.semaphore:
            # Group operations by type for efficiency
            grouped_ops = self._group_operations_by_type(operations)

            # Execute each group
            for op_type, ops in grouped_ops.items():
                await self._execute_operation_group(op_type, ops)

            return operations

    def _group_operations_by_type(
        self, operations: List[BatchOperation]
    ) -> Dict[BatchOperationType, List[BatchOperation]]:
        """Group operations by type for efficient execution."""
        grouped: Dict[BatchOperationType, List[BatchOperation]] = {}
        for op in operations:
            if op.operation_type not in grouped:
                grouped[op.operation_type] = []
            grouped[op.operation_type].append(op)
        return grouped

    async def _execute_operation_group(
        self, op_type: BatchOperationType, operations: List[BatchOperation]
    ) -> None:
        """Execute a group of operations of the same type."""
        if op_type == BatchOperationType.GET:
            await self._execute_get_operations(operations)
        elif op_type == BatchOperationType.SET:
            await self._execute_set_operations(operations)
        elif op_type == BatchOperationType.DELETE:
            await self._execute_delete_operations(operations)
        elif op_type == BatchOperationType.EXISTS:
            await self._execute_exists_operations(operations)
        elif op_type == BatchOperationType.EXPIRE:
            await self._execute_expire_operations(operations)
        elif op_type == BatchOperationType.TTL:
            await self._execute_ttl_operations(operations)

    async def _execute_get_operations(self, operations: List[BatchOperation]) -> None:
        """Execute GET operations in batch."""
        keys = [op.key for op in operations]

        try:
            # Use Redis MGET for multiple keys
            values = self.acp_cache.redis.redis_client.mget(keys)

            for i, op in enumerate(operations):
                op.result = values[i] if i < len(values) else None
                if op.result is None:
                    op.error = "Key not found"

        except Exception as e:
            for op in operations:
                op.error = str(e)

    async def _execute_set_operations(self, operations: List[BatchOperation]) -> None:
        """Execute SET operations in batch."""
        try:
            # Use Redis pipeline for multiple SET operations
            pipe = self.acp_cache.redis.redis_client.pipeline()

            for op in operations:
                # Serialize value for Redis
                if isinstance(op.value, str):
                    serialized_value = op.value
                else:
                    import json

                    serialized_value = json.dumps(op.value)

                if op.ttl:
                    pipe.setex(op.key, int(op.ttl), serialized_value)
                else:
                    pipe.set(op.key, serialized_value)

            results = pipe.execute()

            for i, op in enumerate(operations):
                op.result = results[i] if i < len(results) else None
                if not op.result:
                    op.error = "Set operation failed"

        except Exception as e:
            for op in operations:
                op.error = str(e)

    async def _execute_delete_operations(
        self, operations: List[BatchOperation]
    ) -> None:
        """Execute DELETE operations in batch."""
        keys = [op.key for op in operations]

        try:
            # Use Redis DEL for multiple keys
            deleted_count = self.acp_cache.redis.delete(*keys)

            for i, op in enumerate(operations):
                op.result = deleted_count > i
                if not op.result:
                    op.error = "Delete operation failed"

        except Exception as e:
            for op in operations:
                op.error = str(e)

    async def _execute_exists_operations(
        self, operations: List[BatchOperation]
    ) -> None:
        """Execute EXISTS operations in batch."""
        keys = [op.key for op in operations]

        try:
            # Use Redis EXISTS for multiple keys
            exists_count = self.acp_cache.redis.exists(*keys)

            for i, op in enumerate(operations):
                op.result = exists_count > i

        except Exception as e:
            for op in operations:
                op.error = str(e)

    async def _execute_expire_operations(
        self, operations: List[BatchOperation]
    ) -> None:
        """Execute EXPIRE operations in batch."""
        try:
            # Use Redis pipeline for multiple EXPIRE operations
            pipe = self.acp_cache.redis.redis_client.pipeline()

            for op in operations:
                pipe.expire(op.key, int(op.ttl) if op.ttl else 0)

            results = pipe.execute()

            for i, op in enumerate(operations):
                op.result = results[i] if i < len(results) else False
                if not op.result:
                    op.error = "Expire operation failed"

        except Exception as e:
            for op in operations:
                op.error = str(e)

    async def _execute_ttl_operations(self, operations: List[BatchOperation]) -> None:
        """Execute TTL operations in batch."""
        try:
            # Use Redis pipeline for multiple TTL operations
            pipe = self.acp_cache.redis.redis_client.pipeline()

            for op in operations:
                pipe.ttl(op.key)

            results = pipe.execute()

            for i, op in enumerate(operations):
                op.result = results[i] if i < len(results) else -1

        except Exception as e:
            for op in operations:
                op.error = str(e)

    def _update_performance_stats(
        self, operation_count: int, execution_time_ms: float
    ) -> None:
        """Update performance statistics."""
        self.total_batches_processed += 1
        self.total_operations_processed += operation_count

        # Update running averages
        if self.total_batches_processed == 1:
            self.average_batch_time_ms = execution_time_ms
            self.average_throughput_ops_per_second = (
                operation_count / (execution_time_ms / 1000)
                if execution_time_ms > 0
                else 0
            )
        else:
            # Exponential moving average
            alpha = 0.1
            self.average_batch_time_ms = (
                alpha * execution_time_ms + (1 - alpha) * self.average_batch_time_ms
            )
            current_throughput = (
                operation_count / (execution_time_ms / 1000)
                if execution_time_ms > 0
                else 0
            )
            self.average_throughput_ops_per_second = (
                alpha * current_throughput
                + (1 - alpha) * self.average_throughput_ops_per_second
            )

    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "total_batches_processed": self.total_batches_processed,
            "total_operations_processed": self.total_operations_processed,
            "average_batch_time_ms": self.average_batch_time_ms,
            "average_throughput_ops_per_second": self.average_throughput_ops_per_second,
            "batch_size": self.batch_size,
            "max_concurrent_batches": self.max_concurrent_batches,
        }

    def set_batch_size(self, batch_size: int) -> None:
        """Set batch size."""
        self.batch_size = batch_size
        logger.info(f"Batch size set to {batch_size}")

    def set_max_concurrent_batches(self, max_concurrent: int) -> None:
        """Set maximum concurrent batches."""
        self.max_concurrent_batches = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"Max concurrent batches set to {max_concurrent}")


# Convenience functions for common batch operations
async def batch_get(processor: RedisBatchProcessor, keys: List[str]) -> BatchResult:
    """Execute batch GET operations."""
    operations = [BatchOperation(BatchOperationType.GET, key) for key in keys]
    return await processor.execute_batch(operations)


async def batch_set(
    processor: RedisBatchProcessor,
    key_value_pairs: List[Tuple[str, Any]],
    ttl: Optional[float] = None,
) -> BatchResult:
    """Execute batch SET operations."""
    operations = [
        BatchOperation(BatchOperationType.SET, key, value, ttl)
        for key, value in key_value_pairs
    ]
    return await processor.execute_batch(operations)


async def batch_delete(processor: RedisBatchProcessor, keys: List[str]) -> BatchResult:
    """Execute batch DELETE operations."""
    operations = [BatchOperation(BatchOperationType.DELETE, key) for key in keys]
    return await processor.execute_batch(operations)


async def batch_exists(processor: RedisBatchProcessor, keys: List[str]) -> BatchResult:
    """Execute batch EXISTS operations."""
    operations = [BatchOperation(BatchOperationType.EXISTS, key) for key in keys]
    return await processor.execute_batch(operations)
