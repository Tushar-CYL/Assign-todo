from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a secure secret key

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "tkantipatra357@gmail.com"  # Replace with your Gmail
APP_PASSWORD = "qbaqbnspeocopvxx"  # Replace with your Gmail App Password

db = SQLAlchemy(app)

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    members = db.relationship('Member', backref='organization', lazy=True)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    tasks = db.relationship('Task', backref='member', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=True)

def send_email(receiver_email, subject, message_body):
    """
    Sends an email using Gmail SMTP
    """
    try:
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = subject

        # Add body to email
        msg.attach(MIMEText(message_body, 'plain'))

        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        
        # Send email
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, receiver_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def send_task_notification(task, member):
    """Send email notification for new task assignment"""
    subject = f'New Task Assignment: {task.name}'
    message = f"""
Hello {member.name},

You have been assigned a new task in the Todo App:

Task Details:
-------------
Name: {task.name}
Due Date: {task.due_date.strftime('%B %d, %Y')}

Please complete this task by the due date.

Best regards,
Todo App Team
    """
    
    return send_email(member.email, subject, message)

def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database initialized successfully!")

if not os.path.exists('todo.db'):
    init_db()
else:
    try:
        with app.app_context():
            Member.query.first()
    except Exception as e:
        print("Reinitializing database due to schema change...")
        init_db()

@app.route('/')
def index():
    organizations = Organization.query.all()
    tasks = Task.query.order_by(Task.due_date).all()
    today = datetime.now().date()
    return render_template('index.html', organizations=organizations, tasks=tasks, today=today)

@app.route('/add_organization', methods=['POST'])
def add_organization():
    org_name = request.form.get('org_name')
    if org_name:
        new_org = Organization(name=org_name)
        db.session.add(new_org)
        db.session.commit()
        flash('Organization added successfully!', 'success')
    else:
        flash('Organization name is required.', 'error')
    return redirect(url_for('index'))

@app.route('/add_member/<int:org_id>', methods=['POST'])
def add_member(org_id):
    organization = Organization.query.get(org_id)
    if organization:
        member_name = request.form.get('member_name')
        member_email = request.form.get('member_email')
        if member_name and member_email:
            new_member = Member(name=member_name, email=member_email, org_id=org_id)
            db.session.add(new_member)
            db.session.commit()
            flash('Member added successfully!', 'success')
        else:
            flash('Member name and email are required.', 'error')
    else:
        flash('Organization not found.', 'error')
    return redirect(url_for('index'))

@app.route('/add_task/<int:member_id>', methods=['POST'])
def add_task(member_id):
    member = Member.query.get(member_id)
    if member:
        task_name = request.form.get('task_name')
        due_date_str = request.form.get('due_date')
        if task_name and due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                new_task = Task(name=task_name, due_date=due_date, member_id=member_id)
                db.session.add(new_task)
                db.session.commit()
                
                # Send email notification
                if send_task_notification(new_task, member):
                    flash('Task added successfully and notification sent!', 'success')
                else:
                    flash('Task added but failed to send notification.', 'warning')
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', 'error')
        else:
            flash('Task name and due date are required.', 'error')
    else:
        flash('Member not found.', 'error')
    return redirect(url_for('index'))

@app.route('/reminders')
def reminders():
    today = datetime.now().date()
    pending_tasks = Task.query.filter(Task.due_date <= today, Task.completed == False).all()
    return render_template('reminders.html', tasks=pending_tasks)

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    task = Task.query.get(task_id)
    if task:
        task.completed = True
        db.session.commit()
        flash('Task marked as completed!', 'success')
    else:
        flash('Task not found.', 'error')
    return redirect(url_for('index'))

@app.route('/test_email')
def test_email():
    """Route to test email functionality"""
    test_subject = "Test Email from Todo App"
    test_message = "This is a test email from your Flask Todo application."
    if send_email(SENDER_EMAIL, test_subject, test_message):
        return 'Test email sent successfully!'
    return 'Failed to send test email. Check console for details.'

if __name__ == '__main__':
    app.run(debug=True)