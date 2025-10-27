"""Panel crew collaboration module for podcast generation."""

import logging
import os
from pathlib import Path

from crewai import LLM, Agent, Crew, Process, Task
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.project import CrewBase, agent, crew, task

from .tools import SafeSearchTool

# Store in project directory
project_root = Path(__file__).parent
storage_dir = project_root / "crewai_storage"

os.environ["CREWAI_STORAGE_DIR"] = str(storage_dir)

# Configure logging
logger = logging.getLogger(__name__)

# LLM configurations
research_llm = LLM(model="openai/gpt-4.1", temperature=0.5)
design_llm = LLM(model="openai/gpt-4.1", temperature=0.7)
editor_llm = LLM(model="openai/gpt-4.1", temperature=0.1)


@CrewBase
class PanelCrewCollaboration:
    """Podcast generation crew with 5-step workflow: Research -> Role Design -> Framework Design -> Script Writing -> Editing"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, material_content: str = "") -> None:
        # CrewBase-decorated classes shouldn't call super().__init__()
        # Tools
        self.search_tool = SafeSearchTool()

        # Create knowledge source from material content if provided
        if material_content:
            self.knowledge_source = StringKnowledgeSource(
                content=f"Discussion Material Content:\n\n{material_content}"
            )
        else:
            self.knowledge_source = ""

    # ==================== AGENTS ====================

    @agent
    def researcher(self) -> Agent:
        """Research specialist who conducts in-depth research on the topic"""
        return Agent(
            config=self.agents_config["researcher"],
            tools=[self.search_tool],
            llm=research_llm,
        )

    @agent
    def podcast_designer(self) -> Agent:
        """Podcast designer who handles role design, framework design, and script writing"""
        return Agent(config=self.agents_config["podcast_designer"], llm=design_llm)

    @agent
    def editor(self) -> Agent:
        """Editor who polishes the script and fact-checks technical content"""
        return Agent(
            config=self.agents_config["editor"],
            tools=[self.search_tool],
            llm=editor_llm,
        )

    # ==================== TASKS ====================

    @task
    def research_task(self) -> Task:
        """Step 1: Conduct in-depth research on the topic"""
        return Task(config=self.tasks_config["research_task"])

    @task
    def role_design_task(self) -> Task:
        """Step 2: Design expert roles for the podcast based on research notes"""
        return Task(
            config=self.tasks_config["role_design_task"], context=[self.research_task()]
        )

    @task
    def framework_design_task(self) -> Task:
        """Step 3: Design discussion framework/outline based on research and roles"""
        return Task(
            config=self.tasks_config["framework_design_task"],
            context=[self.research_task(), self.role_design_task()],
        )

    @task
    def script_writing_task(self) -> Task:
        """Step 4: Write complete podcast script based on research, roles, and framework"""
        return Task(
            config=self.tasks_config["script_writing_task"],
            context=[
                self.research_task(),
                self.role_design_task(),
                self.framework_design_task(),
            ],
        )

    @task
    def editing_task(self) -> Task:
        """Step 5: Polish script and fact-check content"""
        return Task(
            config=self.tasks_config["editing_task"],
            context=[self.script_writing_task(), self.research_task()],
        )

    # ==================== CREW ====================

    @crew
    def crew(self) -> Crew:
        """Creates the podcast generation crew with sequential 5-step workflow"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            knowledge_sources=[self.knowledge_source],
        )
