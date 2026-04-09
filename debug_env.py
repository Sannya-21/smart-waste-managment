try:
    import flask
    print("Flask ok")
    import flask_login
    print("Flask-Login ok")
    import werkzeug
    print("Werkzeug ok")
    import sqlite3
    print("sqlite3 ok")
except Exception as e:
    print(f"Error: {e}")
