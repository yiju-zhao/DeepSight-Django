"""
Coordinator Orchestration Logic

This module implements the main coordination logic for multi-agent workflows,
including multi-turn clarification, plan generation, and task execution.
"""

import asyncio
import logging
import uuid
import time
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel

from django.conf import settings

from .schema import (
    TaskType,
    TaskStatus,
    TaskOptions,
    TaskPlan,
    TaskStep,
    TaskResult,
    ExecutionLog,
    ClarificationResult,
    ClarificationQuestion,
)
from .registry import AgentRegistry


logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


def get_coordinator_model():
    """Get the model used for coordination decisions."""
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    model_name = getattr(settings, "COORDINATOR_MODEL", "gpt-4.1")

    return init_chat_model(
        model=f"openai:{model_name}",
        api_key=api_key,
    )


# ============================================================================
# PROMPTS
# ============================================================================

CLARIFICATION_PROMPT = """You are a research coordinator helping users refine their requests.

Current conversation:
{conversation}

Your task is to determine if you have enough information to proceed with research.

Consider:
1. Is the topic clear and specific enough?
2. Are there ambiguous terms that need clarification?
3. Does the user have specific requirements (format, length, style)?
4. Is the scope well-defined?

Respond with a JSON object:
{{
    "need_clarification": boolean,
    "confident": boolean,
    "questions": [
        {{"question": "...", "purpose": "...", "required": true/false}}
    ],
    "extracted_requirements": {{
        "topic": "...",
        "style": "...",
        "scope": "...",
        ...
    }},
    "verification_message": "Message confirming understanding if confident"
}}

If you are confident (have all needed info), set "confident": true and provide a verification message.
If you need more info, set "need_clarification": true with your questions.
After 3 clarification rounds, you MUST set confident: true and proceed with available information.
"""

PLANNING_PROMPT = """Based on the user's goal, create an execution plan.

User Goal: {user_goal}

Requirements: {requirements}

Available Agents:
{agent_capabilities}

Determine the task type:
- RESEARCH_ONLY: Just gather information, no report
- WRITE_ONLY: Generate report from provided information
- RESEARCH_AND_WRITE: Research first, then generate report

Create a plan with ordered steps. Each step should specify which agent to use.

Respond with a JSON object:
{{
    "task_type": "research_only" | "write_only" | "research_and_write",
    "steps": [
        {{
            "step_id": "step_1",
            "agent_name": "research" | "writer",
            "action": "description of what this step does",
            "inputs": {{}},
            "depends_on": []
        }}
    ],
    "estimated_duration": number (seconds)
}}
"""


# ============================================================================
# COORDINATOR CLASS
# ============================================================================


class Coordinator:
    """
    Orchestrates multi-agent task execution.

    The Coordinator handles:
    1. Multi-turn clarification to understand user needs
    2. Plan generation based on requirements
    3. Execution of research and writing agents
    4. Result aggregation and error handling
    """

    def __init__(self):
        self.model = get_coordinator_model()
        self.conversation_history: list[dict[str, str]] = []
        self.clarification_rounds = 0
        self.max_clarification_rounds = 3

    async def clarify_requirements(
        self,
        user_goal: str,
        user_response: str | None = None,
    ) -> ClarificationResult:
        """
        Multi-turn clarification until confident.

        Continues dialogue until:
        - All required information is collected
        - Confidence score exceeds threshold
        - User explicitly confirms to proceed
        - Max clarification rounds reached

        Args:
            user_goal: Initial user goal or latest response
            user_response: User's response to clarification questions

        Returns:
            ClarificationResult with status and any questions
        """
        # Add to conversation history
        if not self.conversation_history:
            self.conversation_history.append(
                {"role": "user", "content": f"I need help with: {user_goal}"}
            )
        elif user_response:
            self.conversation_history.append({"role": "user", "content": user_response})

        self.clarification_rounds += 1

        # Force confidence after max rounds
        force_confident = self.clarification_rounds >= self.max_clarification_rounds

        # Format conversation for prompt
        conversation_text = "\n".join(
            [
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in self.conversation_history
            ]
        )

        prompt = CLARIFICATION_PROMPT.format(conversation=conversation_text)

        if force_confident:
            prompt += "\n\nIMPORTANT: You have reached the maximum clarification rounds. You MUST set confident: true and proceed with the available information."

        try:
            response = await self.model.ainvoke([HumanMessage(content=prompt)])

            # Parse JSON response
            import json

            content = response.content

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result_dict = json.loads(content.strip())

            # Build questions list
            questions = [
                ClarificationQuestion(**q) for q in result_dict.get("questions", [])
            ]

            result = ClarificationResult(
                need_clarification=result_dict.get("need_clarification", False),
                questions=questions,
                confident=result_dict.get("confident", False) or force_confident,
                extracted_requirements=result_dict.get("extracted_requirements", {}),
                verification_message=result_dict.get("verification_message", ""),
            )

            # Add AI response to history
            if result.confident:
                self.conversation_history.append(
                    {"role": "assistant", "content": result.verification_message}
                )
            elif result.questions:
                questions_text = "\n".join(
                    [f"- {q.question}" for q in result.questions]
                )
                self.conversation_history.append(
                    {
                        "role": "assistant",
                        "content": f"I have some clarifying questions:\n{questions_text}",
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Clarification failed: {e}")
            # Return confident on error to allow proceeding
            return ClarificationResult(
                need_clarification=False,
                confident=True,
                extracted_requirements={"topic": user_goal},
                verification_message=f"I'll proceed with researching: {user_goal}",
            )

    async def create_plan(
        self,
        user_goal: str,
        requirements: dict[str, Any],
        options: TaskOptions | None = None,
    ) -> TaskPlan:
        """
        Generate execution plan based on goal and requirements.

        Args:
            user_goal: User's research goal
            requirements: Extracted requirements from clarification
            options: Task execution options

        Returns:
            TaskPlan with ordered execution steps
        """
        options = options or TaskOptions()

        # Format agent capabilities
        capabilities_text = "\n".join(
            [
                f"- {cap.name}: {cap.description}"
                for cap in AgentRegistry.list_capabilities()
            ]
        )

        prompt = PLANNING_PROMPT.format(
            user_goal=user_goal,
            requirements=str(requirements),
            agent_capabilities=capabilities_text,
        )

        try:
            response = await self.model.ainvoke([HumanMessage(content=prompt)])

            # Parse JSON response
            import json

            content = response.content

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            plan_dict = json.loads(content.strip())

            # Override task type if specified in options
            task_type_str = plan_dict.get("task_type", "research_and_write")
            if options.task_type:
                task_type = options.task_type
            else:
                task_type = TaskType(task_type_str)

            # Build steps
            steps = [TaskStep(**step) for step in plan_dict.get("steps", [])]

            # If no steps, create default based on task type
            if not steps:
                steps = self._create_default_steps(task_type, user_goal, options)

            return TaskPlan(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                steps=steps,
                estimated_duration=plan_dict.get("estimated_duration"),
            )

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            # Return default plan
            task_type = options.task_type or TaskType.RESEARCH_AND_WRITE
            return TaskPlan(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                steps=self._create_default_steps(task_type, user_goal, options),
            )

    def _create_default_steps(
        self,
        task_type: TaskType,
        user_goal: str,
        options: TaskOptions,
    ) -> list[TaskStep]:
        """Create default execution steps based on task type."""
        steps = []

        if task_type in [TaskType.RESEARCH_ONLY, TaskType.RESEARCH_AND_WRITE]:
            steps.append(
                TaskStep(
                    step_id="research",
                    agent_name="research",
                    action="Research the topic",
                    inputs={"topic": user_goal},
                    depends_on=[],
                )
            )

        if task_type in [TaskType.WRITE_ONLY, TaskType.RESEARCH_AND_WRITE]:
            depends_on = (
                ["research"] if task_type == TaskType.RESEARCH_AND_WRITE else []
            )
            steps.append(
                TaskStep(
                    step_id="write",
                    agent_name="writer",
                    action="Generate report",
                    inputs={"style": options.style},
                    depends_on=depends_on,
                )
            )

        return steps

    async def execute_plan(
        self,
        plan: TaskPlan,
        user_goal: str,
        options: TaskOptions | None = None,
    ) -> TaskResult:
        """
        Execute the plan, handling parallel/sequential agents.

        Args:
            plan: Execution plan
            user_goal: Original user goal
            options: Task options

        Returns:
            TaskResult with all outputs
        """
        options = options or TaskOptions()
        start_time = time.time()

        execution_logs: list[ExecutionLog] = []
        step_results: dict[str, Any] = {}

        # Track outputs
        findings = None
        sources = []
        final_report = None
        error_message = None
        status = TaskStatus.EXECUTING

        try:
            for step in plan.steps:
                step_start = time.time()

                logger.info(f"Executing step: {step.step_id} ({step.agent_name})")

                try:
                    if step.agent_name == "research":
                        # Execute research
                        from ..deep_researcher import run_research

                        topic = step.inputs.get("topic", user_goal)
                        result = await run_research(
                            topic=topic,
                            max_iterations=options.max_research_iterations,
                            timeout=options.timeout,
                        )

                        findings = result.findings
                        sources = [s.model_dump() for s in result.sources]
                        step_results["research"] = result

                    elif step.agent_name == "writer":
                        # Execute writer
                        from ..report_writer import run_writer

                        # Get research results if available
                        research_result = step_results.get("research")

                        if research_result:
                            result = await run_writer(
                                research_brief=research_result.research_brief
                                or user_goal,
                                findings=research_result.findings,
                                sources=[
                                    s.model_dump() for s in research_result.sources
                                ],
                                style=options.style,
                            )
                        else:
                            # Write from user-provided content
                            result = await run_writer(
                                research_brief=user_goal,
                                findings=step.inputs.get("findings", ""),
                                sources=step.inputs.get("sources", []),
                                style=options.style,
                            )

                        final_report = result.final_report
                        step_results["writer"] = result

                    step_duration = (time.time() - step_start) * 1000
                    execution_logs.append(
                        ExecutionLog(
                            step_id=step.step_id,
                            agent_name=step.agent_name,
                            status="completed",
                            duration_ms=step_duration,
                            message=f"Step completed successfully",
                        )
                    )

                except Exception as e:
                    step_duration = (time.time() - step_start) * 1000
                    error_msg = str(e)
                    logger.error(f"Step {step.step_id} failed: {error_msg}")

                    execution_logs.append(
                        ExecutionLog(
                            step_id=step.step_id,
                            agent_name=step.agent_name,
                            status="failed",
                            duration_ms=step_duration,
                            error=error_msg,
                        )
                    )

                    # Continue to next step or fail based on step criticality
                    if (
                        step.agent_name == "research"
                        and plan.task_type == TaskType.RESEARCH_AND_WRITE
                    ):
                        raise  # Can't continue without research

            status = TaskStatus.COMPLETED

        except Exception as e:
            status = TaskStatus.FAILED
            error_message = str(e)
            logger.error(f"Plan execution failed: {error_message}")

        total_duration = (time.time() - start_time) * 1000

        return TaskResult(
            task_id=plan.task_id,
            status=status,
            plan=plan,
            execution_logs=execution_logs,
            findings=findings,
            sources=sources,
            final_report=final_report,
            total_duration_ms=total_duration,
            error_message=error_message,
        )

    def reset(self):
        """Reset coordinator state for new task."""
        self.conversation_history = []
        self.clarification_rounds = 0
