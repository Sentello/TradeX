import secrets
import bcrypt

def generate_flask_secret_key():
    """Generates a random, cryptographically secure Flask secret key."""
    return secrets.token_hex(32)

def generate_hashed_password():
    """Generates a bcrypt hashed password."""
    while True:
        password = input("Enter a password for the dashboard: ")
        if not password:
            print("Password cannot be empty. Please try again.")
            continue
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return hashed_password.decode('utf-8')

if __name__ == "__main__":
    flask_secret_key = generate_flask_secret_key()
    hashed_password = generate_hashed_password()

    print("\nGenerated Credentials:")
    print("----------------------")
    print(f"FLASK_SECRET_KEY={flask_secret_key}")
    print(f"DASHBOARD_PASSWORD={hashed_password}")
    print("\nInstructions:")
    print("1.  Copy the generated FLASK_SECRET_KEY and DASHBOARD_PASSWORD values.")
    print("2.  Update the .env file with these values.")
    print("3.  Restart the application.")