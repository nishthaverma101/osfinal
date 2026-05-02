import pandas as pd

patients_df = pd.read_csv(r'C:\Users\karvi\OneDrive\Desktop\Hospital Project\patients.csv')
appointments_df = pd.read_csv(r'C:\Users\karvi\OneDrive\Desktop\Hospital Project\appointments.csv')
doctors_df = pd.read_csv(r'C:\Users\karvi\OneDrive\Desktop\Hospital Project\doctors.csv')
treatments_df = pd.read_csv(r'C:\Users\karvi\OneDrive\Desktop\Hospital Project\treatments.csv')
billing_df = pd.read_csv(r'C:\Users\karvi\OneDrive\Desktop\Hospital Project\billing.csv')

print('Patients:', patients_df.head())
print('Appointments:', appointments_df.head())
print('Doctors:', doctors_df.head())
print('Treatments:', treatments_df.head())
print('Billing:', billing_df.head())

