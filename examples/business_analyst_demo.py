"""
Business Analyst Agent Demo.

This script demonstrates the capabilities of the BusinessAnalystAgent
by processing various types of business requirements.
"""

# mypy: disable-error-code=no-untyped-def

import asyncio

from devcycle.agents.business_analyst import BusinessAnalystAgent


async def demo_business_analyst():
    """Demonstrate the Business Analyst agent capabilities."""
    print("🚀 Business Analyst Agent Demo")
    print("=" * 50)

    # Create agent
    agent = BusinessAnalystAgent("demo_analyst")
    print(f"✅ Created agent: {agent.name}")

    # Demo 1: Simple string requirement
    print("\n📝 Demo 1: Simple String Requirement")
    print("-" * 40)

    simple_req = "Users should be able to reset their password"
    result = await agent.process(simple_req)

    if result.success:
        print(f"✅ Processed requirement: {result.data['title']}")
        print(f"📊 Priority: {result.data['priority']}")
        print(f"🏷️  Category: {result.data['category']}")
        print(f"💡 Recommendations: {len(result.data['recommendations'])}")
    else:
        print(f"❌ Failed: {result.error}")

    # Demo 2: Structured requirement
    print("\n📋 Demo 2: Structured Requirement")
    print("-" * 40)

    structured_req = {
        "title": "User Authentication System",
        "description": "Implement secure user login and registration functionality",
        "priority": "high",
        "category": "feature",
        "acceptance_criteria": [
            "Users can register with email and password",
            "Users can login with valid credentials",
            "Passwords are securely hashed",
            "Session management is implemented",
        ],
        "dependencies": ["database_system", "security_framework"],
    }

    result = await agent.process(structured_req)

    if result.success:
        print(f"✅ Processed requirement: {result.data['title']}")
        print(f"📊 Priority: {result.data['priority']}")
        print(f"🏷️  Category: {result.data['category']}")
        print(
            f"📋 Acceptance Criteria: {len(structured_req['acceptance_criteria'])} items"
        )
        print(f"🔗 Dependencies: {len(structured_req['dependencies'])} items")

    # Demo 3: Bug report
    print("\n🐛 Demo 3: Bug Report")
    print("-" * 40)

    bug_report = {
        "title": "Login Button Not Working",
        "description": "Users cannot click the login button on mobile devices",
        "priority": "critical",
        "category": "bugfix",
    }

    result = await agent.process(bug_report)

    if result.success:
        print(f"✅ Processed bug report: {result.data['title']}")
        print(f"📊 Priority: {result.data['priority']}")
        print(f"🏷️  Category: {result.data['category']}")

    # Demo 4: Requirements Summary
    print("\n📊 Demo 4: Requirements Summary")
    print("-" * 40)

    summary = agent.get_requirements_summary()
    print(f"📈 Total Requirements: {summary['total_requirements']}")
    print(f"🎯 By Priority: {summary['by_priority']}")
    print(f"🏷️  By Category: {summary['by_category']}")

    print("\n📋 Recent Requirements:")
    for req in summary["recent_requirements"]:
        print(f"  • {req['id']}: {req['title']} ({req['priority']} priority)")

    # Demo 5: Agent Status
    print("\n🤖 Demo 5: Agent Status")
    print("-" * 40)

    status = agent.get_status()
    print(f"Agent: {status['name']}")
    print(f"Status: {status['status']}")
    print(f"Executions: {status['execution_history_count']}")
    print(f"Configuration: {len(status['config'])} items")

    print("\n🎉 Demo completed successfully!")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_business_analyst())
