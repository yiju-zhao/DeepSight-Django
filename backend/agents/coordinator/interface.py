"""
Public Interface for Coordinator

This module provides the main entry point for task execution,
handling the complete flow from clarification to final output.
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable

from .schema import TaskResult, TaskOptions, TaskStatus, ClarificationResult
from .coordinator import Coordinator


logger = logging.getLogger(__name__)


async def execute_task(
    user_goal: str,
    options: Optional[TaskOptions] = None,
    clarification_callback: Optional[Callable[[ClarificationResult], Awaitable[str]]] = None,
) -> TaskResult:
    """
    Main entry point for task execution.
    
    This function handles the complete workflow:
    1. Multi-turn clarification (if needed)
    2. Plan generation
    3. Research execution (if applicable)
    4. Report writing (if applicable)
    5. Result aggregation
    
    Args:
        user_goal: The user's research goal or question.
        options: Task execution options. If None, defaults are used.
        clarification_callback: Optional async callback for handling clarification.
                               Called with ClarificationResult, should return user response.
                               If None, clarification is skipped.
    
    Returns:
        TaskResult containing:
        - task_id: Unique identifier
        - status: Final status (COMPLETED, FAILED, etc.)
        - plan: Execution plan that was used
        - execution_logs: Detailed logs of each step
        - findings: Research findings (if research was performed)
        - sources: List of sources (if research was performed)
        - final_report: Generated report (if writing was performed)
        - total_duration_ms: Total execution time
        - error_message: Error details if failed
    
    Example:
        ```python
        from agents.coordinator import execute_task, TaskOptions
        
        # Simple usage (no clarification)
        result = await execute_task(
            user_goal="Research the latest developments in LLM agents",
            options=TaskOptions(skip_clarification=True)
        )
        
        print(result.final_report)
        
        # With clarification callback
        async def handle_clarification(clarification):
            if clarification.need_clarification:
                # In a real app, you'd prompt the user here
                return "I want a comprehensive technical report"
            return ""
        
        result = await execute_task(
            user_goal="Research AI",
            clarification_callback=handle_clarification
        )
        ```
    """
    options = options or TaskOptions()
    coordinator = Coordinator()
    
    logger.info(f"Starting task execution: {user_goal[:50]}...")
    
    try:
        # Phase 1: Clarification
        requirements = {"topic": user_goal}
        
        if not options.skip_clarification and clarification_callback:
            logger.info("Starting clarification phase...")
            
            clarification = await coordinator.clarify_requirements(user_goal)
            
            while not clarification.confident and clarification.need_clarification:
                # Get user response via callback
                user_response = await clarification_callback(clarification)
                
                if not user_response:
                    # User wants to proceed anyway
                    clarification.confident = True
                    break
                
                # Continue clarification
                clarification = await coordinator.clarify_requirements(
                    user_goal, 
                    user_response
                )
            
            requirements = clarification.extracted_requirements or requirements
            logger.info(f"Clarification complete. Requirements: {requirements}")
        
        # Phase 2: Planning
        logger.info("Creating execution plan...")
        plan = await coordinator.create_plan(user_goal, requirements, options)
        logger.info(f"Plan created: {plan.task_type}, {len(plan.steps)} steps")
        
        # Phase 3: Execution
        logger.info("Executing plan...")
        result = await coordinator.execute_plan(plan, user_goal, options)
        
        logger.info(
            f"Task completed: status={result.status}, "
            f"duration={result.total_duration_ms:.0f}ms"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        return TaskResult(
            task_id="error",
            status=TaskStatus.FAILED,
            error_message=str(e),
        )


def execute_task_sync(
    user_goal: str,
    options: Optional[TaskOptions] = None,
) -> TaskResult:
    """
    Synchronous wrapper for execute_task.
    
    Note: This version does not support clarification callbacks.
    Use execute_task() directly for async code with clarification.
    
    Args:
        user_goal: The user's research goal
        options: Task execution options (skip_clarification is forced True)
    
    Returns:
        Same as execute_task()
    """
    options = options or TaskOptions()
    options.skip_clarification = True  # Must skip for sync version
    
    return asyncio.run(execute_task(user_goal, options))


async def execute_research_and_write(
    topic: str,
    style: str = "academic",
    timeout: Optional[float] = None,
) -> TaskResult:
    """
    Convenience function for the common research-and-write workflow.
    
    This is a simplified interface that skips clarification and
    directly performs research followed by report generation.
    
    Args:
        topic: Research topic
        style: Writing style ('academic', 'casual', 'technical', 'business')
        timeout: Overall timeout in seconds
    
    Returns:
        TaskResult with findings and final_report
    """
    from .schema import TaskType
    
    options = TaskOptions(
        task_type=TaskType.RESEARCH_AND_WRITE,
        style=style,
        timeout=timeout,
        skip_clarification=True,
    )
    
    return await execute_task(topic, options)
