import pandas as pd
from datetime import datetime, timedelta

# Read existing appointments
appointments_df = pd.read_csv('appointments.csv')
doctors_df = pd.read_csv('doctors.csv')

# Get today's date and next few days
today = datetime.now()
tomorrow = today + timedelta(days=1)
day_after = today + timedelta(days=2)

# Get some patient IDs and doctor IDs for demo
patient_ids = ['P001', 'P002', 'P003', 'P004', 'P005', 'P006', 'P007', 'P008', 'P009', 'P010']
doctor_ids = doctors_df['doctor_id'].tolist()[:5]  # First 5 doctors

# Create new appointments for demonstration
new_appointments = []

# Today's appointments (just booked)
for i, patient_id in enumerate(patient_ids[:5]):
    appointment_id = f"A{len(appointments_df) + i + 1:04d}"
    doctor_id = doctor_ids[i % len(doctor_ids)]
    new_appointments.append({
        'appointment_id': appointment_id,
        'patient_id': patient_id,
        'doctor_id': doctor_id,
        'appointment_date': today.strftime('%Y-%m-%d'),
        'appointment_time': f"{9 + i}:00:00",
        'reason_for_visit': ['Consultation', 'Follow-up', 'Checkup', 'Emergency', 'Therapy'][i],
        'status': 'Scheduled',
        'appointment_datetime': f"{today.strftime('%Y-%m-%d')} {9 + i}:00:00",
        'Severity_Score': [5, 3, 5, 5, 5][i]
    })

# Tomorrow's appointments
for i, patient_id in enumerate(patient_ids[5:8]):
    appointment_id = f"A{len(appointments_df) + len(new_appointments) + 1:04d}"
    doctor_id = doctor_ids[(i + 2) % len(doctor_ids)]
    new_appointments.append({
        'appointment_id': appointment_id,
        'patient_id': patient_id,
        'doctor_id': doctor_id,
        'appointment_date': tomorrow.strftime('%Y-%m-%d'),
        'appointment_time': f"{10 + i}:30:00",
        'reason_for_visit': ['Consultation', 'Follow-up', 'Checkup'][i],
        'status': 'Scheduled',
        'appointment_datetime': f"{tomorrow.strftime('%Y-%m-%d')} {10 + i}:30:00",
        'Severity_Score': [5, 3, 5][i]
    })

# Add new appointments to dataframe
new_df = pd.DataFrame(new_appointments)
appointments_df = pd.concat([appointments_df, new_df], ignore_index=True)

# Save
appointments_df.to_csv('appointments.csv', index=False)
print(f"Added {len(new_appointments)} new appointments for demonstration!")
print(f"Today: {today.strftime('%Y-%m-%d')} - {len([a for a in new_appointments if a['appointment_date'] == today.strftime('%Y-%m-%d')])} appointments")
print(f"Tomorrow: {tomorrow.strftime('%Y-%m-%d')} - {len([a for a in new_appointments if a['appointment_date'] == tomorrow.strftime('%Y-%m-%d')])} appointments")

