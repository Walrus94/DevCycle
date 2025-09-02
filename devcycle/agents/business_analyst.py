"""
Business Analyst Agent for DevCycle system.

This agent specializes in analyzing business requirements and converting them
into structured development specifications.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import AgentResult, BaseAgent


@dataclass
class Requirement:
    """Represents a business requirement."""

    id: str
    title: str
    description: str
    priority: str = "medium"
    category: str = "feature"
    acceptance_criteria: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Initialize the requirement after creation."""
        if self.acceptance_criteria is None:
            self.acceptance_criteria = []
        if self.dependencies is None:
            self.dependencies = []


class BusinessAnalystAgent(BaseAgent):
    """
    Business Analyst Agent for requirements analysis and specification.

    This agent processes business requirements and converts them into
    structured development specifications.
    """

    def __init__(
        self, name: str = "business_analyst", config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the Business Analyst agent."""
        super().__init__(name, config)
        self.requirements_database: List[Requirement] = []
        self.analysis_templates = self._load_analysis_templates()

    def _load_analysis_templates(self) -> Dict[str, Any]:
        """Load analysis templates for different requirement types."""
        return {
            "feature": {
                "sections": [
                    "overview",
                    "user_stories",
                    "acceptance_criteria",
                    "technical_considerations",
                ],
                "priority_levels": ["low", "medium", "high", "critical"],
            },
            "bugfix": {
                "sections": [
                    "issue_description",
                    "reproduction_steps",
                    "expected_behavior",
                    "actual_behavior",
                ],
                "priority_levels": ["low", "medium", "high", "critical"],
            },
        }

    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data for business analysis.

        Args:
            input_data: Input data to validate

        Returns:
            True if input is valid, False otherwise
        """
        if not input_data:
            return False

        # Accept string requirements or requirement dictionaries
        if isinstance(input_data, str):
            return len(input_data.strip()) > 0
        elif isinstance(input_data, dict):
            required_fields = ["title", "description"]
            return all(field in input_data for field in required_fields)

        return False

    async def process(self, input_data: Any, **kwargs: Any) -> AgentResult:
        """
        Process business requirements and generate analysis.

        Args:
            input_data: Business requirement to analyze
            **kwargs: Additional parameters

        Returns:
            AgentResult containing the analysis
        """
        try:
            # Parse input data
            requirement = self._parse_requirement(input_data)

            # Analyze requirement
            analysis = await self._analyze_requirement(requirement)

            # Store in database
            self.requirements_database.append(requirement)

            return AgentResult(
                success=True,
                data=analysis,
                metadata={
                    "requirement_id": requirement.id,
                    "analysis_type": "business_requirement",
                    "stored_in_database": True,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Failed to analyze requirement: {str(e)}",
                metadata={"analysis_type": "business_requirement"},
            )

    def _parse_requirement(self, input_data: Any) -> Requirement:
        """Parse input data into a Requirement object."""
        if isinstance(input_data, str):
            # Simple string input - create basic requirement
            return Requirement(
                id=f"req_{len(self.requirements_database) + 1:03d}",
                title="Business Requirement",
                description=input_data,
            )
        elif isinstance(input_data, dict):
            # Dictionary input - extract fields
            return Requirement(
                id=input_data.get(
                    "id", f"req_{len(self.requirements_database) + 1:03d}"
                ),
                title=input_data.get("title", "Untitled Requirement"),
                description=input_data.get("description", ""),
                priority=input_data.get("priority", "medium"),
                category=input_data.get("category", "feature"),
                acceptance_criteria=input_data.get("acceptance_criteria", []),
                dependencies=input_data.get("dependencies", []),
            )
        else:
            raise ValueError(f"Unsupported input data type: {type(input_data)}")

    async def _analyze_requirement(self, requirement: Requirement) -> Dict[str, Any]:
        """Analyze a business requirement and generate specification."""
        template = self.analysis_templates.get(
            requirement.category, self.analysis_templates["feature"]
        )

        analysis: Dict[str, Any] = {
            "requirement_id": requirement.id,
            "title": requirement.title,
            "description": requirement.description,
            "priority": requirement.priority,
            "category": requirement.category,
            "analysis_sections": {},
            "recommendations": [],
        }

        # Generate analysis for each template section
        for section in template["sections"]:
            analysis["analysis_sections"][section] = self._generate_section_analysis(
                section, requirement, template
            )

        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(requirement)

        return analysis

    def _generate_section_analysis(
        self, section: str, requirement: Requirement, template: Dict[str, Any]
    ) -> str:
        """Generate analysis for a specific section."""
        if section == "overview":
            return (
                f"Requirement '{requirement.title}' is a {requirement.priority} "
                f"priority {requirement.category}."
            )
        elif section == "user_stories":
            return (
                f"As a user, I want {requirement.description.lower()} "
                f"so that I can achieve my business goals."
            )
        elif section == "acceptance_criteria":
            if requirement.acceptance_criteria:
                return "Acceptance criteria: " + "; ".join(
                    requirement.acceptance_criteria
                )
            return (
                "Acceptance criteria need to be defined based on business requirements."
            )
        elif section == "technical_considerations":
            return (
                "Technical implementation details should be discussed "
                "with the development team."
            )
        else:
            return f"Analysis for {section} section."

    def _generate_recommendations(self, requirement: Requirement) -> List[str]:
        """Generate recommendations for the requirement."""
        recommendations = []

        if requirement.priority == "critical":
            recommendations.append(
                "This is a critical requirement - prioritize implementation"
            )

        if not requirement.acceptance_criteria:
            recommendations.append(
                "Define clear acceptance criteria before development"
            )

        if requirement.dependencies:
            recommendations.append(
                f"Consider dependencies: {', '.join(requirement.dependencies)}"
            )

        if len(requirement.description) < 50:
            recommendations.append(
                "Provide more detailed description for better understanding"
            )

        return recommendations

    def get_requirements_summary(self) -> Dict[str, Any]:
        """Get a summary of all analyzed requirements."""
        return {
            "total_requirements": len(self.requirements_database),
            "by_priority": self._count_by_field("priority"),
            "by_category": self._count_by_field("category"),
            "recent_requirements": [
                {
                    "id": req.id,
                    "title": req.title,
                    "priority": req.priority,
                    "category": req.category,
                }
                for req in self.requirements_database[-5:]  # Last 5 requirements
            ],
        }

    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count requirements by a specific field."""
        counts: Dict[str, int] = {}
        for req in self.requirements_database:
            value = getattr(req, field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
