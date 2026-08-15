import getpass
import secrets

import bcrypt


def generate_flask_secret_key():
    """Generates a random, cryptographically secure Flask secret key."""
    return secrets.token_hex(32)


def generate_webhook_pin():
    """Generates a long random PIN for the webhook endpoint."""
    return secrets.token_urlsafe(32)


def generate_hashed_password():
    """Prompt for a dashboard password (hidden) and return its bcrypt hash."""
    while True:
        password = getpass.getpass("Enter a password for the dashboard: ")
        if not password:
            print("Password cannot be empty. Please try again.")
            continue
        confirm = getpass.getpass("Confirm the dashboard password: ")
        if password != confirm:
            print("Passwords do not match. Please try again.")
            continue
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        # Compose interpolates .env: $2b$12$abc becomes $2b$12 + unset $abc.
        # Write $$ so a literal $ survives paste-into-.env.
        return hashed_password.decode("utf-8").replace("$", "$$")


if __name__ == "__main__":
    flask_secret_key = generate_flask_secret_key()
    webhook_pin = generate_webhook_pin()
    hashed_password = generate_hashed_password()

    print("\nGenerated Credentials:")
    print("----------------------")
    print(f"FLASK_SECRET_KEY={flask_secret_key}")
    print(f"WEBHOOK_PIN={webhook_pin}")
    print(f"DASHBOARD_PASSWORD={hashed_password}")
    print("\nInstructions:")
    print("1. Copy these three lines into your .env file.")
    print("2. Paste the DASHBOARD_PASSWORD line as printed (it uses $$ so Docker")
    print("   Compose does not eat the $ in the bcrypt hash). Do not paste the")
    print("   password you typed.")
    print("3. Restart the application.")
