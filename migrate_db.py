"""
Run this once to add reset_token columns to existing users table in Supabase.
"""
from app import create_app
from models import db

app = create_app()

with app.app_context():
    try:
        with db.engine.connect() as conn:
            # Add reset_token column if not exists
            conn.execute(db.text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS reset_token VARCHAR(100),
                ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP;
            """))
            conn.commit()
            print("✅ Migration successful! Columns added.")
    except Exception as e:
        print(f"❌ Error: {e}")
