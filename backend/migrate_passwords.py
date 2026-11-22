from database import get_db_connection
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

db = None
cursor = None

try:
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get all existing accounts
    cursor.execute(
        "SELECT Account_Id, Password FROM LAF_Account"
    )

    accounts = cursor.fetchall()
    migrated_count = 0

    for account in accounts:
        account_id = account["Account_Id"]
        old_password = account["Password"]

        # Skip empty passwords and existing Argon2 hashes
        if not old_password or old_password.startswith("$argon2"):
            continue

        # Convert plain-text password to Argon2 hash
        new_hash = password_hash.hash(old_password)

        cursor.execute(
            """
            UPDATE LAF_Account
            SET Password = %s
            WHERE Account_Id = %s
            """,
            (new_hash, account_id)
        )

        migrated_count += 1

    db.commit()

    print("Password migration successful!")
    print("Accounts migrated:", migrated_count)

except Exception as e:
    if db:
        db.rollback()

    print("Migration failed:", str(e))

finally:
    if cursor:
        cursor.close()

    if db:
        db.close()

