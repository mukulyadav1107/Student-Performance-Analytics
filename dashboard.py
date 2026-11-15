
import streamlit as st
import pandas as pd
import requests
import plotly.express as px

API = "https://studentanalytics-api-mukul-2026-hbf4aze8avccbghx.southeastasia-01.azurewebsites.net/api"

st.set_page_config(
    page_title="Student Analytics Dashboard",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Student Performance & Attendance Analytics")
st.caption("Azure-Based Student Analytics System")

# Fetch data from Azure
@st.cache_data(ttl=10)
def get_students():
    response = requests.get(
        f"{API}/Students", timeout=20
    )
    response.raise_for_status()
    return response.json().get("students", [])

@st.cache_data(ttl=10)
def get_analytics():
    response = requests.get(
        f"{API}/Analytics", timeout=20
    )
    response.raise_for_status()
    return response.json()

try:
    students = get_students()
    analytics = get_analytics()

except requests.RequestException as error:
    st.error(f"Unable to connect to Azure API: {error}")
    st.stop()

df = pd.DataFrame(students)

# Navigation
dashboard_tab, add_tab, records_tab = st.tabs([
    "📊 Dashboard",
    "➕ Add Student",
    "👨‍🎓 Student Records"
])

# DASHBOARD
with dashboard_tab:

    st.subheader("Class Overview")

    if not students:
        st.info("No student records available yet.")
    else:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Students",
            analytics["total_students"]
        )

        col2.metric(
            "Average Marks",
            analytics["average_marks"]
        )

        col3.metric(
            "Average Attendance",
            f'{analytics["average_attendance"]}%'
        )

        col4.metric(
            "Pass Percentage",
            f'{analytics["pass_percentage"]}%'
        )

        st.divider()

        left, right = st.columns(2)

        with left:
            st.subheader("Student Marks")

            marks_chart = px.bar(
                df,
                x="student_name",
                y="marks",
                color="performance",
                title="Marks by Student",
                labels={
                    "student_name": "Student",
                    "marks": "Marks"
                }
            )

            st.plotly_chart(
                marks_chart,
                use_container_width=True
            )

        with right:
            st.subheader("Attendance Analysis")

            attendance_chart = px.bar(
                df,
                x="student_name",
                y="attendance_percentage",
                color="attendance_percentage",
                title="Attendance by Student",
                labels={
                    "student_name": "Student",
                    "attendance_percentage": "Attendance (%)"
                }
            )

            st.plotly_chart(
                attendance_chart,
                use_container_width=True
            )

        st.subheader("Pass and Fail Analysis")

        pass_data = pd.DataFrame({
            "Result": ["Passed", "Failed"],
            "Students": [
                analytics["passed_students"],
                analytics["failed_students"]
            ]
        })

        pie_chart = px.pie(
            pass_data,
            names="Result",
            values="Students",
            hole=0.4
        )

        st.plotly_chart(
            pie_chart,
            use_container_width=True
        )

        st.subheader("Students Needing Academic Support")

        support = analytics.get(
            "students_needing_support", []
        )

        if support:
            st.dataframe(
                pd.DataFrame(support),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("No students currently need support.")

# ADD STUDENT
with add_tab:

    st.subheader("Register Student")

    with st.form("student_form"):

        name = st.text_input("Student Name")
        roll = st.text_input("Roll Number")

        col1, col2 = st.columns(2)

        with col1:
            total_classes = st.number_input(
                "Total Classes",
                min_value=1,
                value=100
            )

            marks = st.number_input(
                "Marks (out of 100)",
                min_value=0.0,
                max_value=100.0,
                value=75.0
            )

        with col2:
            attended_classes = st.number_input(
                "Attended Classes",
                min_value=0,
                max_value=int(total_classes),
                value=min(85, int(total_classes))
            )

        submitted = st.form_submit_button(
            "Save Student",
            use_container_width=True
        )

        if submitted:

            if not name.strip() or not roll.strip():
                st.error("Enter student name and roll number.")

            elif attended_classes > total_classes:
                st.error("Attended classes cannot exceed total classes.")

            else:
                payload = {
                    "name": name.strip(),
                    "roll_number": roll.strip(),
                    "total_classes": int(total_classes),
                    "attended_classes": int(attended_classes),
                    "marks": float(marks)
                }

                try:
                    response = requests.post(
                        f"{API}/StudentAnalytics",
                        json=payload,
                        timeout=20
                    )

                    if response.status_code == 200:
                        st.success("Student saved successfully in Azure!")
                        st.json(response.json())
                        st.cache_data.clear()
                    else:
                        st.error(response.text)

                except requests.RequestException as error:
                    st.error(f"API error: {error}")

# STUDENT RECORDS
with records_tab:

    st.subheader("All Student Records")

    if not df.empty:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Student Records CSV",
            data=df.to_csv(index=False),
            file_name="student_records.csv",
            mime="text/csv"
        )
    else:
        st.info("No student records found.")

st.divider()
st.caption("Powered by Python, Streamlit and Microsoft Azure")
