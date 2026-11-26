"""
One-time migration: convert old base64 password-vault rows to real encryption.

The app reads old rows transparently, so this is not urgent - but until you
run it, those rows are still stored unencrypted in the database.

Run it once after deploying, with VAULT_KEY set:

    python migrate_vault.py            # show what would change
    python migrate_vault.py --apply    # actually convert

Safe to run more than once: already-encrypted rows are skipped.
"""

import sys
import base64

from app import app
from models import db
from routes.vault import PasswordVault, _fernet


def main(apply_changes):
    with app.app_context():
        f = _fernet()
        if f is None:
            print("ERROR: VAULT_KEY is not set (or is not a valid Fernet key).")
            print("       Generate one with:")
            print('       python -c "from cryptography.fernet import Fernet;'
                  'print(Fernet.generate_key().decode())"')
            return 1

        rows = PasswordVault.query.all()
        if not rows:
            print("No password entries found. Nothing to do.")
            return 0

        legacy, already, failed = [], 0, []

        for row in rows:
            if not row.password:
                continue
            try:
                f.decrypt(row.password.encode())
                already += 1
                continue
            except Exception:
                pass
            try:
                plain = base64.b64decode(row.password.encode()).decode()
                legacy.append((row, plain))
            except Exception:
                failed.append(row)

        print(f"Total entries        : {len(rows)}")
        print(f"Already encrypted    : {already}")
        print(f"Old base64, to fix   : {len(legacy)}")
        print(f"Unreadable (skipped) : {len(failed)}")
        for row in failed:
            print(f"   ! id={row.id} {row.app_name!r} - left untouched")

        if not legacy:
            print("\nNothing to convert.")
            return 0

        if not apply_changes:
            print("\nDry run. Re-run with --apply to convert these entries.")
            for row, _ in legacy:
                print(f"   would encrypt id={row.id} {row.app_name!r}")
            return 0

        for row, plain in legacy:
            row.password = f.encrypt(plain.encode()).decode()
        db.session.commit()
        print(f"\nDone. {len(legacy)} entries are now encrypted.")
        print("Reminder: keep your own copy of VAULT_KEY. Without it these "
              "entries cannot be read again.")
        return 0


if __name__ == '__main__':
    sys.exit(main('--apply' in sys.argv))
