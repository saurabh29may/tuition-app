import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# -------------------------------
# Database setup
# -------------------------------
conn = sqlite3.connect('tuition.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    grade TEXT,
    monthly_fee INTEGER,
    start_date TEXT,
    contact TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    month TEXT,
    amount_paid INTEGER,
    payment_date TEXT,
    payment_mode TEXT,
    FOREIGN KEY(student_id) REFERENCES students(student_id)
)''')
conn.commit()

# -------------------------------
# App UI
# -------------------------------
st.title("🎓 Smart Tuition Fee Tracker")
menu = ["Dashboard", "Add Student", "Record Payment", "View Payments"]
choice = st.sidebar.selectbox("Menu", menu)

# -------------------------------
# Add Student
# -------------------------------
if choice == "Add Student":
    st.subheader("Add New Student")
    name = st.text_input("Student Name")
    grade = st.text_input("Grade / Class")
    monthly_fee = st.number_input("Monthly Fee", min_value=0)
    start_date = st.date_input("Start Date")
    contact = st.text_input("Contact Info")

    if st.button("Add Student"):
        c.execute("INSERT INTO students (name, grade, monthly_fee, start_date, contact) VALUES (?, ?, ?, ?, ?)",
                  (name, grade, monthly_fee, start_date.strftime("%Y-%m-%d"), contact))
        conn.commit()
        st.success(f"✅ {name} added successfully!")

# -------------------------------
# Record Payment
# -------------------------------
elif choice == "Record Payment":
    st.subheader("Record Monthly Payment")
    students = pd.read_sql("SELECT * FROM students", conn)
    student_names = students['name'].tolist()
    if student_names:
        selected_student = st.selectbox("Select Student", student_names)
        student_row = students[students['name'] == selected_student].iloc[0]
        month = st.text_input("Month (e.g. Nov 2025)")
        amount = st.number_input("Amount Paid", min_value=0)
        payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer"])
        if st.button("Record Payment"):
            c.execute("INSERT INTO payments (student_id, month, amount_paid, payment_date, payment_mode) VALUES (?, ?, ?, ?, ?)",
                      (student_row['student_id'], month, amount, datetime.now().strftime("%Y-%m-%d"), payment_mode))
            conn.commit()
            st.success(f"💰 Payment of ₹{amount} recorded for {selected_student}")
    else:
        st.warning("No students found. Please add a student first.")

# -------------------------------
# Dashboard
# -------------------------------
elif choice == "Dashboard":
    st.subheader("📊 Dashboard")
    payments_df = pd.read_sql("SELECT * FROM payments", conn)
    students_df = pd.read_sql("SELECT * FROM students", conn)

    total_collected = payments_df['amount_paid'].sum() if not payments_df.empty else 0
    st.metric("Total Collected (All Time)", f"₹{total_collected}")

    if not students_df.empty:
        current_month = datetime.now().strftime("%b %Y")
        paid_students = payments_df[payments_df['month'] == current_month]['student_id'].unique().tolist()
        unpaid_students = students_df[~students_df['student_id'].isin(paid_students)]
        st.write(f"### Unpaid Students for {current_month}")
        st.dataframe(unpaid_students[['name', 'grade', 'contact']])
    else:
        st.info("No students yet.")

# -------------------------------
# View Payments
# -------------------------------
elif choice == "View Payments":
    st.subheader("📜 Payment Records")
    df = pd.read_sql('''
        SELECT s.name, p.month, p.amount_paid, p.payment_mode, p.payment_date
        FROM payments p
        JOIN students s ON p.student_id = s.student_id
        ORDER BY p.payment_date DESC
    ''', conn)

    st.dataframe(df)

    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "payments.csv", "text/csv")
