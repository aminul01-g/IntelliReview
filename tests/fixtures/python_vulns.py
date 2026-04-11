# tests/fixtures/python_vulns.py
# This file contains deliberate intentional vulnerabilities to test the AST/Security scanners.

import sqlite3

def login_user(username, secret_pass):
    # Intentional CWE-89 SQL Injection
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + secret_pass + "'"
    cursor.execute(query)
    return cursor.fetchall()

def load_config():
    # Intentional CWE-798 Hardcoded Secrets
    aws_api_key = "sk-aB3dE5fG7hI9jK1lM2nO4pQ6rS8tU0vW2xY4zA6"
    db_password = "super_secret_production_password"
    
    return aws_api_key, db_password

def calculate_complex_tax(user_data):
    # Intentional High Cyclomatic Complexity
    tax = 0
    if user_data.get('type') == 'corporate':
        if user_data.get('revenue') > 1000000:
            if user_data.get('location') == 'NY':
                tax += 0.08
            elif user_data.get('location') == 'CA':
                tax += 0.09
            else:
                tax += 0.05
        else:
            tax += 0.04
    elif user_data.get('type') == 'freelance':
        if user_data.get('revenue') > 100000:
            tax += 0.02
            if user_data.get('deductions'):
                tax -= 0.01
    return tax

