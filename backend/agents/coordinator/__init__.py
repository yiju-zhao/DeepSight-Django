"""
Coordinator Module

This module provides the main orchestration layer for multi-agent workflows.
The Coordinator handles user goal collection, multi-turn clarification,
plan generation, and task execution across research and writer agents.
"""

from .interface import execute_task
from .schema import TaskResult, TaskPlan, TaskOptions

__all__ = ["execute_task", "TaskResult", "TaskPlan", "TaskOptions"]
