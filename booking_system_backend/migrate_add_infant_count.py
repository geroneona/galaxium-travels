"""
Migration script to add infant_count column to existing bookings table.
Run this script if you have an existing database with bookings.
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('booking.db')
    cursor = conn.cursor()
    
    try:
        # Check if infant_count column already exists
        cursor.execute("PRAGMA table_info(bookings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'infant_count' not in columns:
            print("Adding infant_count column to bookings table...")
            cursor.execute("ALTER TABLE bookings ADD COLUMN infant_count INTEGER NOT NULL DEFAULT 0")
            conn.commit()
            print("[SUCCESS] Migration completed successfully!")
        else:
            print("[INFO] infant_count column already exists. No migration needed.")
            
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

# Made with Bob
