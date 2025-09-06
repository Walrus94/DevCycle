"""Stub file for confluent_kafka.admin module."""

from typing import Any, Dict, List, Optional, Union

class AdminClient:
    def __init__(self, config: Dict[str, Any]) -> None: ...
    def create_topics(self, topics: List[Any], **kwargs: Any) -> Any: ...
    def delete_topics(self, topics: List[Any], **kwargs: Any) -> Any: ...
    def list_topics(self, **kwargs: Any) -> Any: ...
    def close(self) -> None: ...

class NewTopic:
    def __init__(
        self,
        topic: str,
        num_partitions: int = 1,
        replication_factor: int = 1,
        replica_assignment: Optional[Dict[int, List[int]]] = None,
        config: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None: ...

class NewPartitions:
    def __init__(
        self,
        topic: str,
        new_total_count: int,
        replica_assignment: Optional[Dict[int, List[int]]] = None,
        **kwargs: Any,
    ) -> None: ...

class ConfigResource:
    def __init__(
        self,
        restype: int,
        name: str,
        configs: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None: ...

class ResourceType:
    BROKER: int
    TOPIC: int
    GROUP: int
    CLUSTER: int
    # ... other constants
