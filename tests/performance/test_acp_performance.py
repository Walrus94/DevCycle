"""
ACP Performance Tests.

Tests ACP system performance including message throughput, response times,
and concurrent processing capabilities.
"""

import asyncio
import statistics
import time

import pytest

from devcycle.core.acp.agents.business_analyst_agent import BusinessAnalystACPAgent
from devcycle.core.acp.agents.testing_agent import TestingACPAgent
from devcycle.core.acp.models import ACPMessage, ACPResponse
from devcycle.core.acp.services.agent_registry import ACPAgentRegistry
from devcycle.core.acp.services.message_router import ACPMessageRouter


class TestACPPerformance:
    """Test ACP system performance."""

    @pytest.fixture
    async def performance_registry(self):
        """Create agent registry for performance testing."""
        registry = ACPAgentRegistry()

        # Register multiple agents for load testing
        for i in range(5):
            agent = BusinessAnalystACPAgent()
            agent.agent_id = f"business-analyst-{i}"
            await registry.register_agent(agent)

        for i in range(5):
            agent = TestingACPAgent()
            agent.agent_id = f"testing-agent-{i}"
            await registry.register_agent(agent)

        return registry

    @pytest.fixture
    async def performance_router(self, performance_registry):
        """Create message router for performance testing."""
        return ACPMessageRouter(performance_registry)

    @pytest.mark.asyncio
    async def test_message_throughput(self, performance_router):
        """Test ACP message throughput performance."""
        # Create test messages
        messages = []
        for i in range(100):
            message = ACPMessage(
                message_id=f"perf-test-{i}",
                message_type="analyze_requirements",
                source_agent_id="test-sender",
                target_agent_id="business-analyst-0",
                content={"requirements": f"Performance test requirement {i}"},
            )
            messages.append(message)

        # Measure throughput
        start_time = time.time()

        # Process messages concurrently
        tasks = [performance_router.route_message(msg) for msg in messages]
        responses = await asyncio.gather(*tasks)

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify all messages were processed successfully
        assert len(responses) == 100
        success_count = sum(1 for response in responses if response.success)
        success_rate = success_count / len(responses)

        # Performance assertions
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95%"
        assert (
            processing_time < 10.0
        ), f"Processing time {processing_time:.2f}s exceeds 10s"

        # Calculate throughput
        throughput = len(messages) / processing_time
        print(f"Processed {len(messages)} messages in {processing_time:.2f}s")
        print(f"Throughput: {throughput:.2f} messages/second")
        print(f"Success rate: {success_rate:.2%}")

        # Assert minimum throughput
        assert throughput >= 10.0, f"Throughput {throughput:.2f} msg/s below 10 msg/s"

    @pytest.mark.asyncio
    async def test_response_time_distribution(self, performance_router):
        """Test response time distribution and consistency."""
        # Create test messages
        messages = []
        for i in range(50):
            message = ACPMessage(
                message_id=f"response-test-{i}",
                message_type="analyze_requirements",
                source_agent_id="test-sender",
                target_agent_id="business-analyst-0",
                content={"requirements": f"Response time test {i}"},
            )
            messages.append(message)

        # Measure individual response times
        response_times = []

        for message in messages:
            start_time = time.time()
            response = await performance_router.route_message(message)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            response_times.append(response_time)

            assert response.success, f"Message {message.message_id} failed"

        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        median_response_time = statistics.median(response_times)
        p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
        p99_response_time = sorted(response_times)[int(0.99 * len(response_times))]

        print("Response time statistics (ms):")
        print(f"  Average: {avg_response_time:.2f}")
        print(f"  Median: {median_response_time:.2f}")
        print(f"  95th percentile: {p95_response_time:.2f}")
        print(f"  99th percentile: {p99_response_time:.2f}")

        # Performance assertions
        assert (
            avg_response_time < 1000
        ), f"Average response time {avg_response_time:.2f}ms exceeds 1000ms"
        assert (
            p95_response_time < 2000
        ), f"95th percentile {p95_response_time:.2f}ms exceeds 2000ms"
        assert (
            p99_response_time < 5000
        ), f"99th percentile {p99_response_time:.2f}ms exceeds 5000ms"

    @pytest.mark.asyncio
    async def test_concurrent_agent_processing(self, performance_registry):
        """Test concurrent processing across multiple agents."""
        # Create messages for different agents
        messages = []
        for i in range(20):
            # Alternate between business analyst and testing agents
            agent_id = (
                f"business-analyst-{i % 5}" if i % 2 == 0 else f"testing-agent-{i % 5}"
            )
            message_type = "analyze_requirements" if i % 2 == 0 else "generate_tests"

            message = ACPMessage(
                message_id=f"concurrent-test-{i}",
                message_type=message_type,
                source_agent_id="test-sender",
                target_agent_id=agent_id,
                content={"data": f"Concurrent test {i}"},
            )
            messages.append(message)

        # Process messages concurrently
        start_time = time.time()

        tasks = []
        for message in messages:
            agent = performance_registry.agents.get(message.target_agent_id)
            if agent:
                task = agent.handle_message(message)
                tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        processing_time = end_time - start_time

        # Count successful responses
        success_count = sum(
            1
            for response in responses
            if isinstance(response, ACPResponse) and response.success
        )
        success_rate = success_count / len(responses)

        print(f"Concurrent processing: {len(messages)} messages across 10 agents")
        print(f"Processing time: {processing_time:.2f}s")
        print(f"Success rate: {success_rate:.2%}")

        # Performance assertions
        assert success_rate >= 0.90, f"Success rate {success_rate:.2%} below 90%"
        assert (
            processing_time < 5.0
        ), f"Processing time {processing_time:.2f}s exceeds 5s"

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_router):
        """Test memory usage under sustained load."""
        import os

        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process many messages
        messages = []
        for i in range(500):
            message = ACPMessage(
                message_id=f"memory-test-{i}",
                message_type="analyze_requirements",
                source_agent_id="test-sender",
                target_agent_id="business-analyst-0",
                content={"requirements": f"Memory test {i}"},
            )
            messages.append(message)

        # Process in batches to avoid overwhelming the system
        batch_size = 50
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            tasks = [performance_router.route_message(msg) for msg in batch]
            await asyncio.gather(*tasks)

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print("Memory usage:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")

        # Assert reasonable memory usage
        assert (
            memory_increase < 100
        ), f"Memory increase {memory_increase:.2f} MB exceeds 100 MB"

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self, performance_router):
        """Test performance under error conditions."""
        # Create mix of valid and invalid messages
        messages = []

        # Valid messages
        for i in range(20):
            message = ACPMessage(
                message_id=f"valid-{i}",
                message_type="analyze_requirements",
                source_agent_id="test-sender",
                target_agent_id="business-analyst-0",
                content={"requirements": f"Valid test {i}"},
            )
            messages.append(message)

        # Invalid messages (non-existent agent)
        for i in range(10):
            message = ACPMessage(
                message_id=f"invalid-{i}",
                message_type="analyze_requirements",
                source_agent_id="test-sender",
                target_agent_id="non-existent-agent",
                content={"requirements": f"Invalid test {i}"},
            )
            messages.append(message)

        # Process all messages
        start_time = time.time()

        tasks = [performance_router.route_message(msg) for msg in messages]
        responses = await asyncio.gather(*tasks)

        end_time = time.time()
        processing_time = end_time - start_time

        # Count results
        valid_responses = [r for r in responses if r.success]
        invalid_responses = [r for r in responses if not r.success]

        print("Error recovery test:")
        print(f"  Valid messages: {len(valid_responses)}")
        print(f"  Invalid messages: {len(invalid_responses)}")
        print(f"  Processing time: {processing_time:.2f}s")

        # Performance assertions
        assert len(valid_responses) == 20, "Not all valid messages processed"
        assert len(invalid_responses) == 10, "Not all invalid messages handled"
        assert (
            processing_time < 3.0
        ), f"Processing time {processing_time:.2f}s exceeds 3s"

    @pytest.mark.asyncio
    async def test_agent_discovery_performance(self, performance_registry):
        """Test agent discovery performance."""
        # Test discovery performance
        capabilities = ["business_analysis", "testing", "code_generation", "deployment"]

        start_time = time.time()

        discovery_tasks = []
        for capability in capabilities:
            task = performance_registry.discover_agents(capability)
            discovery_tasks.append(task)

        results = await asyncio.gather(*discovery_tasks)

        end_time = time.time()
        discovery_time = end_time - start_time

        # Verify results
        for i, agents in enumerate(results):
            capability = capabilities[i]
            if capability in ["business_analysis", "testing"]:
                assert (
                    len(agents) == 5
                ), f"Expected 5 agents for {capability}, got {len(agents)}"
            else:
                assert (
                    len(agents) == 0
                ), f"Expected 0 agents for {capability}, got {len(agents)}"

        print("Agent discovery performance:")
        print(f"  Capabilities tested: {len(capabilities)}")
        print(f"  Discovery time: {discovery_time:.3f}s")
        print(f"  Average per capability: {discovery_time/len(capabilities):.3f}s")

        # Performance assertions
        assert discovery_time < 1.0, f"Discovery time {discovery_time:.3f}s exceeds 1s"
        assert (
            discovery_time / len(capabilities) < 0.2
        ), "Per-capability time exceeds 200ms"
