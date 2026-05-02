import multiprocessing
import time
import random
import csv

def lab_process(mailbox):
    doctors = ['D001', 'D002', 'D003']
    patients = ['P001', 'P002', 'P003', 'P004']
    test_types = ['Blood Test', 'X-Ray', 'ECG', 'MRI']

    for i in range(6):
        doctor_id = random.choice(doctors)
        patient_id = random.choice(patients)
        test = random.choice(test_types)
        value = random.randint(50, 150)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        report = {
            'doctor_id': doctor_id,
            'timestamp': timestamp,
            'patient_id': patient_id,
            'test': test,
            'value': value
        }
        print(f"[Lab] Sending to {doctor_id}: {report}")
        mailbox.put(report)
        # Save to CSV immediately
        with open('labreport.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([doctor_id, timestamp, patient_id, test, value])
        time.sleep(random.randint(1, 3))

    mailbox.put(None)

def doctor_dashboard(mailbox, doctor_id):
    print(f"[Doctor {doctor_id}] Dashboard started. Waiting for reports...")
    while True:
        report = mailbox.get()
        if report is None:
            print(f"[Doctor {doctor_id}] No more reports.")
            break
        if report.get('doctor_id') == doctor_id:
            print(f"[Doctor {doctor_id}] New Mail: {report}")

if __name__ == '__main__':
    mailbox = multiprocessing.Queue()
    lab = multiprocessing.Process(target=lab_process, args=(mailbox,))
    doctor1 = multiprocessing.Process(target=doctor_dashboard, args=(mailbox, 'D001'))
    doctor2 = multiprocessing.Process(target=doctor_dashboard, args=(mailbox, 'D002'))
    doctor3 = multiprocessing.Process(target=doctor_dashboard, args=(mailbox, 'D003'))

    lab.start()
    doctor1.start()
    doctor2.start()
    doctor3.start()

    lab.join()
    doctor1.join()
    doctor2.join()
    doctor3.join()

    print("Simulation finished.")
