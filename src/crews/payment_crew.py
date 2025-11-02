from crewai import Crew
from crewai.project import CrewBase, crew
from crewai import Agent, LLM
from crewai.project import agent
from crewai import Task
from crewai.project import task
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource

import yaml

pdf_source = PDFKnowledgeSource(
    file_paths=["rejection_policy_knowledge.pdf"]
)

llm = LLM(
    model="gpt-4o-mini", # Prod: anthropic/claude-sonnet-4-5-20250929
    temperature=0.2,
    max_tokens=1000
)

@CrewBase
class PaymentReviewCrew:
    """
    WorkSafeBC Payment Review Automation Crew

    Orchestrates multiple AI agents to automate payment review process:
    1. Policy Lookup Agent - Identifies applicable policies
    2. Summarizer Agent - Creates case summaries
    3. Payment Reviewer Agent - Makes payment decisions
    4. Escalation Agent - Routes complex cases
    """

    # Load Agent configurations
    @staticmethod
    def get_agent_config(agent_name):
        """Fetch agent settings from agents.yml by agent_name key."""
        with open('config/agents.yml', 'r') as f:
            agents_config = yaml.safe_load(f)
        try:
            return agents_config[agent_name]
        except KeyError:
            raise ValueError(f"Agent '{agent_name}' not found in agents.yml")

    @agent
    def policy_lookup(self) -> Agent:
        """Policy Compliance Specialist Agent"""
        cfg = self.get_agent_config('policy_lookup')
        return Agent(
            role=cfg['role'],
            goal=cfg['goal'],
            backstory=cfg['backstory'],
            verbose=cfg.get('verbose', True),
            allow_delegation=cfg.get('allow_delegation', False),
            llm=llm
        )

    @agent
    def summarizer(self) -> Agent:
        """Case Documentation Specialist Agent"""
        cfg = self.get_agent_config('summarizer')
        return Agent(
            role=cfg['role'],
            goal=cfg['goal'],
            backstory=cfg['backstory'],
            verbose=cfg.get('verbose', True),
            allow_delegation=cfg.get('allow_delegation', False),
            llm=llm,
            # knowledge_sources=[pdf_source] # Uncomment to enable testing PDF knowledge source
        )

    @agent
    def payment_reviewer(self) -> Agent:
        """Payment Authorization Officer Agent"""
        cfg = self.get_agent_config('payment_reviewer')
        return Agent(
            role=cfg['role'],
            goal=cfg['goal'],
            backstory=cfg['backstory'],
            verbose=cfg.get('verbose', True),
            allow_delegation=cfg.get('allow_delegation', False),
            llm=llm
        )

    @agent
    def escalation(self) -> Agent:
        """Claims Escalation Coordinator Agent"""
        cfg = self.get_agent_config('escalation')
        return Agent(
            role=cfg['role'],
            goal=cfg['goal'],
            backstory=cfg['backstory'],
            verbose=cfg.get('verbose', True),
            allow_delegation=cfg.get('allow_delegation', False),
            llm=llm
        )


    # Load Task configurations
    @staticmethod
    def get_task_config(task_name):
        """Fetch task settings from tasks.yml by task_name key."""
        with open('config/tasks.yml', 'r') as f:
            tasks_config = yaml.safe_load(f)
        try:
            return tasks_config[task_name]
        except KeyError:
            raise ValueError(f"Task '{task_name}' not found in tasks.yml")

    @task
    def retrieve_applicable_policies(self) -> Task:
        """
        Task to identify and retrieve applicable policies

        Inputs:
        - invoice_data: JSON string of invoice details
        - procedure_code: Medical procedure code
        - industry_type: Employer's industry classification

        Outputs:
        - Structured list of applicable policies
        - Coverage limits and requirements
        - Special conditions or restrictions
        """
        cfg = self.get_task_config('retrieve_applicable_policies')
        return Task(
            description=cfg['description'],
            agent=getattr(self, cfg['agent'])(),
            expected_output=cfg['expected_output']
        )

    @task
    def summarize_case(self) -> Task:
        """
        Task to create comprehensive case summary

        Inputs:
        - patient_history: JSON string of patient medical history
        - communication_logs: JSON string of communication records
        - invoice_data: JSON string of current invoice

        Outputs:
        - Comprehensive case summary
        - Key decision-making factors
        - Red flags or concerns
        """
        cfg = self.get_task_config('summarize_case')
        return Task(
            description=cfg['description'],
            agent=getattr(self, cfg['agent'])(),
            expected_output=cfg['expected_output']
        )

    @task
    def review_payment(self) -> Task:
        """
        Task to make payment decision

        Inputs:
        - invoice_data: Current invoice details
        - policy_summary: Applicable policies from previous task
        - case_summary: Patient case summary from previous task

        Outputs:
        - Decision: APPROVE, DENY, or ESCALATE
        - Confidence score (0-100%)
        - Detailed reasoning with policy citations
        - Recommended action
        """
        cfg = self.get_task_config('review_payment')
        return Task(
            description=cfg['description'],
            agent=getattr(self, cfg['agent'])(),
            expected_output=cfg['expected_output'],
            context=[getattr(self, ctx)() for ctx in cfg.get('context', [])]
        )

    @task
    def escalation_routing(self) -> Task:
        """
        Task to determine if escalation is needed

        Inputs:
        - payment_decision: Decision from payment reviewer
        - confidence_score: Confidence level of decision
        - case_summary: Case complexity information

        Outputs:
        - Escalation decision (YES/NO)
        - Target review level if escalation needed
        - Priority level (High/Medium/Low)
        - Summary of concerns
        """
        cfg = self.get_task_config('escalation_routing')
        return Task(
            description=cfg['description'],
            agent=getattr(self, cfg['agent'])(),
            expected_output=cfg['expected_output'],
            context=[getattr(self, ctx)() for ctx in cfg.get('context', [])]
        )

    # Crew Definition
    @crew
    def crew(self) -> Crew:
        """
        Creates the Payment Review Crew with all agents and tasks

        Configuration:
        - verbose=True: Detailed logging for audit trails
        - delegation=True: Agents can delegate tasks when needed

        Returns:
            Configured Crew instance ready for execution
        """

        return Crew(
            agents=[
                self.policy_lookup(),
                self.summarizer(),
                self.payment_reviewer(),
                self.escalation()
            ],
            tasks=[
                self.retrieve_applicable_policies(),
                self.summarize_case(),
                self.review_payment(),
                self.escalation_routing()
            ],
            verbose=True,
        )