
#!/usr/bin/env python3
import sqlite3
import os
import sys
import csv
import getpass
import hashlib
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

# ---------- Utilities ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def now_str():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

# ---------- Database setup ----------
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash TEXT
    );
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE
    );
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY,
        name TEXT,
        contact TEXT
    );
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        sku TEXT UNIQUE,
        name TEXT,
        category_id INTEGER,
        supplier_id INTEGER,
        unit_price REAL DEFAULT 0,
        quantity INTEGER DEFAULT 0,
        min_quantity INTEGER DEFAULT 0,
        notes TEXT,
        FOREIGN KEY(category_id) REFERENCES categories(id),
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
    );
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        item_id INTEGER,
        change INTEGER,
        type TEXT,
        note TEXT,
        timestamp TEXT,
        user_id INTEGER,
        FOREIGN KEY(item_id) REFERENCES items(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    ''')
    conn.commit()

    # create default admin if no users
    cur.execute("SELECT COUNT(*) FROM users;")
    if cur.fetchone()[0] == 0:
        default_user = "admin"
        default_pass = "admin"
        cur.execute("INSERT INTO users (username, password_hash) VALUES (?,?)",
                    (default_user, hash_password(default_pass)))
        conn.commit()
        print("Created default user 'admin' with password 'admin'. PLEASE change it after login.")

    conn.close()


# ---------- User/Auth ----------
def login():
    conn = get_conn()
    cur = conn.cursor()
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ").strip()
    cur.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        print("User not found.")
        return None
    if hash_password(password) == row["password_hash"]:
        return {"id": row["id"], "username": username}
    else:
        print("Incorrect password.")
        return None

def change_admin_password(user):
    conn = get_conn()
    cur = conn.cursor()
    new = getpass.getpass("New password: ").strip()
    confirm = getpass.getpass("Confirm password: ").strip()
    if new != confirm:
        print("Passwords do not match.")
        conn.close()
        return
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new), user['id']))
    conn.commit()
    conn.close()
    print("Password updated.")


# ---------- Category & Supplier helpers ----------
def choose_category():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY name;")
    rows = cur.fetchall()
    if not rows:
        print("No categories defined. You can skip or add a new one.")
        conn.close()
        return None
    print("Categories:")
    for r in rows:
        print(f"{r['id']}: {r['name']}")
    try:
        cid = input("Enter category id (or blank to skip): ").strip()
        if cid == "":
            conn.close()
            return None
        cid = int(cid)
    except ValueError:
        print("Invalid id.")
        conn.close()
        return None
    conn.close()
    return cid

def choose_supplier():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM suppliers ORDER BY name;")
    rows = cur.fetchall()
    if not rows:
        print("No suppliers defined. You can skip or add a new one.")
        conn.close()
        return None
    print("Suppliers:")
    for r in rows:
        print(f"{r['id']}: {r['name']}")
    try:
        sid = input("Enter supplier id (or blank to skip): ").strip()
        if sid == "":
            conn.close()
            return None
        sid = int(sid)
    except ValueError:
        print("Invalid id.")
        conn.close()
        return None
    conn.close()
    return sid

# ---------- Item operations ----------
def add_item(user):
    conn = get_conn()
    cur = conn.cursor()
    sku = input("SKU (unique): ").strip()
    name = input("Name: ").strip()
    print("Choose category (optional):")
    category_id = choose_category()
    print("Choose supplier (optional):")
    supplier_id = choose_supplier()
    try:
        unit_price = float(input("Unit price (0): ").strip() or 0)
    except ValueError:
        unit_price = 0.0
    try:
        quantity = int(input("Initial quantity (0): ").strip() or 0)
    except ValueError:
        quantity = 0
    try:
        min_q = int(input("Min quantity for alerts (0): ").strip() or 0)
    except ValueError:
        min_q = 0
    notes = input("Notes (optional): ").strip()
    try:
        cur.execute('''INSERT INTO items (sku,name,category_id,supplier_id,unit_price,quantity,min_quantity,notes)
                       VALUES (?,?,?,?,?,?,?,?)''',
                    (sku, name, category_id, supplier_id, unit_price, quantity, min_q, notes))
        item_id = cur.lastrowid
        if quantity:
            cur.execute('''INSERT INTO transactions (item_id,change,type,note,timestamp,user_id)
                           VALUES (?,?,?,?,?,?)''', (item_id, quantity, 'init', 'Initial stock', now_str(), user['id']))
        conn.commit()
        print("Item added.")
    except sqlite3.IntegrityError as e:
        print("Error: SKU must be unique or other integrity error.", e)
    finally:
        conn.close()

def edit_item():
    conn = get_conn()
    cur = conn.cursor()
    item = select_item_by_sku_or_id(cur)
    if not item:
        conn.close()
        return
    print(f"Editing item {item['id']} - {item['sku']} - {item['name']}")
    name = input(f"Name [{item['name']}]: ").strip() or item['name']
    print("Category:")
    category_id = choose_category() or item['category_id']
    print("Supplier:")
    supplier_id = choose_supplier() or item['supplier_id']
    try:
        unit_price = float(input(f"Unit price [{item['unit_price']}]: ").strip() or item['unit_price'])
    except ValueError:
        unit_price = item['unit_price']
    try:
        min_q = int(input(f"Min quantity [{item['min_quantity']}]: ").strip() or item['min_quantity'])
    except ValueError:
        min_q = item['min_quantity']
    notes = input(f"Notes [{item['notes'] or ''}]: ").strip() or item['notes']
    cur.execute('''UPDATE items SET name=?, category_id=?, supplier_id=?, unit_price=?, min_quantity=?, notes=? WHERE id=?''',
                (name, category_id, supplier_id, unit_price, min_q, notes, item['id']))
    conn.commit()
    conn.close()
    print("Item updated. Quantity not changed here (use Adjust stock).")

def delete_item():
    conn = get_conn()
    cur = conn.cursor()
    item = select_item_by_sku_or_id(cur)
    if not item:
        conn.close()
        return
    confirm = input(f"Delete {item['sku']} - {item['name']}? type YES to confirm: ")
    if confirm == "YES":
        cur.execute("DELETE FROM items WHERE id=?", (item['id'],))
        cur.execute("DELETE FROM transactions WHERE item_id=?", (item['id'],))
        conn.commit()
        print("Item and related transactions deleted.")
    else:
        print("Aborted.")
    conn.close()

def select_item_by_sku_or_id(cur):
    key = input("Enter item id or SKU: ").strip()
    if key.isdigit():
        cur.execute("SELECT * FROM items WHERE id=?", (int(key),))
    else:
        cur.execute("SELECT * FROM items WHERE sku=?", (key,))
    row = cur.fetchone()
    if not row:
        print("Item not found.")
        return None
    return row

def adjust_stock(user):
    conn = get_conn()
    cur = conn.cursor()
    item = select_item_by_sku_or_id(cur)
    if not item:
        conn.close()
        return
    print(f"Current quantity: {item['quantity']}")
    try:
        change = int(input("Quantity change (use negative to decrease): ").strip())
    except ValueError:
        print("Invalid number.")
        conn.close()
        return
    ttype = input("Type (receive/sell/correction/other): ").strip() or "other"
    note = input("Note (optional): ").strip()
    new_q = item['quantity'] + change
    if new_q < 0:
        print("Resulting quantity would be negative. Aborted.")
        conn.close()
        return
    cur.execute("UPDATE items SET quantity=? WHERE id=?", (new_q, item['id']))
    cur.execute('''INSERT INTO transactions (item_id,change,type,note,timestamp,user_id)
                   VALUES (?,?,?,?,?,?)''', (item['id'], change, ttype, note, now_str(), user['id']))
    conn.commit()
    conn.close()
    print(f"Stock updated. New quantity: {new_q}")

# ---------- Search / Reports ----------
def search_items():
    conn = get_conn()
    cur = conn.cursor()
    q = input("Search by SKU or name (partial allowed): ").strip()
    qlike = f"%{q}%"
    cur.execute("SELECT i.id,i.sku,i.name,i.quantity,i.unit_price,i.min_quantity,c.name as category,s.name as supplier FROM items i LEFT JOIN categories c ON i.category_id=c.id LEFT JOIN suppliers s ON i.supplier_id=s.id WHERE i.sku LIKE ? OR i.name LIKE ? ORDER BY i.name", (qlike, qlike))
    rows = cur.fetchall()
    conn.close()
    print_items_table(rows)

def list_all_items():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT i.id,i.sku,i.name,i.quantity,i.unit_price,i.min_quantity,c.name as category,s.name as supplier FROM items i LEFT JOIN categories c ON i.category_id=c.id LEFT JOIN suppliers s ON i.supplier_id=s.id ORDER BY i.name")
    rows = cur.fetchall()
    conn.close()
    print_items_table(rows)

def print_items_table(rows):
    if not rows:
        print("No items found.")
        return
    headers = ["ID","SKU","Name","Qty","Unit Price","Min Qty","Category","Supplier"]
    table = []
    for r in rows:
        table.append([r["id"], r["sku"], r["name"], r["quantity"], r["unit_price"], r["min_quantity"], r["category"] or "", r["supplier"] or ""])
    # nice pretty print if tabulate is installed (optional)
    try:
        from tabulate import tabulate
        print(tabulate(table, headers=headers, tablefmt="grid"))
    except Exception:
        print(" | ".join(headers))
        for row in table:
            print(" | ".join(str(x) for x in row))

def low_stock_report():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT sku,name,quantity,min_quantity FROM items WHERE min_quantity>0 AND quantity<=min_quantity ORDER BY quantity ASC")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("No low-stock items.")
        return
    print("Low stock items:")
    for r in rows:
        print(f"{r['sku']} - {r['name']}: {r['quantity']} (min {r['min_quantity']})")

def view_history():
    conn = get_conn()
    cur = conn.cursor()
    key = input("Enter item id or SKU to view history (leave blank to show recent): ").strip()
    if key:
        if key.isdigit():
            cur.execute("SELECT id FROM items WHERE id=?", (int(key),))
        else:
            cur.execute("SELECT id FROM items WHERE sku=?", (key,))
        row = cur.fetchone()
        if not row:
            print("Item not found.")
            conn.close()
            return
        item_id = row['id']
        cur.execute('''SELECT t.id,t.item_id,t.change,t.type,t.note,t.timestamp,u.username FROM transactions t LEFT JOIN users u ON t.user_id=u.id WHERE t.item_id=? ORDER BY t.timestamp DESC''', (item_id,))
    else:
        cur.execute('''SELECT t.id,t.item_id,i.sku,i.name,t.change,t.type,t.note,t.timestamp,u.username FROM transactions t LEFT JOIN users u ON t.user_id=u.id LEFT JOIN items i ON t.item_id=i.id ORDER BY t.timestamp DESC LIMIT 200''')
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("No transactions found.")
        return
    for r in rows:
        if 'sku' in r.keys():
            print(f"[{r['timestamp']}] ({r['username']}) {r['sku']} {r['name']}: {r['change']} ({r['type']}) - {r['note']}")
        else:
            print(f"[{r['timestamp']}] ({r['username']}) item {r['item_id']}: {r['change']} ({r['type']}) - {r['note']}")


# ---------- Categories & Suppliers CRUD ----------
def add_category():
    name = input("Category name: ").strip()
    if not name:
        return
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        print("Category added.")
    except sqlite3.IntegrityError:
        print("Category already exists.")
    finally:
        conn.close()

def list_categories():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM categories ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    for r in rows:
        print(f"{r['id']}: {r['name']}")

def add_supplier():
    name = input("Supplier name: ").strip()
    contact = input("Contact details (optional): ").strip()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO suppliers (name,contact) VALUES (?,?)", (name,contact))
    conn.commit()
    conn.close()
    print("Supplier added.")

def list_suppliers():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,name,contact FROM suppliers ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    for r in rows:
        print(f"{r['id']}: {r['name']} - {r['contact']}")

# ---------- Import / Export CSV ----------
def export_csv():
    path = input("Export CSV path (e.g. export.csv): ").strip() or "export.csv"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT sku,name,quantity,unit_price,min_quantity,notes FROM items ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    with open(path, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["sku","name","quantity","unit_price","min_quantity","notes"])
        for r in rows:
            writer.writerow([r["sku"], r["name"], r["quantity"], r["unit_price"], r["min_quantity"], r["notes"]])
    print("Exported to", path)

def import_csv(user):
    path = input("CSV path to import (sku,name,quantity,unit_price,min_quantity,notes): ").strip()
    if not os.path.exists(path):
        print("File not found.")
        return
    conn = get_conn()
    cur = conn.cursor()
    imported = 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sku = row.get("sku") or ""
            name = row.get("name") or ""
            try:
                quantity = int(row.get("quantity") or 0)
            except ValueError:
                quantity = 0
            try:
                unit_price = float(row.get("unit_price") or 0)
            except ValueError:
                unit_price = 0.0
            try:
                min_q = int(row.get("min_quantity") or 0)
            except ValueError:
                min_q = 0
            notes = row.get("notes") or ""
            if not sku or not name:
                continue
            try:
                cur.execute("INSERT INTO items (sku,name,unit_price,quantity,min_quantity,notes) VALUES (?,?,?,?,?,?)",
                            (sku,name,unit_price,quantity,min_q,notes))
                item_id = cur.lastrowid
                if quantity:
                    cur.execute('''INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)''',
                                (item_id, quantity, 'import', 'Imported from CSV', now_str(), user['id']))
                imported += 1
            except sqlite3.IntegrityError:
                cur.execute("SELECT id,quantity FROM items WHERE sku=?", (sku,))
                existing = cur.fetchone()
                if existing:
                    new_q = existing["quantity"] + quantity
                    cur.execute("UPDATE items SET name=?,unit_price=?,quantity=?,min_quantity=?,notes=? WHERE id=?",
                                (name, unit_price, new_q, min_q, notes, existing["id"]))
                    if quantity:
                        cur.execute('''INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)''',
                                    (existing["id"], quantity, 'import', 'Imported from CSV (merge)', now_str(), user['id']))
                    imported += 1
    conn.commit()
    conn.close()
    print(f"Imported {imported} rows.")

# ---------- Main Menu ----------
def print_menu():
    menu = [
        ("1","Add item"),
        ("2","Edit item (metadata)"),
        ("3","Delete item"),
        ("4","Adjust stock (receive / sell / correction)"),
        ("5","Search items"),
        ("6","List all items"),
        ("7","Low-stock report"),
        ("8","View history / transactions"),
        ("9","Export items to CSV"),
        ("10","Import items from CSV"),
        ("11","Categories: add / list"),
        ("12","Suppliers: add / list"),
        ("13","Change password"),
        ("0","Exit"),
    ]
    print("\n--- Inventory Management ---")
    for code,desc in menu:
        print(f"{code}. {desc}")

def categories_menu():
    print("\n-- Categories --")
    print("1. Add category")
    print("2. List categories")
    print("0. Back")
    choice = input("> ").strip()
    if choice=="1":
        add_category()
    elif choice=="2":
        list_categories()
    else:
        return

def suppliers_menu():
    print("\n-- Suppliers --")
    print("1. Add supplier")
    print("2. List suppliers")
    print("0. Back")
    choice = input("> ").strip()
    if choice=="1":
        add_supplier()
    elif choice=="2":
        list_suppliers()
    else:
        return

def main():
    init_db()
    print("Welcome to Inventory App (Python only).")
    user = None
    while not user:
        user = login()
        if not user:
            if input("Try again? (y/n): ").strip().lower() != "y":
                print("Exiting.")
                return
    while True:
        print_menu()
        choice = input("> ").strip()
        if choice=="1":
            add_item(user)
        elif choice=="2":
            edit_item()
        elif choice=="3":
            delete_item()
        elif choice=="4":
            adjust_stock(user)
        elif choice=="5":
            search_items()
        elif choice=="6":
            list_all_items()
        elif choice=="7":
            low_stock_report()
        elif choice=="8":
            view_history()
        elif choice=="9":
            export_csv()
        elif choice=="10":
            import_csv(user)
        elif choice=="11":
            categories_menu()
        elif choice=="12":
            suppliers_menu()
        elif choice=="13":
            change_admin_password(user)
        elif choice=="0":
            print("Goodbye.")
            break
        else:
            print("Unknown option. Try again.")

if __name__ == "__main__":
    main()
