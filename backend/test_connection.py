from database import engine

try:
    connection = engine.connect()

    print("MySQL Connection Successful!")
    print("Connected to Chronexa AI Database.")

    connection.close()

except Exception as e:
    print("Database Connection Failed!")
    print(e)
    