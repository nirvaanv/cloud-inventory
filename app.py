import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for


app = Flask(__name__)
DATABASE_PATH = os.environ.get("DATABASE_PATH", "instance/inventory.db")


def connect_db():
    path = Path(DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def db_session():
    connection = connect_db()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_db():
    with db_session() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0)
            )"""
        )


initialize_db()


@app.get("/")
def index():
    with db_session() as connection:
        products = connection.execute(
            "SELECT id, name, quantity FROM products ORDER BY name"
        ).fetchall()
    return render_template("index.html", products=products, error=None)


@app.post("/products")
def add_product():
    name = request.form.get("name", "").strip()
    quantity_text = request.form.get("quantity", "").strip()
    try:
        quantity = int(quantity_text)
        if not name or quantity < 0:
            raise ValueError
    except ValueError:
        with db_session() as connection:
            products = connection.execute(
                "SELECT id, name, quantity FROM products ORDER BY name"
            ).fetchall()
        return render_template(
            "index.html", products=products,
            error="Enter a product name and a quantity of zero or more.",
        ), 400

    with db_session() as connection:
        connection.execute(
            "INSERT INTO products (name, quantity) VALUES (?, ?)",
            (name, quantity),
        )
    return redirect(url_for("index"))


@app.get("/health")
def health():
    with db_session() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "healthy"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
