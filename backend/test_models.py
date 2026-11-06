from database import engine
from models import User, Task
from sqlalchemy import inspect

try:
    inspector = inspect(engine)

    tables = inspector.get_table_names()

    print("Database Tables:", tables)

    print("\nUser Model:")
    print(User.__tablename__)
    print("Columns:", list(User.__table__.columns.keys()))

    print("\nTask Model:")
    print(Task.__tablename__)
    print("Columns:", list(Task.__table__.columns.keys()))

    if "users" in tables and "tasks" in tables:
        print("\nSUCCESS: Both database tables are recognized!")

    else:
        print("\nERROR: Required tables are missing.")

except Exception as e:
    print("Error:", e)