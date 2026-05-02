import pandas as pd

def clean_and_prepare_data(df):
    # Combine appointment_date and appointment_time into one datetime column
    df['appointment_datetime'] = pd.to_datetime(
        df['appointment_date'].astype(str) + ' ' + df['appointment_time'].astype(str),
        errors='coerce'
    )
    # Fill missing or blank reason_for_visit with 'routine'
    df['reason_for_visit'] = df['reason_for_visit'].fillna('routine')
    df.loc[df['reason_for_visit'].str.strip() == '', 'reason_for_visit'] = 'routine'
    return df


def assign_severity(reason_for_visit):
    # Assign a base score
    if 'cardiac arrest' in reason_for_visit.lower():
        severity = 1  # highest priority = 1
    elif 'stroke' in reason_for_visit.lower():
        severity = 2
    elif 'follow-up' in reason_for_visit.lower():
        severity = 3
    elif 'scheduled' in reason_for_visit.lower():
        severity = 4
    else:
        severity = 5  # least urgent

    return severity

def apply_severity(df):
    df['Severity_Score'] = df['reason_for_visit'].apply(assign_severity)
    return df

def estimate_wait_time(queue_df, doctors_available, avg_consult_time):
    queue_df = queue_df.copy()
    queue_df['Patients_Ahead'] = range(len(queue_df))
    queue_df['Estimated_Wait_Time'] = (queue_df['Patients_Ahead'] / doctors_available) * avg_consult_time
    return queue_df

def update_patient_severity(df, patient_id, new_reason_for_visit):
    """
    Update the severity of a specific patient based on new reason for visit.
    """
    # Update reason_for_visit
    df.loc[df['patient_id'] == patient_id, 'reason_for_visit'] = new_reason_for_visit
    
    # Recalculate severity score for updated patient
    df.loc[df['patient_id'] == patient_id, 'Severity_Score'] = assign_severity(new_reason_for_visit)
    
    return df

def reorder_full_queues(df, doctors_available, avg_consult_time):
    # Priority queue = severity 1 and 2 (highest priority)
    priority = df[(df['Severity_Score'] == 1) | (df['Severity_Score'] == 2)].sort_values('appointment_datetime')
    # Medium = severity 3 and 4
    medium = df[(df['Severity_Score'] == 3) | (df['Severity_Score'] == 4)].sort_values('appointment_datetime')
    # Low = severity 5 (lowest priority)
    low = df[df['Severity_Score'] == 5].sort_values('appointment_datetime')

    priority = estimate_wait_time(priority, doctors_available, avg_consult_time)
    medium = estimate_wait_time(medium, doctors_available, avg_consult_time)
    low = estimate_wait_time(low, doctors_available, avg_consult_time)

    return {'priority': priority, 'medium': medium, 'low': low}


def process_all_queues(df, doctors_available, avg_consult_time):
    priority_queue = df[(df['Severity_Score'] == 1) | (df['Severity_Score'] == 2)].sort_values('appointment_datetime')
    priority_queue = priority_queue.drop_duplicates(subset='patient_id', keep='first')

    medium_queue = df[(df['Severity_Score'] == 3) | (df['Severity_Score'] == 4)].sort_values('appointment_datetime')
    medium_queue = medium_queue.drop_duplicates(subset='patient_id', keep='first')

    low_queue = df[df['Severity_Score'] == 5].sort_values('appointment_datetime')
    low_queue = low_queue.drop_duplicates(subset='patient_id', keep='first')

    priority_queue = estimate_wait_time(priority_queue, doctors_available, avg_consult_time)
    medium_queue = estimate_wait_time(medium_queue, doctors_available, avg_consult_time)
    low_queue = estimate_wait_time(low_queue, doctors_available, avg_consult_time)

    return {
        'priority': priority_queue,
        'medium': medium_queue,
        'low': low_queue,
    }
def start_consultation(df, appointment_id):
    # Check if appointment exists
    if appointment_id not in df['appointment_id'].values:
        print(f"Appointment ID {appointment_id} not found")
        return df
    # Get current status
    current_status = df.loc[df['appointment_id'] == appointment_id, 'status'].values[0]
    print(f"Current status for {appointment_id}: {current_status}")
    # Update status if not already in session or completed
    if current_status not in ['in-session', 'completed']:
        df.loc[df['appointment_id'] == appointment_id, 'status'] = 'in-session'
        print(f"Status updated to in-session for {appointment_id}")
    else:
        print(f"No update needed, status is {current_status}")
    return df


def complete_consultation(df, appointment_id):
    if (df['appointment_id'] == appointment_id).any():
        df.loc[df['appointment_id'] == appointment_id, 'status'] = 'completed'
    else:
        print(f"Appointment ID {appointment_id} not found in complete_consultation.")
    return df


