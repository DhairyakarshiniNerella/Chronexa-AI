from security import create_access_token
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

# Generate a test token
token = create_access_token({"sub": "1"})

print("Generated Token:")
print(token)

# Decode the token
decoded = jwt.decode(
    token,
    os.getenv("JWT_SECRET_KEY"),
    algorithms=["HS256"]
)

print("\nDecoded Token:")
print(decoded)

print("\nJWT authentication test successful!")