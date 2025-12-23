"""
Reset admin user script.

Deletes all existing superusers and creates a new admin user.
"""
import sqlite3
import os
import sys

# Add project root to path for password hashing
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from passlib.context import CryptContext

# Password hashing (same as in auth module)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def reset_admin():
    """Delete all superusers and create new admin."""

    db_path = os.path.join(PROJECT_ROOT, "data", "whisperx.db")

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        print("Make sure to run the API server at least once to create the database.")
        return

    print(f"Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete all existing superusers
    cursor.execute("SELECT id, email FROM users WHERE is_superuser = 1")
    superusers = cursor.fetchall()

    if superusers:
        print(f"\nDeleting {len(superusers)} existing superuser(s):")
        for su_id, su_email in superusers:
            print(f"  - {su_email} (id={su_id})")
        cursor.execute("DELETE FROM users WHERE is_superuser = 1")

    # Check if admin email already exists (non-superuser)
    cursor.execute("SELECT id, email FROM users WHERE email = 'admin'")
    existing = cursor.fetchone()
    if existing:
        print(f"\nDeleting existing 'admin' user (id={existing[0]})")
        cursor.execute("DELETE FROM users WHERE email = 'admin'")

    # Create new admin
    hashed_password = get_password_hash("sa51ag6w")

    cursor.execute("""
        INSERT INTO users (email, hashed_password, full_name, role, is_superuser, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, ("admin", hashed_password, "Administrator", "admin", 1, 1))

    new_id = cursor.lastrowid

    conn.commit()
    conn.close()

    print(f"\n{'='*40}")
    print("New admin created:")
    print(f"  Email:    admin")
    print(f"  Password: sa51ag6w")
    print(f"  ID:       {new_id}")
    print(f"  Role:     admin")
    print(f"  Superuser: Yes")
    print(f"{'='*40}")


if __name__ == "__main__":
    reset_admin()
