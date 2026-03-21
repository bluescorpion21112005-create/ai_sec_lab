# fix_admin.py
import sqlite3
import os

# Database faylini topish
db_path = "siteguard.db"

# Agar shu papkada bo'lmasa, instance papkasini tekshirish
if not os.path.exists(db_path):
    if os.path.exists("instance/siteguard.db"):
        db_path = "instance/siteguard.db"
    else:
        print("Database topilmadi!")
        print("Iltimos, quyidagi yo'llarni tekshiring:")
        print("  - ./siteguard.db")
        print("  - instance/siteguard.db")
        exit(1)

print(f"Database: {db_path}")

# Database'ga ulanish
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# user tablosidagi kolonkalarni ko'rish
print("\n=== User tablosidagi kolonkalar ===")
cursor.execute("PRAGMA table_info(user)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# is_admin kolonkasi mavjudligini tekshirish
cursor.execute("PRAGMA table_info(user)")
has_is_admin = any(col[1] == 'is_admin' for col in cursor.fetchall())

if not has_is_admin:
    print("\n⚠️ is_admin kolonkasi mavjud emas! Qo'shish kerak...")
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        conn.commit()
        print("✅ is_admin kolonkasi qo'shildi!")
    except Exception as e:
        print(f"Xatolik: {e}")

# Barcha foydalanuvchilarni ko'rish
print("\n=== Mavjud foydalanuvchilar ===")
cursor.execute("SELECT id, email, full_name, is_admin FROM user")
users = cursor.fetchall()
print(f"Jami: {len(users)} ta foydalanuvchi")
for user in users:
    admin_status = "✅ ADMIN" if user[3] else "❌ USER"
    print(f"  ID: {user[0]} | Email: {user[1]} | Ismi: {user[2]} | {admin_status}")

# Foydalanuvchilarni admin qilish
if users:
    print("\n=== Admin qilish ===")
    
    # Birinchi foydalanuvchini admin qilish
    first_user_id = users[0][0]
    cursor.execute("UPDATE user SET is_admin = 1 WHERE id = ?", (first_user_id,))
    conn.commit()
    print(f"✅ ID: {first_user_id} ({users[0][1]}) foydalanuvchi admin qilindi!")
    
    # Agar barchasini admin qilmoqchi bo'lsangiz:
    # cursor.execute("UPDATE user SET is_admin = 1")
    # conn.commit()
    # print("✅ Barcha foydalanuvchilar admin qilindi!")
    
else:
    print("\n❌ Hech qanday foydalanuvchi topilmadi!")
    print("Iltimos, avval ro'yxatdan o'ting!")

# Yangilangan ro'yxat
print("\n=== Yangilangan foydalanuvchilar ===")
cursor.execute("SELECT id, email, full_name, is_admin FROM user")
users = cursor.fetchall()
for user in users:
    admin_status = "✅ ADMIN" if user[3] else "❌ USER"
    print(f"  ID: {user[0]} | Email: {user[1]} | Ismi: {user[2]} | {admin_status}")

conn.commit()
conn.close()

print("\n✅ Admin sozlamalari yangilandi!")
print("Endi http://localhost:5000/admin manziliga kiring.")