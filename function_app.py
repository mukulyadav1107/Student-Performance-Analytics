
import azure.functions as func
import logging
import json
import os
import math

from azure.data.tables import TableServiceClient

app = func.FunctionApp(
    http_auth_level=func.AuthLevel.ANONYMOUS
)

TABLE_NAME = "StudentRecords"


# CONNECT TO AZURE TABLE STORAGE
def get_table_client():

    connection_string = os.environ.get(
        "AzureWebJobsStorage"
    )

    if not connection_string:
        raise ValueError(
            "Azure Storage connection string is missing."
        )

    service = TableServiceClient.from_connection_string(
        connection_string
    )

    table = service.create_table_if_not_exists(
        table_name=TABLE_NAME
    )

    return table


# RETRIEVE ALL STUDENTS FROM AZURE
def fetch_students():

    table = get_table_client()

    entities = table.query_entities(
        query_filter="PartitionKey eq 'Students'"
    )

    students = []

    for entity in entities:

        students.append({
            "student_name": entity.get("Name"),
            "roll_number": entity.get("RowKey"),
            "total_classes": entity.get("TotalClasses"),
            "attended_classes": entity.get("AttendedClasses"),
            "attendance_percentage": entity.get(
                "AttendancePercentage"
            ),
            "marks": entity.get("Marks"),
            "performance": entity.get("Performance")
        })

    return students


# API 1: ADD OR UPDATE STUDENT
@app.route(
    route="StudentAnalytics",
    methods=["GET", "POST"]
)
def StudentAnalytics(req: func.HttpRequest) -> func.HttpResponse:

    try:

        if req.method == "GET":

            return func.HttpResponse(
                json.dumps({
                    "message": "Welcome to Student Analytics API",
                    "storage": "Azure Table Storage",
                    "endpoints": [
                        "/api/StudentAnalytics",
                        "/api/Students",
                        "/api/Analytics"
                    ]
                }),
                mimetype="application/json",
                status_code=200
            )

        data = req.get_json()

        if not isinstance(data, dict):
            raise ValueError("Invalid student data.")

        name = data.get("name")
        roll_number = data.get("roll_number")
        total_classes = data.get("total_classes")
        attended_classes = data.get("attended_classes")
        marks = data.get("marks")

        # Validate required fields
        if (
            not name
            or not str(name).strip()
            or roll_number is None
            or not str(roll_number).strip()
            or total_classes is None
            or attended_classes is None
            or marks is None
        ):
            raise ValueError(
                "Please provide all student details."
            )

        # Validate attendance
        if (
            isinstance(total_classes, bool)
            or not isinstance(total_classes, int)
            or isinstance(attended_classes, bool)
            or not isinstance(attended_classes, int)
            or total_classes <= 0
            or attended_classes < 0
            or attended_classes > total_classes
        ):
            raise ValueError("Invalid attendance values.")

        # Validate marks
        if (
            isinstance(marks, bool)
            or not isinstance(marks, (int, float))
            or not math.isfinite(marks)
            or marks < 0
            or marks > 100
        ):
            raise ValueError(
                "Marks must be between 0 and 100."
            )

        # Calculate attendance
        attendance = (
            attended_classes / total_classes
        ) * 100

        # Classify performance
        if marks >= 80:
            performance = "Excellent"
        elif marks >= 60:
            performance = "Good"
        elif marks >= 40:
            performance = "Average"
        else:
            performance = "Needs Improvement"

        clean_name = str(name).strip()
        clean_roll = str(roll_number).strip()

        result = {
            "student_name": clean_name,
            "roll_number": clean_roll,
            "total_classes": total_classes,
            "attended_classes": attended_classes,
            "attendance_percentage": round(
                attendance, 2
            ),
            "marks": marks,
            "performance": performance
        }

        # Save student in Azure
        table = get_table_client()

        entity = {
            "PartitionKey": "Students",
            "RowKey": clean_roll,
            "Name": clean_name,
            "TotalClasses": total_classes,
            "AttendedClasses": attended_classes,
            "AttendancePercentage": round(
                attendance, 2
            ),
            "Marks": marks,
            "Performance": performance
        }

        table.upsert_entity(entity=entity)

        result["storage_status"] = "Saved successfully"

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    except ValueError as error:

        return func.HttpResponse(
            json.dumps({"error": str(error)}),
            mimetype="application/json",
            status_code=400
        )

    except Exception:

        logging.exception(
            "Student processing failed."
        )

        return func.HttpResponse(
            json.dumps({
                "error": "Unable to process student record."
            }),
            mimetype="application/json",
            status_code=500
        )


# API 2: GET ALL STUDENTS
@app.route(
    route="Students",
    methods=["GET"]
)
def GetAllStudents(req: func.HttpRequest) -> func.HttpResponse:

    try:

        students = fetch_students()

        return func.HttpResponse(
            json.dumps({
                "total_students": len(students),
                "students": students
            }),
            mimetype="application/json",
            status_code=200
        )

    except Exception:

        logging.exception(
            "Unable to retrieve student records."
        )

        return func.HttpResponse(
            json.dumps({
                "error": "Unable to retrieve student records."
            }),
            mimetype="application/json",
            status_code=500
        )


# API 3: CLASS PERFORMANCE ANALYTICS
@app.route(
    route="Analytics",
    methods=["GET"]
)
def GetAnalytics(req: func.HttpRequest) -> func.HttpResponse:

    try:

        students = fetch_students()

        total = len(students)

        if total == 0:

            return func.HttpResponse(
                json.dumps({
                    "message": "No student records available.",
                    "total_students": 0
                }),
                mimetype="application/json",
                status_code=200
            )

        marks = [
            float(student["marks"])
            for student in students
        ]

        attendance = [
            float(student["attendance_percentage"])
            for student in students
        ]

        passed = sum(
            1 for mark in marks if mark >= 40
        )

        needs_support = [
            student for student in students
            if (
                float(student["marks"]) < 40
                or float(student["attendance_percentage"]) < 75
            )
        ]

        analytics = {
            "total_students": total,
            "average_marks": round(
                sum(marks) / total, 2
            ),
            "average_attendance": round(
                sum(attendance) / total, 2
            ),
            "passed_students": passed,
            "failed_students": total - passed,
            "pass_percentage": round(
                (passed / total) * 100, 2
            ),
            "students_needing_support": needs_support
        }

        return func.HttpResponse(
            json.dumps(analytics),
            mimetype="application/json",
            status_code=200
        )

    except Exception:

        logging.exception(
            "Analytics calculation failed."
        )

        return func.HttpResponse(
            json.dumps({
                "error": "Unable to calculate analytics."
            }),
            mimetype="application/json",
            status_code=500
        )
