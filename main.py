"""
File: main.py
Entry point for WorkSafeBC Payment Review System
"""

import os
from dotenv import load_dotenv
from src.orchestration.orchestrator import PaymentReviewOrchestrator

def main():
    """
    Main execution function for batch processing invoices
    """
    # Load environment variables
    load_dotenv()

    # Configure database connection from environment
    connection_string = (
        f"Driver={os.getenv('AZURE_SQL_DRIVER')};"
        f"Server={os.getenv('AZURE_SQL_SERVER')};"
        f"Database={os.getenv('AZURE_SQL_DATABASE')};"
        f"UID={os.getenv('AZURE_SQL_USER')};"
        f"PWD={os.getenv('AZURE_SQL_PASSWORD')};"
    )

    # Initialize orchestrator
    print("Initializing WorkSafeBC Payment Review System...")
    orchestrator = PaymentReviewOrchestrator(connection_string)

    # Process batch of invoices
    batch_size = int(os.getenv('BATCH_SIZE', '2'))
    print(f"\nStarting automated payment review process (batch size: {batch_size})...")

    results = orchestrator.process_batch(batch_size=batch_size)

    # Display results
    print(f"\n{'=' * 60}")
    print("PROCESSING COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total Processed:  {results['processed']}")
    print(f"  ├─ Approved:    {results['approved']} ({results['approved'] / results['processed'] * 100:.1f}%)")
    print(f"  ├─ Denied:      {results['denied']} ({results['denied'] / results['processed'] * 100:.1f}%)")
    print(f"  └─ Escalated:   {results['escalated']} ({results['escalated'] / results['processed'] * 100:.1f}%)")
    print(f"\nErrors:           {results['errors']}")

    if results['processed'] > 0:
        success_rate = (results['processed'] / (results['processed'] + results['errors']) * 100)
        print(f"Success Rate:     {success_rate:.1f}%")

    # Display sample details
    if results['details']:
        print(f"\n{'=' * 60}")
        print("SAMPLE RESULTS (First 5)")
        print(f"{'=' * 60}")
        for detail in results['details'][:5]:
            print(f"\nInvoice ID:      {detail['invoice_id']}")
            print(f"Patient:         {detail['patient_name']}")
            print(f"Procedure:       {detail['procedure_code']}")
            print(f"Amount:          ${detail['billed_amount']:.2f}")
            print(f"Decision:        {detail['decision']}")
            print(f"Confidence:      {detail['confidence']:.1%}")
            print(f"{'-' * 60}")

    print(f"\nProcessing complete. Check database for full details.")


if __name__ == "__main__":
    main()