from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)

app.secret_key = "spendwise-secret-key"


def get_db_connection():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL")
    )


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            expense_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Incomes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incomes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            income_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    cursor.close()
    conn.close()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match!"

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
                """,
                (name, email, hashed_password)
            )

            conn.commit()

        except psycopg2.IntegrityError:
            conn.rollback()
            cursor.close()
            conn.close()
            return "This email is already registered!"

        cursor.close()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["user_name"] = user[1]

            return redirect("/dashboard")

        return "Invalid email or password!"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Calculate total income
    cursor.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM incomes
        WHERE user_id = %s
        """,
        (session["user_id"],)
    )

    total_income = cursor.fetchone()[0]

    # Calculate total expense
    cursor.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = %s
        """,
        (session["user_id"],)
    )

    total_expense = cursor.fetchone()[0]

    # Calculate balance
    balance = total_income - total_expense

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        total_income=total_income,
        total_expense=total_expense,
        balance=balance
    )


@app.route("/add-expense", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        amount = request.form["amount"]
        category = request.form["category"]
        expense_date = request.form["expense_date"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO expenses
            (user_id, title, amount, category, expense_date)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                title,
                amount,
                category,
                expense_date
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_expense.html")


@app.route("/add-income", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        amount = request.form["amount"]
        income_date = request.form["income_date"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO incomes
            (user_id, title, amount, income_date)
            VALUES (%s, %s, %s, %s)
            """,
            (
                session["user_id"],
                title,
                amount,
                income_date
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_income.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# Initialize database
init_db()


if __name__ == "__main__":
    app.run(debug=True)