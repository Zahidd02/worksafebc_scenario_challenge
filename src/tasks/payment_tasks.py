"""
File: src/tasks/payment_tasks.py
CrewAI tasks for WorkSafeBC Payment Review System
"""

from crewai import Task
from crewai.project import task
from src.agents.payment_agents import PaymentReviewAgents


class PaymentReviewTasks:
    """Factory class for creating payment review tasks"""

    def __init__(self, agents: PaymentReviewAgents):
        """
        Initialize tasks with agent references

        Args:
            agents: Instance of PaymentReviewAgents
        """
        self.agents = agents

    @task
    def retrieve_applicable_policies_task(self) -> Task:
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
        return Task(
            description="""Analyze the invoice details and retrieve all applicable WorkSafeBC policies:
            - Invoice: {invoice_data}
            - Procedure Code: {procedure_code}
            - Industry: {industry_type}

            Identify:
            1. Relevant billing policies for the procedure code
            2. Industry-specific coverage rules
            3. Maximum coverage amounts
            4. Required documentation standards
            5. Any special conditions or restrictions

            Return a structured summary of applicable policies.""",
            agent=self.agents.policy_lookup(),
            expected_output="Structured list of applicable policies with coverage details and requirements"
        )

    @task
    def summarize_case_task(self) -> Task:
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
        return Task(
            description="""Create a comprehensive case summary for payment review:
            - Patient History: {patient_history}
            - Communication Logs: {communication_logs}
            - Current Invoice: {invoice_data}

            Summarize:
            1. Patient injury details and claim timeline
            2. Previous treatment and billing history
            3. Relevant communications with providers and patient
            4. Current claim status and return-to-work progress
            5. Any red flags or concerns

            Provide a concise, actionable summary for payment decision.""",
            agent=self.agents.summarizer(),
            expected_output="Comprehensive case summary with key decision-making information"
        )

    @task
    def review_payment_task(self) -> Task:
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
        return Task(
            description="""Review the invoice and make a payment decision:
            - Invoice Details: {invoice_data}
            - Applicable Policies: {policy_summary}
            - Case Summary: {case_summary}

            Evaluate:
            1. Does the procedure code match policy coverage?
            2. Is the billed amount within policy limits?
            3. Is documentation sufficient?
            4. Are there any timing or eligibility issues?
            5. Does the treatment align with injury type?

            Provide:
            - Decision: APPROVE, DENY, or ESCALATE
            - Confidence Score: 0-100%
            - Detailed reasoning
            - Recommended action""",
            agent=self.agents.payment_reviewer(),
            expected_output="Payment decision with confidence score and detailed reasoning",
            context=[
                self.retrieve_applicable_policies_task(),
                self.summarize_case_task()
            ]
        )

    @task
    def escalation_routing_task(self) -> Task:
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
        return Task(
            description="""Review the payment decision and determine if escalation is needed:
            - Payment Decision: {payment_decision}
            - Confidence Score: {confidence_score}
            - Case Complexity: {case_summary}

            Escalate if:
            1. Confidence score < 75%
            2. Policy conflicts detected
            3. Billed amount exceeds typical range by >30%
            4. Missing critical documentation
            5. First-time complex procedure

            If escalation needed:
            - Identify appropriate review level (Senior Officer, Medical Advisor, etc.)
            - Summarize key concerns
            - Recommend priority level

            If no escalation:
            - Confirm automated processing is appropriate""",
            agent=self.agents.escalation(),
            expected_output="Escalation decision with routing details or confirmation for automated processing",
            context=[self.review_payment_task()]
        )