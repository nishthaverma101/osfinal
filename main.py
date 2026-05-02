# main.py

import pandas as pd
from Hospital_utils import (
    clean_and_prepare_data,
    apply_severity,
    update_patient_severity,
    process_all_queues
)

def main():
    # Load your data files
    patients_df = pd.read_csv('patients.csv')
    appointments_df = pd.read_csv('appointments.csv')
    doctors_df = pd.read_csv('doctors.csv')
    treatments_df = pd.read_csv('treatments.csv')
    billing_df = pd.read_csv('billing.csv')

    print('Appointments Columns:', appointments_df.columns)

    # Step 1: Clean and prepare appointment datetime and reason
    appointments_df = clean_and_prepare_data(appointments_df)

    # Step 2: Assign severity scores based on reason for visit
    appointments_df = apply_severity(appointments_df)

    # Step 3: Process all queues and calculate estimated wait times
    queues = process_all_queues(appointments_df, doctors_available=3, avg_consult_time=15)

    # Display queue information
    print("\nPriority Queue:")
    print(queues['priority'][['patient_id', 'Severity_Score', 'Estimated_Wait_Time']])

    print("\nMedium Queue:")
    print(queues['medium'][['patient_id', 'Severity_Score', 'Estimated_Wait_Time']])

    print("\nLow Queue:")
    print(queues['low'][['patient_id', 'Severity_Score', 'Estimated_Wait_Time']])

    # Example: Update severity of a patient dynamically
    appointments_df = update_patient_severity(appointments_df, patient_id='P003', new_reason_for_visit='emergency surgery')

    # Recalculate queues after the update
    queues = process_all_queues(appointments_df, doctors_available=3, avg_consult_time=15)

    print("\nUpdated Priority Queue After Severity Change:")
    print(queues['priority'][['patient_id', 'Severity_Score', 'Estimated_Wait_Time']])

if __name__ == "__main__":
    main()
