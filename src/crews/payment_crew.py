from crewai import Crew
from crewai.project import CrewBase, crew
from src.agents.payment_agents import PaymentReviewAgents
from src.tasks.payment_tasks import PaymentReviewTasks


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

    agents_config = '../../config/agents.yml'
    tasks_config = '../../config/tasks.yml'

    def __init__(self):
        """Initialize crew with data access capability"""
        self.data_access = None  # Will be injected by orchestrator
        self.agents = PaymentReviewAgents()
        self.tasks = PaymentReviewTasks(self.agents)

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
        if not self.agents:
            self.agents = PaymentReviewAgents()
        if not self.tasks:
            self.tasks = PaymentReviewTasks(self.agents)

        return Crew(
            agents=[
                self.agents.policy_lookup(),
                self.agents.summarizer(),
                self.agents.payment_reviewer(),
                self.agents.escalation()
            ],
            tasks=[
                self.tasks.retrieve_applicable_policies_task(),
                self.tasks.summarize_case_task(),
                self.tasks.review_payment_task(),
                self.tasks.escalation_routing_task()
            ],
            verbose=True,
            delegation=True,
        )

    def kickoff(self, inputs: dict):
        """
        Execute the crew with provided inputs

        Args:
            inputs: Dictionary containing:
                - invoice_data: JSON string of invoice details
                - patient_history: JSON string of patient history
                - communication_logs: JSON string of communications
                - procedure_code: Medical procedure code
                - industry_type: Employer industry
                - policy_summary: JSON string of applicable policies

        Returns:
            Crew execution result with decisions and reasoning
        """
        return self.crew().kickoff(inputs=inputs)