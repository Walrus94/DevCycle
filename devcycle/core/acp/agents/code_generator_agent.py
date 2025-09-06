"""
ACP Code Generator Agent.

Real AI-powered code generation using Hugging Face models.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict, List

from acp_sdk.models import Message
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

from devcycle.huggingface.client import HuggingFaceClient

from ..config import ACPAgentConfig
from ..models import ACPAgentInfo, ACPAgentStatus

logger = logging.getLogger(__name__)


class CodeGeneratorACPAgent:
    """ACP-native code generation agent with real AI capabilities."""

    def __init__(self, config: ACPAgentConfig):
        """Initialize the code generator agent."""
        self.config = config
        self.hf_client = HuggingFaceClient()
        self.server = Server()

        # Register the agent with the ACP server
        self.server.agent()(self.handle_code_generation)

        # Agent information
        self.agent_info = ACPAgentInfo(
            agent_id=config.agent_id,
            agent_name=config.agent_name,
            agent_version=config.agent_version,
            capabilities=["code_generation", "text_processing", "code_analysis"],
            input_types=["generate_code", "analyze_code", "refactor_code"],
            output_types=["generated_code", "code_analysis", "refactored_code"],
            status=ACPAgentStatus.OFFLINE,
            is_stateful=False,
            max_concurrent_runs=config.max_concurrent_runs,
            hf_model_name=config.hf_model_name,
        )

    async def handle_code_generation(
        self, input: List[Message], context: Context
    ) -> AsyncGenerator[RunYield, RunYieldResume]:
        """Handle code generation requests using ACP SDK."""
        try:
            # Update agent status
            self.agent_info.status = ACPAgentStatus.BUSY

            # Process each input message
            for message in input:
                # Extract content from message
                content = self._extract_message_content(message)

                # Determine the type of code generation request
                request_type = content.get("type", "generate_code")

                if request_type == "generate_code":
                    yield await self._handle_generate_code(content, context)
                elif request_type == "analyze_code":
                    yield await self._handle_analyze_code(content, context)
                elif request_type == "refactor_code":
                    yield await self._handle_refactor_code(content, context)
                else:
                    yield {
                        "error": f"Unknown request type: {request_type}",
                        "content_type": "text/plain",
                    }

            # Update agent status
            self.agent_info.status = ACPAgentStatus.ONLINE

        except Exception as e:
            logger.error(f"Code generation error: {e}")
            self.agent_info.status = ACPAgentStatus.ERROR
            yield {
                "error": f"Code generation failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _handle_generate_code(
        self, content: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Handle code generation requests."""
        try:
            requirements = content.get("requirements", "")
            language = content.get("language", "python")
            framework = content.get("framework", "")

            # Generate code using Hugging Face models
            generated_code = await self._generate_code(
                requirements, language, framework
            )

            # Analyze the generated code
            complexity = self._analyze_complexity(generated_code)
            lines_of_code = len(generated_code.split("\n"))

            return {
                "generated_code": generated_code,
                "language": language,
                "framework": framework,
                "metadata": {
                    "lines_of_code": lines_of_code,
                    "complexity": complexity,
                    "model_used": self.config.hf_model_name
                    or "microsoft/CodeGPT-small",
                    "agent_id": self.agent_info.agent_id,
                },
                "content_type": "application/json",
            }

        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return {
                "error": f"Code generation failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _handle_analyze_code(
        self, content: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Handle code analysis requests."""
        try:
            code = content.get("code", "")
            analysis_type = content.get("analysis_type", "general")

            # Analyze the code
            analysis_result = await self._analyze_code(code, analysis_type)

            return {
                "analysis": analysis_result,
                "analysis_type": analysis_type,
                "metadata": {
                    "lines_of_code": len(code.split("\n")),
                    "agent_id": self.agent_info.agent_id,
                },
                "content_type": "application/json",
            }

        except Exception as e:
            logger.error(f"Code analysis error: {e}")
            return {
                "error": f"Code analysis failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _handle_refactor_code(
        self, content: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Handle code refactoring requests."""
        try:
            code = content.get("code", "")
            refactor_type = content.get("refactor_type", "general")
            language = content.get("language", "python")

            # Refactor the code
            refactored_code = await self._refactor_code(code, refactor_type, language)

            return {
                "original_code": code,
                "refactored_code": refactored_code,
                "refactor_type": refactor_type,
                "language": language,
                "metadata": {
                    "original_lines": len(code.split("\n")),
                    "refactored_lines": len(refactored_code.split("\n")),
                    "agent_id": self.agent_info.agent_id,
                },
                "content_type": "application/json",
            }

        except Exception as e:
            logger.error(f"Code refactoring error: {e}")
            return {
                "error": f"Code refactoring failed: {str(e)}",
                "content_type": "text/plain",
            }

    async def _generate_code(
        self, requirements: str, language: str, framework: str = ""
    ) -> str:
        """Generate code using Hugging Face models."""
        try:
            # Use appropriate model for code generation
            model_name = (
                self.config.hf_model_name or f"microsoft/CodeGPT-small-{language}"
            )

            # Create prompt for code generation
            prompt = f"Generate {language} code for: {requirements}"
            if framework:
                prompt += f" using {framework} framework"

            # Generate code using Hugging Face client
            response = await self.hf_client.generate_text(
                model_name=model_name, prompt=prompt, max_length=1024, temperature=0.7
            )

            return str(response.get("generated_text", ""))

        except Exception as e:
            logger.error(f"Code generation error: {e}")
            # Fallback to simple code generation
            return self._fallback_code_generation(requirements, language, framework)

    async def _analyze_code(self, code: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze code using AI models."""
        try:
            # Use appropriate model for code analysis
            model_name = self.config.hf_model_name or "microsoft/CodeGPT-small"

            # Create prompt for code analysis
            prompt = f"Analyze this code for {analysis_type}:\n\n{code}"

            # Analyze code using Hugging Face client
            response = await self.hf_client.generate_text(
                model_name=model_name, prompt=prompt, max_length=512, temperature=0.3
            )

            analysis_text = response.get("generated_text", "")

            # Extract structured analysis
            return {
                "analysis_text": analysis_text,
                "complexity": self._analyze_complexity(code),
                "lines_of_code": len(code.split("\n")),
                "analysis_type": analysis_type,
            }

        except Exception as e:
            logger.error(f"Code analysis error: {e}")
            return {
                "analysis_text": f"Analysis failed: {str(e)}",
                "complexity": "unknown",
                "lines_of_code": len(code.split("\n")),
                "analysis_type": analysis_type,
            }

    async def _refactor_code(self, code: str, refactor_type: str, language: str) -> str:
        """Refactor code using AI models."""
        try:
            # Use appropriate model for code refactoring
            model_name = (
                self.config.hf_model_name or f"microsoft/CodeGPT-small-{language}"
            )

            # Create prompt for code refactoring
            prompt = f"Refactor this {language} code for {refactor_type}:\n\n{code}"

            # Refactor code using Hugging Face client
            response = await self.hf_client.generate_text(
                model_name=model_name, prompt=prompt, max_length=1024, temperature=0.5
            )

            return str(response.get("generated_text", ""))

        except Exception as e:
            logger.error(f"Code refactoring error: {e}")
            return code  # Return original code if refactoring fails

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

    def _analyze_complexity(self, code: str) -> str:
        """Analyze code complexity."""
        lines = len(code.split("\n"))

        if lines < 10:
            return "simple"
        elif lines < 50:
            return "moderate"
        else:
            return "complex"

    def _fallback_code_generation(
        self, requirements: str, language: str, framework: str = ""
    ) -> str:
        """Fallback code generation when AI models are unavailable."""
        if language.lower() == "python":
            if framework.lower() == "fastapi":
                return f"""from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {{"message": "Hello World"}}

# {requirements}
"""
            else:
                return f'''def main():
    """{requirements}"""
    pass

if __name__ == "__main__":
    main()
'''
        else:
            return f"""// {requirements}
// Generated code for {language}
"""

    def run(self) -> None:
        """Start the ACP agent server."""
        logger.info(f"Starting Code Generator ACP Agent: {self.agent_info.agent_id}")
        self.agent_info.status = ACPAgentStatus.ONLINE
        self.server.run()

    def get_agent_info(self) -> ACPAgentInfo:
        """Get agent information."""
        return self.agent_info
