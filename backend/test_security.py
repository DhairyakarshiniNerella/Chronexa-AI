from security import hash_password, verify_password

# Original password
password = "Chronexa@123"

# Generate secure hash
hashed_password = hash_password(password)

print("Original Password:", password)
print("Hashed Password:", hashed_password)

# Verify correct password
print("Correct Password:", verify_password(password, hashed_password))

# Verify incorrect password
print("Wrong Password:", verify_password("Wrong@123", hashed_password))