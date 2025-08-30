#!/usr/bin/env python3
"""
Demo script showing the message protocol in action.

This script demonstrates how to create and use messages for
communication between the system and the business analyst agent.
"""

import json

from devcycle.core.protocols import (
    AgentAction,
    AgentEvent,
    MessageStatus,
    create_command,
    create_event,
)


def demo_business_analysis_workflow() -> None:
    """Demonstrate a complete business analysis workflow."""
    print("🚀 DevCycle Message Protocol Demo")
    print("=" * 50)

    # Step 1: System sends command to analyze business requirement
    print("\n📤 Step 1: System → Business Analyst Agent")
    print("-" * 40)

    command_data = {
        "business_task": "Create user authentication system",
        "context": "E-commerce platform, must support social login",
        "constraints": "GDPR compliant, OAuth 2.0",
        "priority": "high",
    }

    command_message = create_command(
        AgentAction.ANALYZE_BUSINESS_REQUIREMENT.value, command_data
    )

    print("Command Message:")
    print(json.dumps(command_message.to_dict(), indent=2))

    # Step 2: Agent responds with analysis started event
    print("\n📤 Step 2: Business Analyst Agent → System")
    print("-" * 40)

    started_data = {
        "requirements_doc": "path/to/requirements.md",
        "estimated_duration": "2 hours",
    }

    started_message = create_event(
        AgentEvent.ANALYSIS_STARTED.value, started_data, MessageStatus.IN_PROGRESS
    )

    print("Analysis Started Event:")
    print(json.dumps(started_message.to_dict(), indent=2))

    # Step 3: Agent reports progress
    print("\n📤 Step 3: Progress Update")
    print("-" * 40)

    progress_data = {
        "step": "breaking_down_requirements",
        "progress": 0.3,
        "current_focus": "identifying authentication flows",
    }

    progress_message = create_event(
        AgentEvent.ANALYSIS_PROGRESS.value, progress_data, MessageStatus.IN_PROGRESS
    )

    print("Progress Event:")
    print(json.dumps(progress_message.to_dict(), indent=2))

    # Step 4: Agent completes analysis
    print("\n📤 Step 4: Analysis Complete")
    print("-" * 40)

    complete_data = {
        "tech_tasks": [
            {
                "id": "task_001",
                "title": "Implement OAuth 2.0 provider integration",
                "dependencies": [],
                "estimated_effort": "3 days",
                "priority": "high",
            },
            {
                "id": "task_002",
                "title": "Create user registration flow",
                "dependencies": ["task_001"],
                "estimated_effort": "2 days",
                "priority": "high",
            },
            {
                "id": "task_003",
                "title": "Implement GDPR compliance features",
                "dependencies": ["task_001", "task_002"],
                "estimated_effort": "1 day",
                "priority": "medium",
            },
        ],
        "workflow_diagram": "path/to/workflow.json",
        "total_estimated_effort": "6 days",
    }

    complete_message = create_event(
        AgentEvent.ANALYSIS_COMPLETE.value, complete_data, MessageStatus.COMPLETED
    )

    print("Analysis Complete Event:")
    print(json.dumps(complete_message.to_dict(), indent=2))

    print("\n✅ Demo completed successfully!")
    print("\nThis demonstrates:")
    print("- Command messages (System → Agent)")
    print("- Event messages (Agent → System)")
    print("- Progress tracking")
    print("- Structured data exchange")
    print("- Message serialization")


if __name__ == "__main__":
    demo_business_analysis_workflow()
