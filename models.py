from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)  # Hashed password recommended
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False, default=2)
    flag = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    rejection_count = db.Column(db.Integer, default=0)  # Track number of loan rejections
    phone_number = db.Column(db.String(15), nullable=True)  # Store user's phone number

    role = db.relationship('Role', backref='users')

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

class LoanApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    income = db.Column(db.Float, nullable=False)
    credit_score = db.Column(db.Integer, nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    employment_status = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    prediction = db.Column(db.String(10), default='Pending')  # Approved, Rejected, Pending
    rejection_reason = db.Column(db.String(255), nullable=True)  # Stores rejection reason
    rejection_suggestion = db.Column(db.String(255), nullable=True)  # Suggestion to improve
    suggestion = db.Column(db.String(255), nullable=True)  # Changed from Float to String
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  
    
    flag = db.Column(db.Boolean, default=True)  
    aadhaar_number = db.Column(db.BigInteger, nullable=False)

    # Uploaded documents
    aadhaar_file = db.Column(db.LargeBinary, nullable=True)
    pan_file = db.Column(db.LargeBinary, nullable=True)
    income_certificate_file = db.Column(db.LargeBinary, nullable=True)

    user = db.relationship('User', backref='loan_applications')

    def __repr__(self):
        return f'<LoanApplication {self.id} - User {self.user_id}>'


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    payment_mode = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)


class VerifiedUser(db.Model):  # Acts as a centralized RBI-like database
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    
    correct_income = db.Column(db.Float, nullable=False)
    correct_credit_score = db.Column(db.Integer, nullable=False)
    employment_status = db.Column(db.String(50), nullable=False)
    
    bank_count = db.Column(db.Integer, default=1)  # ✅ Tracks how many banks the user is registered in
    status = db.Column(db.Boolean, default=True)  # ✅ Manually set by admin (True = Approved, False = Rejected)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    flag = db.Column(db.Boolean, default=True)

    # Uploaded documents (for cross-checking with user dashboard)
    aadhaar_file = db.Column(db.LargeBinary, nullable=True)
    pan_file = db.Column(db.LargeBinary, nullable=True)
    income_certificate_file = db.Column(db.LargeBinary, nullable=True)

    aadhaar_number = db.Column(db.BigInteger, nullable=False)

    def __repr__(self):
        return f'<VerifiedUser {self.email} | Banks: {self.bank_count} | Status: {"Approved" if self.status else "Rejected"}>'
