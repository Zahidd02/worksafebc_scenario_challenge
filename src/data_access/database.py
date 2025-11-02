import pyodbc
from typing import List, Dict


class WorkSafeBCDataAccess:
    """Handles all database operations for the payment review system"""

    def __init__(self, connection_string: str):
        """
        Initialize database connection

        Args:
            connection_string: Azure SQL Database connection string
        """
        self.connection_string = connection_string

    def get_pending_invoices(self, limit: int = 100) -> List[Dict]:
        """
        Retrieve pending invoices that require review

        Args:
            limit: Maximum number of invoices to retrieve

        Returns:
            List of invoice dictionaries with patient and provider details
        """
        query = """
        SELECT TOP (?) 
            i.InvoiceID, i.PatientID, i.ProviderID, i.ProcedureCode,
            i.BilledAmount, i.InvoiceDate, i.Status, i.RejectionReason,
            p.FirstName, p.LastName, p.InjuryDate, p.ClaimStartDate,
            p.EmployerName, p.IndustryType, p.ReturnToWorkStatus,
            pr.ProviderName, pr.ProviderType, pr.Specialization
        FROM Invoices i
        INNER JOIN Patients p ON i.PatientID = p.PatientID
        INNER JOIN Providers pr ON i.ProviderID = pr.ProviderID
        WHERE i.Status = 'Pending Review'
        ORDER BY i.InvoiceDate ASC
        """

        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_patient_history(self, patient_id: str) -> Dict:
        """
        Get comprehensive patient medical and claim history from DB.
        Prod: This would usually be an API call to EMR endpoint provider.

        Args:
            patient_id: Unique patient identifier

        Returns:
            Dictionary containing patient details and aggregated invoice data
        """
        query = """
        SELECT 
            p.*,
            COUNT(DISTINCT i.InvoiceID) as TotalInvoices,
            SUM(CASE WHEN i.Status = 'Approved' THEN i.BilledAmount ELSE 0 END) as TotalApprovedAmount,
            MAX(i.InvoiceDate) as LastInvoiceDate
        FROM Patients p
        LEFT JOIN Invoices i ON p.PatientID = i.PatientID
        WHERE p.PatientID = ?
        GROUP BY p.PatientID, p.FirstName, p.LastName, p.DateOfBirth, 
                 p.Gender, p.AddressLine1, p.City, p.Province, p.PostalCode,
                 p.PhoneNumber, p.Email, p.EmployerName, p.IndustryType,
                 p.InjuryDate, p.ClaimStartDate, p.ClaimEndDate, 
                 p.ReturnToWorkStatus, p.CreatedAt
        """

        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (patient_id,))
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else {}

    def get_communication_logs(self, patient_id: str) -> List[Dict]:
        """
        Retrieve communication history for a patient

        Args:
            patient_id: Unique patient identifier

        Returns:
            List of communication records ordered by date (most recent first)
        """
        query = """
        SELECT CommunicationID, PatientID, CommunicationType, 
               Subject, MessageBody, SentDate, SentBy, ReceivedFrom
        FROM Communications
        WHERE PatientID = ?
        ORDER BY SentDate DESC
        """

        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (patient_id,))
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_applicable_policies(self, procedure_code: str, industry: str) -> List[Dict]:
        """
        Retrieve relevant policies for a procedure and industry

        Args:
            procedure_code: Medical procedure code
            industry: Industry type of the employer

        Returns:
            List of applicable policy dictionaries
        """
        query = """
        SELECT PolicyID, PolicyName, PolicyDescription, 
               ApplicableProcedures, MaxCoverageAmount, RequiredDocumentation
        FROM Policies
        WHERE (ApplicableProcedures LIKE ? OR ApplicableProcedures = 'All')
        AND (IndustryType = ? OR IndustryType = 'All')
        AND IsActive = 1
        """

        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (f'%{procedure_code}%', industry))
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def update_invoice_decision(
            self,
            invoice_id: str,
            decision: str,
            confidence: float,
            reasoning: str,
            reviewed_by: str = 'AI_System'
    ) -> None:
        """
        Update invoice with automated decision

        Args:
            invoice_id: Unique invoice identifier
            decision: Decision status (Approved, Denied, Escalated)
            confidence: AI confidence score (0.0 to 1.0)
            reasoning: Detailed explanation of the decision
            reviewed_by: Name of reviewer (default: AI_System)
        """
        query = """
        UPDATE Invoices
        SET Status = ?,
            ReviewedBy = ?,
            ReviewDate = SYSUTCDATETIME(),
            AIConfidenceScore = ?,
            DecisionReasoning = ?
        WHERE InvoiceID = ?
        """

        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (decision, reviewed_by, confidence, reasoning, invoice_id))
            conn.commit()

    def log_audit_entry(
            self,
            invoice_id: str,
            action: str,
            performed_by: str,
            details: str
    ) -> None:
        """
        Create audit log entry for compliance tracking

        Args:
            invoice_id: Unique invoice identifier
            action: Action performed (e.g., "AI_REVIEW", "MANUAL_OVERRIDE")
            performed_by: User or system that performed the action
            details: Additional details about the action
        """
        query = """
        INSERT INTO AuditLog (InvoiceID, Action, PerformedBy, OldValue, NewValue)
        VALUES (?, ?, ?, NULL, ?)
        """

        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (invoice_id, action, performed_by, details))
            conn.commit()