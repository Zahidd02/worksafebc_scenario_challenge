import json
import re
from typing import Dict, Any

from src.data_access.database import WorkSafeBCDataAccess
from src.crews.payment_crew import PaymentReviewCrew

class PaymentReviewOrchestrator:
    """
    Main orchestrator for automated payment review process

    Responsibilities:
    - Coordinate data retrieval from database
    - Execute CrewAI pipeline for each invoice
    - Parse AI decisions and update database
    - Track processing statistics
    """

    def __init__(self, db_connection_string: str):
        """
        Initialize orchestrator with database connection

        Args:
            db_connection_string: Azure SQL Database connection string
        """
        self.data_access = WorkSafeBCDataAccess(db_connection_string)
        self.crew_instance = PaymentReviewCrew()
        self.crew_instance.data_access = self.data_access

    def process_invoice(self, invoice_data: Dict) -> Dict:
        """
        Process a single invoice through the CrewAI pipeline

        Args:
            invoice_data: Dictionary containing invoice details

        Returns:
            Crew execution result with decision and reasoning
        """
        # Gather all necessary context for processing the invoice
        patient_history = self.data_access.get_patient_history(
            invoice_data['PatientID']
        )

        communication_logs = self.data_access.get_communication_logs(
            invoice_data['PatientID']
        )

        applicable_policies = self.data_access.get_applicable_policies(
            invoice_data['ProcedureCode'],
            invoice_data['IndustryType']
        )

        # Prepare inputs for the crew
        inputs = {
            'invoice_data': json.dumps(invoice_data, default=str),
            'patient_history': json.dumps(patient_history, default=str),
            'communication_logs': json.dumps(communication_logs, default=str),
            'procedure_code': invoice_data['ProcedureCode'],
            'industry_type': invoice_data['IndustryType'],
            'policy_summary': json.dumps(applicable_policies, default=str),
            'case_summary': '',  # Will be filled by summarizer agent
            'payment_decision': '',  # Will be filled by payment_reviewer agent
            'confidence_score': 0  # Will be filled by payment_reviewer agent
        }

        # Execute the crew with delegation enabled
        result = self.crew_instance.crew().kickoff(inputs=inputs)

        return result

    def process_batch(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Process a batch of pending invoices

        Args:
            batch_size: Number of invoices to process in this batch

        Returns:
            Dictionary containing processing statistics:
            - processed: Number of successfully processed invoices
            - approved: Number of approved invoices
            - denied: Number of denied invoices
            - escalated: Number of escalated invoices
            - errors: Number of processing errors
            - details: List of individual results
        """
        pending_invoices = self.data_access.get_pending_invoices(limit=batch_size)

        results = {
            'processed': 0,
            'approved': 0,
            'denied': 0,
            'escalated': 0,
            'errors': 0,
            'details': []
        }

        for invoice in pending_invoices:
            try:
                # Process invoice through AI pipeline
                result = self.process_invoice(invoice)

                # Parse result and extract decision components
                decision = self._extract_decision(result)
                confidence = self._extract_confidence(result)
                reasoning = self._extract_reasoning(result)

                # Update invoice in database
                self.data_access.update_invoice_decision(
                    invoice['InvoiceID'],
                    decision,
                    confidence,
                    reasoning
                )

                # Log audit entry for compliance
                self.data_access.log_audit_entry(
                    invoice['InvoiceID'],
                    'AI_AUTOMATED_REVIEW',
                    'PaymentReviewCrew',
                    f"Decision: {decision}, Confidence: {confidence:.2%}"
                )

                # Update statistics
                results['processed'] += 1
                if decision == 'Approved':
                    results['approved'] += 1
                elif decision == 'Denied':
                    results['denied'] += 1
                else:
                    results['escalated'] += 1

                results['details'].append({
                    'invoice_id': invoice['InvoiceID'],
                    'patient_name': f"{invoice['FirstName']} {invoice['LastName']}",
                    'procedure_code': invoice['ProcedureCode'],
                    'billed_amount': float(invoice['BilledAmount']),
                    'decision': decision,
                    'confidence': confidence
                })

            except Exception as e:
                results['errors'] += 1
                error_msg = f"Error processing invoice {invoice['InvoiceID']}: {str(e)}"
                print(error_msg)

                # Log error to audit trail
                try:
                    self.data_access.log_audit_entry(
                        invoice['InvoiceID'],
                        'AI_PROCESSING_ERROR',
                        'PaymentReviewCrew',
                        error_msg
                    )
                except:
                    pass  # Don't fail if audit logging fails

        return results

    def _extract_decision(self, crew_result) -> str:
        """
        Extract decision from crew output

        Args:
            crew_result: Raw output from crew execution

        Returns:
            Decision status: 'Approved', 'Denied', or 'Escalated'
        """
        result_text = str(crew_result).upper()

        if 'APPROVE' in result_text and 'DENY' not in result_text:
            return 'Approved'
        elif 'DENY' in result_text:
            return 'Denied'
        elif 'ESCALATE' in result_text:
            return 'Escalated'
        else:
            # Default to escalation if decision is unclear
            return 'Escalated'

    def _extract_confidence(self, crew_result) -> float:
        """
        Extract confidence score from crew output

        Args:
            crew_result: Raw output from crew execution

        Returns:
            Confidence score as float between 0.0 and 1.0
        """
        result_text = str(crew_result)

        # Try to find percentage format (e.g., "85%")
        match = re.search(r'(\d+)%', result_text)
        if match:
            return float(match.group(1)) / 100.0

        # Try to find decimal format (e.g., "0.85")
        match = re.search(r'confidence[:\s]+(\d+\.\d+)', result_text, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Default to moderate confidence if not found
        return 0.5

    def _extract_reasoning(self, crew_result) -> str:
        """
        Extract reasoning from crew output

        Args:
            crew_result: Raw output from crew execution

        Returns:
            Reasoning text (truncated to 500 characters for database)
        """
        reasoning = str(crew_result)

        # Truncate for database storage (DecisionReasoning field)
        if len(reasoning) > 500:
            reasoning = reasoning[:497] + "..."

        return reasoning

    def get_processing_summary(self) -> Dict[str, Any]:
        """
        Get summary of current processing status

        Returns:
            Dictionary with current backlog and processing stats
        """
        # This would query the database for current statistics
        # Implementation depends on specific reporting requirements
        pass