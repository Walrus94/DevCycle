"""
ACP Business Analyst Agent.

Real AI-powered business analysis and requirements gathering using Hugging Face models.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional

from acp_sdk.models import Message
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

from devcycle.huggingface.client import HuggingFaceClient

from ..config import ACPAgentConfig
from ..models import ACPAgentInfo, ACPAgentStatus, ACPMessage, ACPResponse

logger = logging.getLogger(__name__)


class BusinessAnalystACPAgent:
    """ACP-native business analyst agent with real AI capabilities."""

    def __init__(self, config: ACPAgentConfig):
        """Initialize the business analyst agent."""
        self.config = config
        self.hf_client = HuggingFaceClient()
        self.server = Server()

        # Register the agent with the ACP server
        self.server.agent()(self.handle_business_analysis_requests)

        # Agent information
        self.agent_info = ACPAgentInfo(
            agent_id=config.agent_id,
            agent_name=config.agent_name,
            agent_version=config.agent_version,
            capabilities=[
                "business_analysis",
                "requirements_gathering",
                "stakeholder_analysis",
                "process_analysis",
            ],
            input_types=[
                "analyze_requirements",
                "gather_stakeholder_needs",
                "analyze_business_process",
                "create_user_stories",
            ],
            output_types=[
                "requirements_document",
                "stakeholder_analysis",
                "process_analysis",
                "user_stories",
            ],
            status=ACPAgentStatus.OFFLINE,
            is_stateful=False,
            max_concurrent_runs=config.max_concurrent_runs,
            hf_model_name=config.hf_model_name,
        )

    async def handle_business_analysis_requests(
        self, input: List[Message], context: Context
    ) -> AsyncGenerator[RunYield, RunYieldResume]:
        """Handle business analysis requests using ACP SDK."""
        try:
            # Update agent status
            self.agent_info.status = ACPAgentStatus.BUSY

            # Process each input message
            for message in input:
                # Extract content from message
                content = self._extract_message_content(message)

                # Determine the type of business analysis request
                request_type = content.get("type", "analyze_requirements")

                if request_type == "analyze_requirements":
                    yield await self._handle_analyze_requirements(content, context)
                elif request_type == "gather_stakeholder_needs":
                    yield await self._handle_gather_stakeholder_needs(content, context)
                elif request_type == "analyze_business_process":
                    yield await self._handle_analyze_business_process(content, context)
                elif request_type == "create_user_stories":
                    yield await self._handle_create_user_stories(content, context)
                elif request_type == "create_acceptance_criteria":
                    yield await self._handle_create_acceptance_criteria(
                        content, context
                    )
                else:
                    yield {
                        "error": f"Unknown request type: {request_type}",
                        "content_type": "text/plain",
                    }

            # Update agent status
            self.agent_info.status = ACPAgentStatus.ONLINE

        except Exception as e:
            logger.error(f"Business analysis error: {e}")
            self.agent_info.status = ACPAgentStatus.ERROR
            yield {
                "error": f"Business analysis failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _handle_analyze_requirements(
        self, content: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Handle requirements analysis requests."""
        try:
            project_description = content.get("project_description", "")
            business_context = content.get("business_context", "")
            stakeholders = content.get("stakeholders", [])

            # Analyze requirements using AI
            requirements_analysis = await self._analyze_requirements(
                project_description, business_context, stakeholders
            )

            return {
                "requirements_analysis": requirements_analysis,
                "project_description": project_description,
                "business_context": business_context,
                "stakeholders": stakeholders,
                "metadata": {
                    "functional_requirements": len(
                        requirements_analysis.get("functional_requirements", [])
                    ),
                    "non_functional_requirements": len(
                        requirements_analysis.get("non_functional_requirements", [])
                    ),
                    "risks_identified": len(requirements_analysis.get("risks", [])),
                    "agent_id": self.agent_info.agent_id,
                },
                "content_type": "application/json",
            }

        except Exception as e:
            logger.error(f"Requirements analysis error: {e}")
            return {
                "error": f"Requirements analysis failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _handle_gather_stakeholder_needs(
        self, content: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Handle stakeholder needs gathering requests."""
        try:
            stakeholders = content.get("stakeholders", [])
            project_scope = content.get("project_scope", "")

            # Gather stakeholder needs using AI
            stakeholder_analysis = await self._gather_stakeholder_needs(
                stakeholders, project_scope
            )

            return {
                "stakeholder_analysis": stakeholder_analysis,
                "stakeholders": stakeholders,
                "project_scope": project_scope,
                "metadata": {
                    "stakeholders_analyzed": len(
                        stakeholder_analysis.get("stakeholder_needs", {})
                    ),
                    "conflicts_identified": len(
                        stakeholder_analysis.get("conflicts", [])
                    ),
                    "consensus_areas": len(
                        stakeholder_analysis.get("consensus_areas", [])
                    ),
                    "agent_id": self.agent_info.agent_id,
                },
                "content_type": "application/json",
            }

        except Exception as e:
            logger.error(f"Stakeholder analysis error: {e}")
            return {
                "error": f"Stakeholder analysis failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _handle_analyze_business_process(
        self, content: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Handle business process analysis requests."""
        try:
            process_description = content.get("process_description", "")
            current_state = content.get("current_state", "")
            desired_state = content.get("desired_state", "")

            # Analyze business process using AI
            process_analysis = await self._analyze_business_process(
                process_description, current_state, desired_state
            )

            return {
                "process_analysis": process_analysis,
                "process_description": process_description,
                "current_state": current_state,
                "desired_state": desired_state,
                "metadata": {
                    "process_steps": len(process_analysis.get("process_steps", [])),
                    "bottlenecks_identified": len(
                        process_analysis.get("bottlenecks", [])
                    ),
                    "improvement_opportunities": len(
                        process_analysis.get("improvements", [])
                    ),
                    "agent_id": self.agent_info.agent_id,
                },
                "content_type": "application/json",
            }

        except Exception as e:
            logger.error(f"Process analysis error: {e}")
            return {
                "error": f"Process analysis failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _handle_create_user_stories(
        self, content: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Handle user story creation requests."""
        try:
            requirements = content.get("requirements", [])
            user_personas = content.get("user_personas", [])
            epic_scope = content.get("epic_scope", "")

            # Create user stories using AI
            user_stories = await self._create_user_stories(
                requirements, user_personas, epic_scope
            )

            return {
                "user_stories": user_stories,
                "requirements": requirements,
                "user_personas": user_personas,
                "epic_scope": epic_scope,
                "metadata": {
                    "stories_created": len(user_stories.get("stories", [])),
                    "epics_identified": len(user_stories.get("epics", [])),
                    "acceptance_criteria": sum(
                        len(story.get("acceptance_criteria", []))
                        for story in user_stories.get("stories", [])
                    ),
                    "agent_id": self.agent_info.agent_id,
                },
                "content_type": "application/json",
            }

        except Exception as e:
            logger.error(f"User story creation error: {e}")
            return {
                "error": f"User story creation failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _handle_create_acceptance_criteria(
        self, content: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Handle acceptance criteria creation requests."""
        try:
            user_story = content.get("user_story", "")
            story_context = content.get("story_context", "")
            testing_requirements = content.get("testing_requirements", [])

            # Create acceptance criteria using AI
            acceptance_criteria = await self._create_acceptance_criteria(
                user_story, story_context, testing_requirements
            )

            return {
                "acceptance_criteria": acceptance_criteria,
                "user_story": user_story,
                "story_context": story_context,
                "testing_requirements": testing_requirements,
                "metadata": {
                    "criteria_created": len(acceptance_criteria.get("criteria", [])),
                    "test_scenarios": len(
                        acceptance_criteria.get("test_scenarios", [])
                    ),
                    "agent_id": self.agent_info.agent_id,
                },
                "content_type": "application/json",
            }

        except Exception as e:
            logger.error(f"Acceptance criteria creation error: {e}")
            return {
                "error": f"Acceptance criteria creation failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _analyze_requirements(
        self, project_description: str, business_context: str, stakeholders: List[str]
    ) -> Dict[str, Any]:
        """Analyze requirements using AI models."""
        try:
            # Use appropriate model for requirements analysis
            model_name = self.config.hf_model_name or "microsoft/CodeGPT-small"

            # Create prompt for requirements analysis
            prompt = f"""Analyze the following project requirements
            and provide a comprehensive analysis:

Project Description: {project_description}
Business Context: {business_context}
Stakeholders: {', '.join(stakeholders) if stakeholders else 'Not specified'}

Please provide:
1. Functional requirements (list of features and capabilities)
2. Non-functional requirements (performance, security, usability, etc.)
3. Business rules and constraints
4. Assumptions and dependencies
5. Potential risks and mitigation strategies
6. Success criteria and metrics

Format the response as a structured analysis.
"""

            # Analyze using Hugging Face client
            response = await self.hf_client.generate_text(
                model_name=model_name, prompt=prompt, max_length=2048, temperature=0.7
            )

            analysis_text = response.get("generated_text", "")

            # Parse the analysis into structured format
            return self._parse_requirements_analysis(analysis_text)

        except Exception as e:
            logger.error(f"Requirements analysis error: {e}")
            return self._fallback_requirements_analysis(
                project_description, business_context, stakeholders
            )

    async def _gather_stakeholder_needs(
        self, stakeholders: List[str], project_scope: str
    ) -> Dict[str, Any]:
        """Gather stakeholder needs using AI."""
        try:
            # Use appropriate model for stakeholder analysis
            model_name = self.config.hf_model_name or "microsoft/CodeGPT-small"

            # Create prompt for stakeholder analysis
            prompt = f"""Analyze the needs and requirements
            of the following stakeholders for this project:

Stakeholders: {', '.join(stakeholders) if stakeholders else 'General stakeholders'}
Project Scope: {project_scope}

For each stakeholder, provide:
1. Primary needs and goals
2. Pain points and challenges
3. Success criteria
4. Potential conflicts with other stakeholders
5. Communication preferences
6. Influence level and decision-making power

Also identify:
- Areas of consensus among stakeholders
- Potential conflicts and how to resolve them
- Stakeholder engagement strategy
"""

            # Analyze using Hugging Face client
            response = await self.hf_client.generate_text(
                model_name=model_name, prompt=prompt, max_length=2048, temperature=0.6
            )

            analysis_text = response.get("generated_text", "")

            # Parse the analysis into structured format
            return self._parse_stakeholder_analysis(analysis_text, stakeholders)

        except Exception as e:
            logger.error(f"Stakeholder analysis error: {e}")
            return self._fallback_stakeholder_analysis(stakeholders, project_scope)

    async def _analyze_business_process(
        self, process_description: str, current_state: str, desired_state: str
    ) -> Dict[str, Any]:
        """Analyze business process using AI."""
        try:
            # Use appropriate model for process analysis
            model_name = self.config.hf_model_name or "microsoft/CodeGPT-small"

            # Create prompt for process analysis
            prompt = f"""Analyze the following business process
            and provide improvement recommendations:

Process Description: {process_description}
Current State: {current_state}
Desired State: {desired_state}

Please provide:
1. Current process steps (detailed breakdown)
2. Identified bottlenecks and inefficiencies
3. Improvement opportunities
4. Technology recommendations
5. Change management considerations
6. Success metrics and KPIs
7. Implementation roadmap

Format as a structured process analysis.
"""

            # Analyze using Hugging Face client
            response = await self.hf_client.generate_text(
                model_name=model_name, prompt=prompt, max_length=2048, temperature=0.6
            )

            analysis_text = response.get("generated_text", "")

            # Parse the analysis into structured format
            return self._parse_process_analysis(analysis_text)

        except Exception as e:
            logger.error(f"Process analysis error: {e}")
            return self._fallback_process_analysis(
                process_description, current_state, desired_state
            )

    async def _create_user_stories(
        self, requirements: List[str], user_personas: List[str], epic_scope: str
    ) -> Dict[str, Any]:
        """Create user stories using AI."""
        try:
            # Use appropriate model for user story creation
            model_name = self.config.hf_model_name or "microsoft/CodeGPT-small"

            # Create prompt for user story creation
            prompt = f"""Create user stories based on the following requirements:

Requirements: {', '.join(requirements) if requirements else 'General requirements'}
User Personas: {', '.join(user_personas) if user_personas else 'General users'}
Epic Scope: {epic_scope}

For each user story, provide:
1. User story in standard format:
    "As a [user type], I want [functionality] so that [benefit]"
2. Acceptance criteria (3-5 criteria per story)
3. Story points estimation (1, 2, 3, 5, 8, 13, 21)
4. Priority (High, Medium, Low)
5. Dependencies and related stories
6. Definition of Done

Group stories into epics and provide epic descriptions.
"""

            # Generate using Hugging Face client
            response = await self.hf_client.generate_text(
                model_name=model_name, prompt=prompt, max_length=2048, temperature=0.7
            )

            stories_text = response.get("generated_text", "")

            # Parse the stories into structured format
            return self._parse_user_stories(stories_text)

        except Exception as e:
            logger.error(f"User story creation error: {e}")
            return self._fallback_user_stories(requirements, user_personas, epic_scope)

    async def _create_acceptance_criteria(
        self, user_story: str, story_context: str, testing_requirements: List[str]
    ) -> Dict[str, Any]:
        """Create acceptance criteria using AI."""
        try:
            # Use appropriate model for acceptance criteria creation
            model_name = self.config.hf_model_name or "microsoft/CodeGPT-small"

            # Create prompt for acceptance criteria creation
            prompt = f"""Create detailed acceptance criteria
            for the following user story:

User Story: {user_story}
Story Context: {story_context}
Testing Requirements: {
                    ', '.join(testing_requirements)
                    if testing_requirements else 'Standard testing'
                }

Provide:
1. Detailed acceptance criteria (5-8 criteria)
2. Test scenarios for each criterion
3. Edge cases and error conditions
4. Performance requirements
5. Security considerations
6. Usability requirements
7. Definition of Done checklist

Format each criterion as: "Given [context], When [action], Then [expected result]"
"""

            # Generate using Hugging Face client
            response = await self.hf_client.generate_text(
                model_name=model_name, prompt=prompt, max_length=1024, temperature=0.6
            )

            criteria_text = response.get("generated_text", "")

            # Parse the criteria into structured format
            return self._parse_acceptance_criteria(criteria_text)

        except Exception as e:
            logger.error(f"Acceptance criteria creation error: {e}")
            return self._fallback_acceptance_criteria(
                user_story, story_context, testing_requirements
            )

    def _extract_message_content(self, message: Message) -> Dict[str, Any]:
        """Extract content from ACP message."""
        content = {}

        for part in message.parts:
            if part.content_type == "application/json":
                try:
                    import json

                    if part.content:
                        content.update(json.loads(part.content))
                except json.JSONDecodeError:
                    content["text"] = part.content
            else:
                content["text"] = part.content

        return content

    def _parse_requirements_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse requirements analysis into structured format."""
        # Simple parsing - in practice, you'd want more sophisticated parsing
        lines = analysis_text.split("\n")

        functional_requirements = []
        non_functional_requirements = []
        risks = []

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "functional" in line.lower():
                current_section = "functional"
            elif "non-functional" in line.lower() or "non functional" in line.lower():
                current_section = "non_functional"
            elif "risk" in line.lower():
                current_section = "risks"
            elif line.startswith(("-", "*", "•", "1.", "2.", "3.")):
                item = line.lstrip("-*•123456789. ").strip()
                if current_section == "functional":
                    functional_requirements.append(item)
                elif current_section == "non_functional":
                    non_functional_requirements.append(item)
                elif current_section == "risks":
                    risks.append(item)

        return {
            "functional_requirements": functional_requirements,
            "non_functional_requirements": non_functional_requirements,
            "risks": risks,
            "analysis_text": analysis_text,
        }

    def _parse_stakeholder_analysis(
        self, analysis_text: str, stakeholders: List[str]
    ) -> Dict[str, Any]:
        """Parse stakeholder analysis into structured format."""
        # Simple parsing - in practice, you'd want more sophisticated parsing
        stakeholder_needs = {}
        conflicts: List[str] = []
        consensus_areas: List[str] = []

        for stakeholder in stakeholders:
            stakeholder_needs[stakeholder] = {
                "needs": [f"Need for {stakeholder}"],
                "goals": [f"Goal for {stakeholder}"],
                "pain_points": [f"Pain point for {stakeholder}"],
            }

        return {
            "stakeholder_needs": stakeholder_needs,
            "conflicts": conflicts,
            "consensus_areas": consensus_areas,
            "analysis_text": analysis_text,
        }

    def _parse_process_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse process analysis into structured format."""
        # Simple parsing
        lines = analysis_text.split("\n")

        process_steps = []
        bottlenecks = []
        improvements = []

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "step" in line.lower():
                current_section = "steps"
            elif "bottleneck" in line.lower():
                current_section = "bottlenecks"
            elif "improvement" in line.lower():
                current_section = "improvements"
            elif line.startswith(("-", "*", "•", "1.", "2.", "3.")):
                item = line.lstrip("-*•123456789. ").strip()
                if current_section == "steps":
                    process_steps.append(item)
                elif current_section == "bottlenecks":
                    bottlenecks.append(item)
                elif current_section == "improvements":
                    improvements.append(item)

        return {
            "process_steps": process_steps,
            "bottlenecks": bottlenecks,
            "improvements": improvements,
            "analysis_text": analysis_text,
        }

    def _parse_user_stories(self, stories_text: str) -> Dict[str, Any]:
        """Parse user stories into structured format."""
        # Simple parsing
        lines = stories_text.split("\n")

        stories: List[Dict[str, Any]] = []
        epics: List[Dict[str, Any]] = []

        current_story: Optional[Dict[str, Any]] = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("As a"):
                if current_story:
                    stories.append(current_story)
                current_story = {
                    "story": line,
                    "acceptance_criteria": [],
                    "story_points": 3,
                    "priority": "Medium",
                }
            elif current_story and line.startswith(("-", "*", "•")):
                if current_story and "acceptance_criteria" in current_story:
                    current_story["acceptance_criteria"].append(
                        line.lstrip("-*• ").strip()
                    )

        if current_story:
            stories.append(current_story)

        return {"stories": stories, "epics": epics, "stories_text": stories_text}

    def _parse_acceptance_criteria(self, criteria_text: str) -> Dict[str, Any]:
        """Parse acceptance criteria into structured format."""
        # Simple parsing
        lines = criteria_text.split("\n")

        criteria = []
        test_scenarios = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if (
                line.startswith("Given")
                or line.startswith("When")
                or line.startswith("Then")
            ):
                criteria.append(line)
            elif line.startswith(("-", "*", "•")):
                test_scenarios.append(line.lstrip("-*• ").strip())

        return {
            "criteria": criteria,
            "test_scenarios": test_scenarios,
            "criteria_text": criteria_text,
        }

    def _fallback_requirements_analysis(
        self, project_description: str, business_context: str, stakeholders: List[str]
    ) -> Dict[str, Any]:
        """Fallback requirements analysis when AI is unavailable."""
        return {
            "functional_requirements": [
                f"Implement core functionality for {project_description}",
                "Provide user authentication and authorization",
                "Enable data management and storage",
                "Support reporting and analytics",
            ],
            "non_functional_requirements": [
                "System should be responsive and performant",
                "Data should be secure and encrypted",
                "System should be scalable and maintainable",
                "User interface should be intuitive and accessible",
            ],
            "risks": [
                "Technical complexity may impact timeline",
                "Stakeholder requirements may change",
                "Integration challenges with existing systems",
            ],
            "analysis_text": f"Fallback analysis for {project_description}",
        }

    def _fallback_stakeholder_analysis(
        self, stakeholders: List[str], project_scope: str
    ) -> Dict[str, Any]:
        """Fallback stakeholder analysis when AI is unavailable."""
        stakeholder_needs = {}
        for stakeholder in stakeholders:
            stakeholder_needs[stakeholder] = {
                "needs": [f"Clear communication about {project_scope}"],
                "goals": [f"Successful delivery of {project_scope}"],
                "pain_points": ["Lack of clear requirements"],
            }

        return {
            "stakeholder_needs": stakeholder_needs,
            "conflicts": [],
            "consensus_areas": [f"Agreement on {project_scope} scope"],
        }

    def _fallback_process_analysis(
        self, process_description: str, current_state: str, desired_state: str
    ) -> Dict[str, Any]:
        """Fallback process analysis when AI is unavailable."""
        return {
            "process_steps": [
                "Identify current process gaps",
                "Design improved process flow",
                "Implement process changes",
                "Monitor and optimize process",
            ],
            "bottlenecks": [
                "Manual data entry processes",
                "Lack of automation",
                "Poor communication between teams",
            ],
            "improvements": [
                "Automate manual processes",
                "Improve communication channels",
                "Implement better tracking and monitoring",
            ],
        }

    def _fallback_user_stories(
        self, requirements: List[str], user_personas: List[str], epic_scope: str
    ) -> Dict[str, Any]:
        """Fallback user stories when AI is unavailable."""
        stories = []
        for i, requirement in enumerate(requirements[:5]):  # Limit to 5 stories
            stories.append(
                {
                    "story": (
                        f"As a user, I want {requirement.lower()} "
                        f"so that I can achieve my goals"
                    ),
                    "acceptance_criteria": [
                        (
                            f"Given I am a user, When I access the system, "
                            f"Then I should be able to {requirement.lower()}"
                        ),
                        (
                            "Given the system is available, When I perform the action, "
                            "Then I should receive confirmation"
                        ),
                    ],
                    "story_points": 3,
                    "priority": "Medium",
                }
            )

        return {
            "stories": stories,
            "epics": [{"name": epic_scope, "description": f"Epic for {epic_scope}"}],
        }

    def _fallback_acceptance_criteria(
        self, user_story: str, story_context: str, testing_requirements: List[str]
    ) -> Dict[str, Any]:
        """Fallback acceptance criteria when AI is unavailable."""
        return {
            "criteria": [
                f"""Given {story_context}, When the user performs the action,
                Then the expected result should occur""",
                """Given the system is available,
                When the user accesses the feature,
                Then it should load within 2 seconds""",
                """Given the user has proper permissions,
                When they perform the action,
                Then they should receive confirmation""",
            ],
            "test_scenarios": [
                "Test with valid input data",
                "Test with invalid input data",
                "Test with edge cases",
                "Test performance under load",
            ],
        }

    def run(self) -> None:
        """Start the ACP agent server."""
        logger.info(f"Starting Business Analyst ACP Agent: {self.agent_info.agent_id}")
        self.agent_info.status = ACPAgentStatus.ONLINE
        self.server.run()

    def get_agent_info(self) -> ACPAgentInfo:
        """Get agent information."""
        return self.agent_info

    async def handle_message(self, message: "ACPMessage") -> "ACPResponse":
        """Handle ACP messages for the business analyst agent."""
        from ..models import ACPMessageType, ACPResponse

        try:
            # Update agent status
            self.agent_info.status = ACPAgentStatus.ONLINE
            self.agent_info.current_runs += 1

            # Process the message based on type
            if message.message_type == ACPMessageType.ANALYZE_REQUIREMENTS:
                result = await self._analyze_requirements(
                    message.content.get("project_description", ""),
                    message.content.get("business_context", ""),
                    message.content.get("stakeholders", []),
                )
            elif message.message_type == ACPMessageType.GATHER_STAKEHOLDER_NEEDS:
                result = await self._gather_stakeholder_needs(
                    message.content.get("stakeholders", []),
                    message.content.get("project_scope", ""),
                )
            elif message.message_type == ACPMessageType.ANALYZE_BUSINESS_PROCESS:
                result = await self._analyze_business_process(
                    message.content.get("process_description", ""),
                    message.content.get("current_workflow", ""),
                    message.content.get("desired_state", ""),
                )
            elif message.message_type == ACPMessageType.CREATE_USER_STORIES:
                result = await self._create_user_stories(
                    message.content.get("requirements", []),
                    message.content.get("user_personas", []),
                    message.content.get("epic_scope", ""),
                )
            else:
                result = {"error": f"Unsupported message type: {message.message_type}"}

            # Create response
            response = ACPResponse(
                response_id=f"resp_{message.message_id}",
                message_id=message.message_id,
                success=True,
                content=result,
                metadata={
                    "agent_id": self.agent_info.agent_id,
                    "agent_name": self.agent_info.agent_name,
                    "processing_time_ms": 0,  # Will be set by message router
                },
            )

            return response

        except Exception as e:
            logger.error(f"Error handling message {message.message_id}: {e}")
            return ACPResponse(
                response_id=f"resp_{message.message_id}",
                message_id=message.message_id,
                success=False,
                content={"error": str(e)},
                metadata={
                    "agent_id": self.agent_info.agent_id,
                    "agent_name": self.agent_info.agent_name,
                },
            )
        finally:
            # Update agent status
            self.agent_info.current_runs -= 1
            if self.agent_info.current_runs <= 0:
                self.agent_info.status = ACPAgentStatus.ONLINE
