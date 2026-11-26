"""
Set a login password for a MyVault user, or list the users.

Login passwords are HASHED (pbkdf2:sha256), which is one-way - there is no way
to read an existing password back out of the database. If someone is locked
out, you set a new password instead.

    python set_password.py --list
    python set_password.py --email papa@example.com --password "NewPass123"
    python set_password.py --email papa@example.com --password "NewPass123" --sql

--sql prints an UPDATE statement instead of touching the database. Use that for
Supabase: run it in the SQL Editor. It needs no psycopg2 on your Mac.
"""

import argparse
import sys

from werkzeug.security import generate_password_hash


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--list', action='store_true', help='show all users')
    p.add_argument('--email')
    p.add_argument('--password')
    p.add_argument('--sql', action='store_true',
                   help='print SQL for Supabase instead of writing to the database')
    args = p.parse_args()

    # Hash-only mode needs no app or database connection at all.
    if args.sql:
        if not args.email or not args.password:
            p.error('--sql needs both --email and --password')
        if len(args.password) < 8:
            p.error('password must be at least 8 characters')
        h = generate_password_hash(args.password, method='pbkdf2:sha256')
        print("\nRun this in the Supabase SQL Editor:\n")
        print(f"UPDATE users SET password_hash = '{h}',")
        print(f"                 reset_token = NULL,")
        print(f"                 reset_token_expiry = NULL")
        print(f" WHERE email = '{args.email}';\n")
        print("Then log in with the password you just chose.")
        return 0

    from app import app
    from models import db, User

    with app.app_context():
        if args.list:
            users = User.query.order_by(User.id).all()
            if not users:
                print("No users yet. Register the first one in the app - "
                      "whoever registers first becomes admin.")
                return 0
            print(f"\n{'id':<4} {'name':<22} {'email':<32} role")
            print("-" * 70)
            for u in users:
                print(f"{u.id:<4} {u.name:<22} {u.email:<32} {u.role}")
            print()
            return 0

        if not args.email or not args.password:
            p.error('need --email and --password (or --list)')
        if len(args.password) < 8:
            p.error('password must be at least 8 characters')

        user = User.query.filter_by(email=args.email.strip().lower()).first()
        if not user:
            print(f"No user with email {args.email!r}.")
            print("Run with --list to see the accounts that exist.")
            return 1

        user.password_hash = generate_password_hash(args.password,
                                                    method='pbkdf2:sha256')
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        print(f"Password updated for {user.name} <{user.email}>.")
        return 0


if __name__ == '__main__':
    sys.exit(main())
