import io
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import openpyxl
from sqlalchemy.exc import IntegrityError, DataError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Define the ExamHall model
class ExamHall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    program_name = db.Column(db.String(100), nullable=False)
    register_number = db.Column(db.String(20), nullable=False)

class SeatLayout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_hall_id = db.Column(db.Integer, db.ForeignKey('ExamHall.id'), nullable=False)
    layout = db.Column(db.Text, nullable=False)
    

# Create database tables
with app.app_context():
    db.create_all()

# Define routes

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        hall_name = request.form['hall_name']
        existing_hall = ExamHall.query.filter_by(name=hall_name).first()
        if not existing_hall:
            new_hall = ExamHall(name=hall_name)
            db.session.add(new_hall)
            db.session.commit()
        return redirect(url_for('index'))
    halls = ExamHall.query.all()
    return render_template('index.html', halls=halls)

@app.route('/back', methods=['GET'])
def back():
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('aboutus.html')

@app.route('/plan_seating/<int:class_room_number>', methods=['GET', 'POST'])
def plan_seating(class_room_number):
    class_room = ExamHall.query.get_or_404(class_room_number)
    seat_layout = SeatLayout.query.filter_by(exam_hall_id=class_room_number).first()
    program_name = Student.query.with_entities(Student.program_name).distinct().all()
    

    program_name_list = []
    
    for i in range(len(program_name)):
        program_name_list.append(program_name[i][0])

    if request.method == 'POST':
        rows = int(request.form['rows'])
        columns = int(request.form['columns'])
        
        layout = generate_layout(rows, columns)

        if seat_layout:
            seat_layout.layout = layout
        else:
            seat_layout = SeatLayout(exam_hall_id=class_room_number, layout=layout)
            db.session.add(seat_layout)
        db.session.commit()
        return render_template('roomdesign.html', class_room=class_room, layout=layout, rows=rows, columns=columns, program_name=program_name_list)

    if seat_layout:
        layout = seat_layout.layout
        rows, columns = get_layout_dimensions(layout)
        return render_template('roomdesign.html', class_room=class_room, layout=layout, rows=rows, columns=columns, program_name=program_name_list)
    else:
        return render_template('roomdesign.html', class_room=class_room, rows=None, columns=None, program_name=program_name_list)

def generate_layout(rows, columns):
    layout = ""
    for _ in range(rows):
        row = ""
        for _ in range(columns):
            row += "0"
        layout += row + "\n"
    return layout

def get_layout_dimensions(layout):
    rows = len(layout.splitlines())
    columns = len(layout.splitlines()[0])
    return rows, columns
@app.route('/assign_students/<int:class_room_id>', methods=['POST'])
def assign_students(class_room_id):
    selected_programs = request.form.getlist('programs[]')
    # Write your logic here to assign students to seats based on selected programs and generate the layout
    layout = generate_layout(class_room_id, selected_programs)  # Implement this function
    return jsonify({'layout': layout})

@app.route('/delete_exam_hall/<int:exam_hall_id>', methods=['POST'])
def delete_exam_hall(exam_hall_id):
    try:
        # Query the exam hall by its ID
        exam_hall = ExamHall.query.get_or_404(exam_hall_id)

        # Delete the exam hall from the database
        db.session.delete(exam_hall)
        db.session.commit()

        # Redirect to the index page or any other appropriate page
        return redirect(url_for('index'))
    except Exception as e:
        # Handle any exceptions and return an error response
        return jsonify(success=False, error=str(e))
@app.route('/add_students', methods=['GET', 'POST'])
def add_students():
    if request.method == 'POST':
        program_name = request.form['program_name']
        register_numbers = request.files['register_numbers']
        
        # Open the Excel file
        excel_file = io.BytesIO(register_numbers.read())
        workbook = openpyxl.load_workbook(excel_file)
        sheet = workbook.active
        
        students = []
        # Iterate over rows starting from the second row (skipping the header)
        for row in sheet.iter_rows(min_row=2, values_only=True):
            register_number = row[0]
            if register_number:
                students.append(Student(program_name=program_name, register_number=str(register_number)))
        # Add students to the database
        db.session.add_all(students)
        db.session.commit()

    programs = db.session.query(Student.program_name, db.func.count(Student.register_number).label('total_students')).group_by(Student.program_name).all()
    return render_template('students.html', programs=programs)



@app.route('/delete_students/<program_name>', methods=['POST'])
def delete_students(program_name):
    students_to_delete = Student.query.filter_by(program_name=program_name).all()
    for student in students_to_delete:
        db.session.delete(student)
    db.session.commit()
    return redirect(url_for('add_students'))

@app.route('/list_students')
def list_students():
    students = Student.query.all()
    return render_template('list_students.html', students=students)



if __name__ == '__main__':
    app.run(debug=True)
