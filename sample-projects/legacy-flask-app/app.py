"""Legacy Flask application with various issues for testing Rejig."""
import os
import sqlite3
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Hardcoded secrets - security issue
SECRET_KEY = "super-secret-key-12345"
DATABASE_URL = "postgresql://admin:password123@localhost/mydb"
API_KEY = "sk_live_abcdefghijklmnop"

# Magic numbers
MAX_ITEMS = 100
CACHE_TIMEOUT = 3600
PAGE_SIZE = 25

def get_db():
    # type: () -> sqlite3.Connection
    """Get database connection."""
    conn = sqlite3.connect('app.db')
    return conn

def validate_user(user_id):
    # type: (int) -> bool
    if user_id > 0:
        return True
    return False

def get_user(user_id):
    # type: (int) -> dict
    db = get_db()
    cursor = db.cursor()
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    cursor.execute(query)
    row = cursor.fetchone()
    if row:
        return {"id": row[0], "name": row[1], "email": row[2]}
    return None

def get_users(limit, offset):
    # type: (int, int) -> list
    db = get_db()
    cursor = db.cursor()
    # Another SQL injection
    cursor.execute(f"SELECT * FROM users LIMIT {limit} OFFSET {offset}")
    return cursor.fetchall()

def create_user(name, email, password):
    # type: (str, str, str) -> dict
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        (name, email, password)
    )
    db.commit()
    return {"id": cursor.lastrowid, "name": name, "email": email}

def send_email(to, subject, body):
    # type: (str, str, str) -> bool
    # TODO: implement actual email sending
    print(f"Sending email to {to}: {subject}")
    return True

def process_data(items):
    # type: (list) -> list
    result = []
    for item in items:
        if item is not None:
            processed = item.strip().lower()
            if len(processed) > 0:
                result.append(processed)
    return result

def calculate_total(prices):
    # type: (list) -> float
    total = 0
    for price in prices:
        total = total + price
    return total

def format_currency(amount):
    # type: (float) -> str
    return "${:.2f}".format(amount)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users', methods=['GET'])
def list_users():
    limit = request.args.get('limit', 25)
    offset = request.args.get('offset', 0)
    users = get_users(limit, offset)
    return jsonify(users)

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_endpoint(user_id):
    if not validate_user(user_id):
        return jsonify({"error": "Invalid user ID"}), 400
    user = get_user(user_id)
    if user:
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404

@app.route('/api/users', methods=['POST'])
def create_user_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    if not name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
    user = create_user(name, email, password)
    return jsonify(user), 201

@app.route('/api/process', methods=['POST'])
def process_endpoint():
    data = request.get_json()
    items = data.get('items', [])
    result = process_data(items)
    return jsonify({"result": result})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# Duplicate function - same logic as process_data
def clean_strings(strings):
    # type: (list) -> list
    result = []
    for s in strings:
        if s is not None:
            cleaned = s.strip().lower()
            if len(cleaned) > 0:
                result.append(cleaned)
    return result

# Unused function - dead code
def deprecated_helper(x):
    # type: (int) -> int
    return x * 2

# Another unused function
def old_format_date(date_str):
    # type: (str) -> str
    parts = date_str.split('-')
    return f"{parts[2]}/{parts[1]}/{parts[0]}"

class UserService:
    """Service for user operations."""

    def __init__(self):
        self.db = get_db()

    def get_by_id(self, user_id):
        # type: (int) -> dict
        return get_user(user_id)

    def get_all(self):
        # type: () -> list
        return get_users(100, 0)

    def create(self, name, email, password):
        # type: (str, str, str) -> dict
        return create_user(name, email, password)

    def delete(self, user_id):
        # type: (int) -> bool
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.db.commit()
        return cursor.rowcount > 0


class EmailService:

    def __init__(self, api_key):
        self.api_key = api_key

    def send(self, to, subject, body):
        # TODO(john): Add rate limiting
        return send_email(to, subject, body)

    def send_bulk(self, recipients, subject, body):
        results = []
        for recipient in recipients:
            result = self.send(recipient, subject, body)
            results.append(result)
        return results


if __name__ == '__main__':
    app.run(debug=True)
