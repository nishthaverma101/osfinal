from flask import Flask, render_template
import pandas as pd
import os

app = Flask(__name__)

@app.route('/doctor/<doctor_id>')
def doctor_dashboard(doctor_id):
    reports = []
    if os.path.exists('labreport.csv'):
        try:
            df = pd.read_csv('labreport.csv')
            if 'doctor_id' in df.columns:
                doctor_reports = df[df['doctor_id'] == doctor_id]
                reports = doctor_reports.to_dict(orient='records')
        except Exception as e:
            print("Error reading CSV:", e)
            reports = []
    return render_template('doctor_dashboard.html', reports=reports, doctor_id=doctor_id)

if __name__ == "__main__":
    app.run(debug=True)
