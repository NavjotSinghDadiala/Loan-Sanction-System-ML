from dotenv import load_dotenv
import os

# Load environment variables at the start
load_dotenv()

# Verify Twilio credentials are loaded
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    print("Warning: Twilio credentials not found in environment variables")

from models import *
from flask import Flask, render_template, request, flash, session, redirect, url_for
from flask import send_file
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import pickle
import io
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive Agg
import matplotlib.pyplot as plt
import base64
from twilio_utils import make_phone_call
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif'}  # Define allowed file extensions

# Create the uploads folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


#----------------------------------------------MODEL----------------------------------------------------
model = pickle.load(open('loan_model.pkl', 'rb'))

def predict_loan(income, credit_score, loan_amount, employment_status):
    return "Approved" if model.predict([[income, credit_score, loan_amount, employment_status]])[0] == 1 else "Rejected"


#+----------------------------------------------------------------APP----------------------------------------
app = Flask(__name__, template_folder='scripts')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SECRET_KEY'] = 'thisissecretkey'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Directory to save uploaded files
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}
db.init_app(app)

with app.app_context():
    db.create_all()

    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='Admin Role')
        db.session.add(admin_role)
    
    customer_role = Role.query.filter_by(name='customer').first()
    if not customer_role:
        customer_role = Role(name='customer', description='Customer Role')
        db.session.add(customer_role)

    db.session.commit()

    admin = User.query.filter_by(email='admin@gmail.com').first()
    if not admin:
        admin = User(
            name='Admin User',
            email='admin@gmail.com',
            password='admin',
            role_id=admin_role.id 
        )
        db.session.add(admin)
        db.session.commit()

#--------------------------------------------------------ROUTER--------------------------------------------------------

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('login.html')

    email = request.form.get('email', None)
    password = request.form.get('password', None)

    if not email or not password:
        flash('Credentials invalid', 'danger')
        return render_template('login.html')

    user = User.query.filter_by(email=email).first()

    if not user:
        flash('User not found', 'danger')
        return render_template('login.html')

    if user.password != password:
        flash('Incorrect password', 'danger')
        return render_template('login.html')

    session['user_email'] = user.email
    session['role'] = user.role.name if user.role else "customer" 
    flash("Login successful!", "success")
    if session['role'] == 'admin':
        return redirect(url_for('admin_dashboard')) 
    else:
        return redirect(url_for('user_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template('register.html')  

    name = request.form.get('name', None)
    email = request.form.get('email', None)
    password = request.form.get('password', None)
    role_name = request.form.get('role', 'customer')

    if not name or not email or not password:
        flash("Please enter all the details correctly", "danger")
        return render_template('register.html')

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash("User already exists", "warning")
        return redirect(url_for('login'))

    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash("Invalid role selected!", "danger")
        return render_template('register.html')

    # Create new user with rejection_count initialized to 0
    new_user = User(
        name=name, 
        email=email, 
        password=password, 
        role_id=role.id,
        rejection_count=0  # Initialize rejection count to 0
    )
    db.session.add(new_user)

    # **Update or Auto-Fill `VerifiedUser` Table**
    verified_user = VerifiedUser.query.filter_by(email=email).first()

    if verified_user:
        # If email exists in both User and VerifiedUser tables, set bank_count to 2
        verified_user.bank_count = 2
        print(f"📊 Setting bank_count to 2 for user: {email}")
    else:
        recent_loan = LoanApplication.query.filter_by(user_id=new_user.id).order_by(LoanApplication.created_at.desc()).first()

        correct_income = recent_loan.income if recent_loan else 0.0
        correct_credit_score = recent_loan.credit_score if recent_loan else 600
        employment_status = recent_loan.employment_status if recent_loan else "Unemployed"
        aadhaar_number = recent_loan.aadhaar_number if recent_loan else 123  # Default 12-digit number

        new_verified_user = VerifiedUser(
            email=email,
            correct_income=correct_income,
            correct_credit_score=correct_credit_score,
            employment_status=employment_status,
            aadhaar_number=aadhaar_number,
            bank_count=1,
            status=True  
        )
        db.session.add(new_verified_user)

    db.session.commit()

    flash("User created successfully! Please log in.", "success")
    return redirect(url_for('login'))



@app.route('/system_settings')
def system_settings():
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('admin_dashboard'))
    

    return render_template('system_settings.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('user_dashboard')) 
    try:
        total_users = max(0, User.query.count())
        verified_users = max(0, VerifiedUser.query.count())
        total_loans = max(0, LoanApplication.query.count())
        approved_loans = max(0, LoanApplication.query.filter_by(prediction='Approved').count())
        rejected_loans = max(0, LoanApplication.query.filter_by(prediction='Rejected').count())

        # Create pie charts
        import matplotlib
        matplotlib.use('Agg')  
        import matplotlib.pyplot as plt
        import io
        import base64

        plt.style.use('default')
        
        # Create a figure with two subplots
        plt.figure(figsize=(15, 6))

        # Total Users vs Verified Users Pie Chart
        plt.subplot(1, 2, 1)
        users_data = [total_users, verified_users]  # Show total users vs verified users
        if sum(users_data) > 0:  # Only create pie chart if there's data
            plt.pie(users_data, 
                    labels=['Total Users', 'Verified Users'],
                    colors=['#dc3545', '#28a745'],
                    autopct='%1.1f%%',
                    shadow=True,
                    explode=(0.05, 0),
                    startangle=90)
            plt.title('Users Distribution', pad=20)
        else:
            plt.text(0.5, 0.5, 'No User Data', 
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=plt.gca().transAxes)
            plt.title('Users Distribution', pad=20)

        # Loan Status Pie Chart
        plt.subplot(1, 2, 2)
        loans_data = [approved_loans, rejected_loans]
        if sum(loans_data) > 0:  # Only create pie chart if there's data
            plt.pie(loans_data,
                    labels=['Approved', 'Rejected'],
                    colors=['#28a745', '#dc3545'],
                    autopct='%1.1f%%',
                    shadow=True,
                    explode=(0.05, 0),
                    startangle=90)
            plt.title('Loan Application Status', pad=20)
        else:
            plt.text(0.5, 0.5, 'No Loan Data', 
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=plt.gca().transAxes)
            plt.title('Loan Application Status', pad=20)

        # Add a title to the entire figure
        plt.suptitle('System Statistics Overview', fontsize=14, y=1.05)

        # Save the plot to a base64 string
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', dpi=300)
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()

        # Additional statistics
        stats = {
            'total_users': total_users,
            'verified_users': verified_users,
            'total_loans': total_loans,
            'approved_loans': approved_loans,
            'rejected_loans': rejected_loans,
            'approval_rate': round((approved_loans / total_loans * 100) if total_loans > 0 else 0, 2),
            'verification_rate': round((verified_users / total_users * 100) if total_users > 0 else 0, 2)
        }

        return render_template('admin_dashboard.html', plot_url=plot_url, stats=stats)
    
    except Exception as e:
        print(f"Error in admin dashboard: {str(e)}")
        flash("Error loading dashboard statistics", "danger")
        return render_template('admin_dashboard.html', plot_url=None, stats={
            'total_users': 0,
            'verified_users': 0,
            'total_loans': 0,
            'approved_loans': 0,
            'rejected_loans': 0,
            'approval_rate': 0,
            'verification_rate': 0
        })

#----------------------------------------------------------------- DASHBOARD---------------------------------------------------------------


@app.route('/user_dashboard', methods=['GET'])
def user_dashboard():
    if 'user_email' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=session['user_email']).first()
    loan_application = LoanApplication.query.filter_by(user_id=user.id).order_by(LoanApplication.created_at.desc()).first()
    loan_applications = LoanApplication.query.filter_by(user_id=user.id).order_by(LoanApplication.created_at.desc()).all()

    print(f"✅ User Dashboard - User: {user.email}, User ID: {user.id}")  # Debug

    rejection_reason = None  

    if loan_application:
        print(f"📌 Loan Found - Amount: {loan_application.loan_amount}, Status: {loan_application.prediction}")

        if loan_application.prediction == "Rejected":
            if loan_application.credit_score <= 500:
                rejection_reason = f"❌ REJECTED: Credit score ({loan_application.credit_score}) ≤ 500"
            elif loan_application.employment_status not in ["Employed", "Self-Employed"]:
                rejection_reason = "❌ REJECTED: Unemployed applicants do not qualify"
            elif loan_application.loan_amount > (loan_application.income * 0.8333): 
                suggested_loan_amount = round(loan_application.income * 0.8333, 2)
                rejection_reason = (
                    f"❌ REJECTED: Income (₹{loan_application.income}) too low for ₹{loan_application.loan_amount} loan. "
                    f"💡 Suggestion: Apply for ₹{suggested_loan_amount} or less"
                )

            print(f"🚨 Loan Rejection Reason: {rejection_reason}")

        elif loan_application.prediction == "Approved":
            print("🎉 Loan Approved!")

        else:
            rejection_reason = "⏳ Loan application is under review."
            print("⏳ Loan Pending Review")

    else:
        print("⚠️ No Loan Application Found")

    return render_template(
        'user_dashboard.html',
        user=user,
        loan_application=loan_application,
        loan_applications=loan_applications,
        rejection_reason=rejection_reason
    )





@app.route('/manage_users')
def manage_users():
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!")
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/manage_verified_users', methods=['GET', 'POST'])
def manage_verified_users():
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('register'))

    if request.method == 'POST':
        email = request.form.get('email')
        income = float(request.form.get('income'))
        credit_score = int(request.form.get('credit_score'))
        employment_status = request.form.get('employment_status')

        aadhaar_number = request.form.get('aadhaar_number', '0')  # Default to '0' if not provided
        aadhaar_number = int(aadhaar_number) if aadhaar_number.isdigit() else 0

        aadhaar_file = request.files.get('aadhaar_file')
        pan_file = request.files.get('pan_file')
        income_certificate_file = request.files.get('income_certificate_file')

        aadhaar_binary = aadhaar_file.read() if aadhaar_file else None
        pan_binary = pan_file.read() if pan_file else None
        income_certificate_binary = income_certificate_file.read() if income_certificate_file else None

        verified_user = VerifiedUser.query.filter_by(email=email).first()

        if verified_user:
            verified_user.correct_income = income
            verified_user.correct_credit_score = credit_score
            verified_user.employment_status = employment_status
            verified_user.aadhaar_number = aadhaar_number
            
            if aadhaar_binary:
                verified_user.aadhaar_file = aadhaar_binary
            if pan_binary:
                verified_user.pan_file = pan_binary
            if income_certificate_binary:
                verified_user.income_certificate_file = income_certificate_binary
        else:
            new_verified = VerifiedUser(
                email=email,
                correct_income=income,
                correct_credit_score=credit_score,
                employment_status=employment_status,
                aadhaar_file=aadhaar_binary,
                aadhaar_number=aadhaar_number,
                pan_file=pan_binary,
                income_certificate_file=income_certificate_binary
            )
            db.session.add(new_verified)

        db.session.commit()
        flash("User verification details updated successfully!", "success")
        return redirect(url_for('manage_verified_users'))

    verified_users = VerifiedUser.query.all()
    return render_template('manage_verified_users.html', verified_users=verified_users)


@app.route('/delete_user/<int:id>')
def delete_user(id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('home'))

    user = User.query.get_or_404(id) 

    db.session.delete(user)
    db.session.commit()

    flash('User deleted successfully', 'success')
    return redirect(url_for('manage_users'))

#----------------------------------------------------------- CAN BE IMPLEMENTED ------------------------------------------------
@app.route('/deactivate_user/<int:id>')
def deactivate_user(id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('home'))

    user = User.query.get_or_404(id)

    if user.flag: 
        flash('User is already deactivated!', 'info')
        return redirect(url_for('manage_users'))

    user.flag = True
    db.session.commit()

    flash('User deactivated successfully', 'warning')
    return redirect(url_for('manage_users'))

@app.route('/activate_user/<int:id>')
def activate_user(id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('home'))

    user = User.query.get_or_404(id)

    if not user.flag:
        flash('User is already active', 'info')
        return redirect(url_for('manage_users'))

    user.flag = False
    db.session.commit()

    flash('User activated successfully', 'success')
    return redirect(url_for('manage_users'))

#----------------------------------------------------------------------------------------------------------------------------------


import uuid 

@app.route('/apply_loan', methods=['GET', 'POST'])
def apply_loan():
    if 'user_email' not in session:
        flash('Please log in to apply for a loan.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=session['user_email']).first()
    loan_application = LoanApplication.query.filter_by(user_id=user.id).first()
    verified_user = VerifiedUser.query.filter_by(email=user.email).first()
    customer = Customer.query.filter_by(user_id=user.id).first()

    print("\n=== Loan Application Process Started ===")
    print(f"User Email: {session['user_email']}")
    
    if user:
        print(f"User Found: {user.email}, User ID: {user.id}")
    else:
        print("User Not Found in the System!")

    if request.method == 'POST':
        print("\n--- Processing Loan Application Form ---")
        
        try:
            income = float(request.form.get('income'))
            credit_score = int(request.form.get('credit_score'))
            loan_amount = float(request.form.get('loan_amount'))
            employment_status = request.form.get('employment_status')
            phone_number = request.form.get('phone_number')  # Get phone number from form

            # Update user's phone number if provided
            if phone_number and not user.phone_number:
                user.phone_number = phone_number

            aadhaar_file = request.files.get('aadhaar_file').read() if request.files.get('aadhaar_file') else None
            pan_file = request.files.get('pan_file').read() if request.files.get('pan_file') else None
            income_certificate_file = request.files.get('income_certificate_file').read() if request.files.get('income_certificate_file') else None

            if not (aadhaar_file and pan_file and income_certificate_file):
                flash("All required files must be uploaded!", "danger")
                print("❌ Missing file uploads! Loan application aborted.")
                return redirect(url_for('apply_loan'))

            aadhaar_number = request.form.get('aadhaar_number')
            aadhaar_number = int(aadhaar_number)  # Validate Aadhaar format
            employment_status_num = 1 if employment_status in ["Employed", "Self-Employed"] else 0

            print(f"User Income: {income}, Credit Score: {credit_score}, Loan Amount: {loan_amount}")
            print(f"Employment Status: {employment_status}, Employment Num: {employment_status_num}")
            print(f"Aadhaar Number: {aadhaar_number}")

            # Check if documents match
            if (aadhaar_file != verified_user.aadhaar_file or 
                pan_file != verified_user.pan_file or 
                income_certificate_file != verified_user.income_certificate_file):
                print("❌ Uploaded documents do not match verified documents!")
                flash("Uploaded documents do not match our verified records!", "danger")
                
                # Increment rejection count for document mismatch
                user.rejection_count += 1
                print(f"📊 Rejection count incremented to: {user.rejection_count} (Document mismatch)")
                db.session.commit()
                return redirect(url_for('apply_loan'))

            # Check if user's status is False (rejected in another bank)
            if not verified_user.status:
                print("❌ Loan was rejected in another bank. Auto-rejecting here.")  

                new_loan = LoanApplication(
                    income=income,
                    credit_score=credit_score,
                    loan_amount=loan_amount,
                    employment_status=employment_status,
                    user_id=user.id if user else None,
                    prediction='Rejected',
                    rejection_reason="Previous rejection in another bank",
                    rejection_suggestion="Please improve your credit score or try with a different bank",
                    suggestion="Loan auto-rejected due to previous rejection in another bank",
                    aadhaar_file=aadhaar_file,
                    pan_file=pan_file,
                    income_certificate_file=income_certificate_file,
                    aadhaar_number=aadhaar_number
                )

                db.session.add(new_loan)
                
                # Increment rejection count for status=False
                user.rejection_count += 1
                print(f"📊 Rejection count incremented to: {user.rejection_count} (Status=False)")
                
                # Always show rejection count message
                flash(f"Your loan application was rejected. This is rejection #{user.rejection_count}.", "warning")
                
                # Trigger phone call for any count >= 3
                if user.rejection_count >= 3:
                    flash('You have reached 3 or more rejections. A representative will call you shortly.', 'warning')
                    if make_phone_call():
                        flash('A call has been initiated to discuss your loan application.', 'info')
                    else:
                        flash('Could not initiate call. Please contact customer support.', 'error')
                
                db.session.commit()
                return redirect(url_for('user_dashboard'))

            # === RUN LOAN PREDICTION ===
            prediction = predict_loan(income, credit_score, loan_amount, employment_status_num)
            print(f"🔮 Loan Prediction: {prediction}")

            flag = (
                verified_user
                and float(verified_user.correct_income) == float(income)
                and int(verified_user.correct_credit_score) == int(credit_score)
                and str(verified_user.employment_status).strip().lower() == str(employment_status).strip().lower()
                and verified_user.aadhaar_number == aadhaar_number
            ) if verified_user else False

            print(f"🔍 User Verification Status in Our Bank: {flag}")

            rejection_suggestion = None
            suggested_loan_amount = loan_amount

            if prediction == "Rejected":
                print("🚨 Loan Rejected! Checking for possible improvement suggestions...")

                if credit_score <= 500:
                    rejection_suggestion = f"Credit score ({credit_score}) is too low."
                elif employment_status_num == 0:
                    rejection_suggestion = "Unemployed applicants are not eligible."
                elif loan_amount > (income * 0.8333):  
                    suggested_loan_amount = round(income * 0.8333, 2)
                    rejection_suggestion = f"💡 Suggestion: Apply for ₹{suggested_loan_amount} or less."
                else:
                    rejection_suggestion = "Loan denied based on internal checks."

                print(f"❌ Rejection Reason: {rejection_suggestion}")

            # Check verified_user status again before final decision
            final_decision = "Rejected" if not verified_user.status else ("Approved" if flag and prediction == "Approved" else "Rejected")
            print(f"✅ Final Decision: {final_decision}")

            if customer:
                customer.payment_mode = rejection_suggestion or "No Suggestion"
            else:
                customer = Customer(
                    user_id=user.id,
                    address="Not Provided",
                    payment_mode=rejection_suggestion or "No Suggestion",
                    phone_number=phone_number or "Not Provided"
                )
                db.session.add(customer)

            new_application = LoanApplication(
                income=income,
                credit_score=credit_score,
                loan_amount=loan_amount,
                employment_status=employment_status,
                user_id=user.id,
                prediction=final_decision,
                flag=flag,
                rejection_reason=rejection_suggestion if prediction == "Rejected" else None,
                rejection_suggestion=rejection_suggestion if prediction == "Rejected" else None,
                suggestion=rejection_suggestion if prediction == "Rejected" else "Loan application processed successfully",
                aadhaar_file=aadhaar_file,
                pan_file=pan_file,
                income_certificate_file=income_certificate_file,
                aadhaar_number=aadhaar_number
            )
            db.session.add(new_application)

            # Increment rejection count for any type of rejection
            if final_decision == "Rejected":
                user.rejection_count += 1
                print(f"📊 Rejection count incremented to: {user.rejection_count}")
                
                # Always show rejection count message
                flash(f"Your loan application was rejected. This is rejection #{user.rejection_count}.", "warning")
                
                # Trigger phone call for any count >= 3
                if user.rejection_count >= 3:
                    flash('You have reached 3 or more rejections. A representative will call you shortly.', 'warning')
                    if make_phone_call():
                        flash('A call has been initiated to discuss your loan application.', 'info')
                    else:
                        flash('Could not initiate call. Please contact customer support.', 'error')

                db.session.commit()

            db.session.commit()

            print("\n✅ Loan application submitted successfully!")
            flash(f"Loan application submitted! Status: {final_decision}", "success")
            return redirect(url_for('user_dashboard'))

        except ValueError:
            # Increment rejection count for invalid credentials
            user.rejection_count += 1
            print(f"📊 Rejection count incremented to: {user.rejection_count} (Invalid credentials)")
            flash('Invalid input format.', 'danger')
            db.session.commit()
            return redirect(url_for('apply_loan'))

    return render_template('apply_loan.html')

@app.route('/update_loan_status/<int:id>', methods=['POST'])
def update_loan_status(id):
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('manage_verified_users'))

    user = VerifiedUser.query.get(id)
    
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for('manage_verified_users'))

    new_status = request.form.get('loan_status')
    print(f"\n=== Updating Loan Status ===")
    print(f"User ID: {id}")
    print(f"Current Status: {user.status}")
    print(f"New Status: {new_status}")

    if new_status not in ["Pending", "Approved", "Rejected"]:
        flash("Invalid status!", "danger")
        return redirect(url_for('manage_verified_users'))

    # Update both status fields
    user.status = True if new_status == "Approved" else False
    user.loan_status_in_other_bank = new_status

    try:
        db.session.commit()
        print(f"✅ Status updated successfully!")
        print(f"New Status: {user.status}")
        print(f"Loan Status in Other Bank: {user.loan_status_in_other_bank}")
        flash("Loan status updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating status: {str(e)}")
        flash("Error updating loan status!", "danger")

    return redirect(url_for('manage_verified_users'))







#----------------------------------------------------------------ROUTER NOT IN USE ----------------------------------------------------------------
@app.route('/download/<email>/<file_type>')
def download_file(email, file_type):
    user = VerifiedUser.query.filter_by(email=email).first()
    if not user:
        return "User not found", 404

    file_data = None
    filename = None

    if file_type == 'aadhaar' and user.aadhaar_file:
        file_data = user.aadhaar_file
        filename = "aadhaar.pdf"  # Adjust file extension as needed
    elif file_type == 'pan' and user.pan_file:
        file_data = user.pan_file
        filename = "pan.pdf"
    elif file_type == 'income_certificate' and user.income_certificate_file:
        file_data = user.income_certificate_file
        filename = "income_certificate.pdf"

    if file_data:
        return send_file(io.BytesIO(file_data), as_attachment=True, download_name=filename)
    return "File not found", 404





 
#----------------------------------------------------------------------NO USE ----------------------------------------------------



@app.route('/approve_loan/<int:id>')
def approve_loan(id):
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('home'))

    loan = LoanApplication.query.get_or_404(id)
    loan.prediction = "Approved"
    db.session.commit()

    flash("Loan approved successfully!", "success")
    return redirect(url_for('manage_loans'))

@app.route('/reject_loan/<int:id>')
def reject_loan(id):
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('home'))

    loan = LoanApplication.query.get_or_404(id)
    loan.prediction = "Rejected"
    db.session.commit()

    flash("Loan rejected successfully!", "danger")
    return redirect(url_for('manage_loans'))


    return render_template('apply_loan.html')

@app.route('/manage_loans')
def manage_loans():
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('login'))

    users = User.query.all()
    return render_template('manage_loans.html', users=users)
@app.route('/delete_verified_user/<int:id>')
def delete_verified_user(id):
    if 'role' not in session or session['role'] != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('home'))

    verified_user = VerifiedUser.query.get_or_404(id)
    db.session.delete(verified_user)
    db.session.commit()

    flash("Verified user deleted successfully!", "success")
    return redirect(url_for('manage_verified_users'))


#------------------------------------------------------------------------------------------------------------------------------




if __name__ == '__main__':
    app.run(debug=True)
