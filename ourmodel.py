import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

np.random.seed(42)
num_samples = 1000
data = pd.DataFrame({
    'income': np.random.randint(20000, 90000, num_samples),
    'credit_score': np.random.randint(300, 850, num_samples),
    'loan_amount': np.random.randint(5000, 80000, num_samples),
    'employment_status': np.random.choice([0, 1], num_samples),
})

data['approved'] = np.where(
    (data['income'] > data['loan_amount'] * 1.2) & 
    (data['credit_score'] > 500) & 
    (data['employment_status'] == 1),
    1, 0
)

X = data[['income', 'credit_score', 'loan_amount', 'employment_status']]
y = data['approved']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight="balanced")
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Model Accuracy: {accuracy:.2%}")

def loan_decision(applicant):
    applicant_df = pd.DataFrame([applicant])
    prediction = model.predict(applicant_df)[0]
    
    if prediction == 1:
        return "✅ APPROVED"
    
    reasons = []
    suggestions = []
    
    if applicant['employment_status'] == 0:
        reasons.append("unemployed")
        suggestions.append("Only employed applicants qualify")
    
    if applicant['credit_score'] <= 500:
        reasons.append(f"credit score ({applicant['credit_score']}) ≤ 500")
        suggestions.append(f"Increase score to at least 501 (current: {applicant['credit_score']})")
    
    required_income = applicant['loan_amount'] * 1.2
    if applicant['income'] <= required_income:
        reasons.append(f"income (₹{applicant['income']}) too low for ₹{applicant['loan_amount']} loan")
        max_eligible = int(applicant['income'] / 1.2)
        suggestions.append(f"Apply for ₹{max_eligible} or less instead")
    
    rejection_msg = "❌ REJECTED: " + ", ".join(reasons).capitalize()
    suggestion_msg = "💡 Suggestions: " + "; ".join(suggestions)
    
    return f"{rejection_msg}\n{suggestion_msg}"

test_applications = [
    {'income': 50000, 'credit_score': 650, 'loan_amount': 20000, 'employment_status': 1},
    {'income': 30000, 'credit_score': 550, 'loan_amount': 35000, 'employment_status': 1},
    {'income': 60000, 'credit_score': 450, 'loan_amount': 25000, 'employment_status': 1},
    {'income': 70000, 'credit_score': 700, 'loan_amount': 50000, 'employment_status': 0},
    {'income': 80000, 'credit_score': 600, 'loan_amount': 70000, 'employment_status': 1},
]

print("LOAN DECISION ENGINE\n" + "="*40)
for app in test_applications:
    decision = loan_decision(app)
    print(f"\nApplication: ₹{app['loan_amount']} loan | ₹{app['income']} income | {app['credit_score']} credit")
    print(decision)
    print("-"*60)   

__all__ = ['loan_decision', 'model']
