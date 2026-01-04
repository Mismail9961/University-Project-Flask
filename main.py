from flask import Flask, request, jsonify, g
import sqlite3
from datetime import datetime

# -----------------------------
# App Configuration
# -----------------------------
app = Flask(__name__)
DATABASE = "app.db"

# -----------------------------
# Database Helpers
# -----------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    db.commit()

# -----------------------------
# Utility Functions
# -----------------------------
def user_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


def error_response(message, status=400):
    return jsonify({"error": message}), status

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return jsonify({
        "message": "Flask API is running",
        "endpoints": [
            "GET /users",
            "POST /users",
            "GET /users/<id>",
            "PUT /users/<id>",
            "DELETE /users/<id>"
        ]
    })


@app.route("/users", methods=["GET"])
def get_users():
    db = get_db()
    users = db.execute("SELECT * FROM users").fetchall()
    return jsonify([user_to_dict(u) for u in users])


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    if not data:
        return error_response("JSON body required")

    name = data.get("name")
    email = data.get("email")

    if not name or not email:
        return error_response("Name and email are required")

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
            (name, email, datetime.utcnow().isoformat())
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error_response("Email already exists", 409)

    return jsonify({"message": "User created"}), 201


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if user is None:
        return error_response("User not found", 404)

    return jsonify(user_to_dict(user))


@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()
    if not data:
        return error_response("JSON body required")

    name = data.get("name")
    email = data.get("email")

    if not name and not email:
        return error_response("Nothing to update")

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if user is None:
        return error_response("User not found", 404)

    new_name = name if name else user["name"]
    new_email = email if email else user["email"]

    try:
        db.execute(
            "UPDATE users SET name = ?, email = ? WHERE id = ?",
            (new_name, new_email, user_id)
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error_response("Email already exists", 409)

    return jsonify({"message": "User updated"})


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    db = get_db()
    cursor = db.execute(
        "DELETE FROM users WHERE id = ?", (user_id,)
    )
    db.commit()

    if cursor.rowcount == 0:
        return error_response("User not found", 404)

    return jsonify({"message": "User deleted"})

# -----------------------------
# Error Handlers
# -----------------------------
@app.errorhandler(404)
def not_found(e):
    return error_response("Endpoint not found", 404)


@app.errorhandler(500)
def server_error(e):
    return error_response("Internal server error", 500)

# -----------------------------
# App Entry Point
# -----------------------------
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
