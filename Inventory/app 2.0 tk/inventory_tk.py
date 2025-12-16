#!/usr/bin/env python3
'''
inventory_tk.py - Minimal Inventory Management with Tkinter and role-based users.
Features:
- SQLite backend (inventory.db)
- Tkinter GUI (login screen, main window with role-based features)
- Roles: admin (full access) and clerk (limited: search, list, adjust stock, view history)
- Admin can create users, categories, suppliers, and manage items
- Clerk can search items, adjust stock, and view low-stock
- All changes recorded in transactions table
- No external packages required
Run: python inventory_tk.py
'''

import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

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
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, role TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY, name TEXT, contact TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY, sku TEXT UNIQUE, name TEXT, category_id INTEGER, supplier_id INTEGER,
        unit_price REAL DEFAULT 0, quantity INTEGER DEFAULT 0, min_quantity INTEGER DEFAULT 0, notes TEXT,
        FOREIGN KEY(category_id) REFERENCES categories(id), FOREIGN KEY(supplier_id) REFERENCES suppliers(id))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY, item_id INTEGER, change INTEGER, type TEXT, note TEXT, timestamp TEXT, user_id INTEGER,
        FOREIGN KEY(item_id) REFERENCES items(id), FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()

    # default users if none exist
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
        print("Created default users: admin/admin and clerk/clerk. Change passwords after login.")
    conn.close()

# ---------- Data access helpers ----------
def get_user(username):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone(); conn.close(); return row

def list_items(q="%"):
    conn = get_conn(); cur = conn.cursor()
    qlike = f"%{q}%"
    cur.execute("SELECT i.*, c.name as category, s.name as supplier FROM items i LEFT JOIN categories c ON i.category_id=c.id LEFT JOIN suppliers s ON i.supplier_id=s.id WHERE i.sku LIKE ? OR i.name LIKE ? ORDER BY i.name", (qlike, qlike))
    rows = cur.fetchall(); conn.close(); return rows

def get_item_by_sku_or_id(key):
    conn = get_conn(); cur = conn.cursor()
    if str(key).isdigit():
        cur.execute("SELECT * FROM items WHERE id=?", (int(key),))
    else:
        cur.execute("SELECT * FROM items WHERE sku=?", (key,))
    row = cur.fetchone(); conn.close(); return row

# ---------- GUI Application ----------
class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Manager (Tk)")
        self.geometry("900x600")
        self.resizable(True, True)
        self.current_user = None
        self.create_login_screen()

    # ---------- Login ----------
    def create_login_screen(self):
        for w in self.winfo_children(): w.destroy()
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True)
        ttk.Label(frame, text="Inventory Manager", font=("Arial", 18)).grid(row=0, column=0, columnspan=2, pady=(0,10))
        ttk.Label(frame, text="Username:").grid(row=1, column=0, sticky="e")
        user_entry = ttk.Entry(frame); user_entry.grid(row=1, column=1, sticky="w")
        ttk.Label(frame, text="Password:").grid(row=2, column=0, sticky="e")
        pass_entry = ttk.Entry(frame, show="*"); pass_entry.grid(row=2, column=1, sticky="w")

        def do_login(event=None):
            username = user_entry.get().strip()
            password = pass_entry.get().strip()
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                messagebox.showerror("Login failed", "Incorrect username or password")
                return
            self.current_user = {"id": user["id"], "username": user["username"], "role": user["role"]}
            self.create_main_ui()

        login_btn = ttk.Button(frame, text="Login", command=do_login)
        login_btn.grid(row=3, column=0, columnspan=2, pady=10)
        self.bind("<Return>", do_login)

    # ---------- Main UI ----------
    def create_main_ui(self):
        for w in self.winfo_children(): w.destroy()
        top = ttk.Frame(self)
        top.pack(fill="x", padx=5, pady=5)
        ttk.Label(top, text=f"Logged in: {self.current_user['username']} ({self.current_user['role']})").pack(side="left")
        ttk.Button(top, text="Logout", command=self.logout).pack(side="right")

        # main panes
        pan = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        pan.pack(fill="both", expand=True)
        left = ttk.Frame(pan, width=350)
        right = ttk.Frame(pan)
        pan.add(left, weight=1)
        pan.add(right, weight=3)

        # Left: search and list
        search_frame = ttk.Frame(left, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search SKU/Name:").pack(anchor="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(fill="x")

        listbox = tk.Listbox(left)
        listbox.pack(fill="both", expand=True, padx=8, pady=8)

        def refresh_list(event=None):
            q = search_var.get() or "%"
            items = list_items(q)
            listbox.delete(0, tk.END)
            for it in items:
                listbox.insert(tk.END, f"{it['id']} | {it['sku']} | {it['name']} | Qty: {it['quantity']}")

        search_entry.bind("<KeyRelease>", lambda e: refresh_list())
        refresh_list()

        # Right: details and actions
        details = tk.Text(right, height=15)
        details.pack(fill="x", padx=8, pady=8)

        action_frame = ttk.Frame(right)
        action_frame.pack(fill="x", padx=8, pady=8)

        def show_selected(event=None):
            sel = listbox.curselection()
            if not sel: return
            text = listbox.get(sel[0])
            key = text.split("|")[0].strip()
            item = get_item_by_sku_or_id(key)
            if not item:
                details.delete("1.0", tk.END); details.insert(tk.END, "Item not found"); return
            out = []
            out.append(f"ID: {item['id']}")
            out.append(f"SKU: {item['sku']}")
            out.append(f"Name: {item['name']}")
            out.append(f"Category ID: {item['category_id']}")
            out.append(f"Supplier ID: {item['supplier_id']}")
            out.append(f"Unit price: {item['unit_price']}")
            out.append(f"Quantity: {item['quantity']}")
            out.append(f"Min quantity: {item['min_quantity']}")
            out.append(f"Notes: {item['notes']}")
            details.delete("1.0", tk.END); details.insert(tk.END, "\n".join(out))

        listbox.bind("<<ListboxSelect>>", show_selected)

        # Actions depending on role
        role = self.current_user['role']

        def adjust_stock():
            sel = listbox.curselection()
            if not sel: messagebox.showinfo("Select", "Select an item first"); return
            text = listbox.get(sel[0]); key = text.split("|")[0].strip()
            item = get_item_by_sku_or_id(key)
            if not item: return
            try:
                change = int(simpledialog.askstring("Change", "Quantity change (use negative to decrease):", parent=self))
            except Exception:
                messagebox.showerror("Invalid", "Invalid number"); return
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            new_q = item['quantity'] + change
            if new_q < 0:
                messagebox.showerror("Error", "Resulting quantity would be negative"); return
            conn = get_conn(); cur = conn.cursor()
            cur.execute("UPDATE items SET quantity=? WHERE id=?", (new_q, item['id']))
            cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                        (item['id'], change, 'adjust', note, now_str(), self.current_user['id']))
            conn.commit(); conn.close()
            messagebox.showinfo("Updated", f"New quantity: {new_q}")
            refresh_list()

        def add_item():
            sku = simpledialog.askstring("SKU", "SKU:", parent=self)
            if not sku: return
            name = simpledialog.askstring("Name", "Name:", parent=self)
            if not name: return
            try:
                unit_price = float(simpledialog.askstring("Unit price", "Unit price (0):", parent=self) or 0)
            except Exception:
                unit_price = 0.0
            try:
                quantity = int(simpledialog.askstring("Quantity", "Initial quantity (0):", parent=self) or 0)
            except Exception:
                quantity = 0
            try:
                min_q = int(simpledialog.askstring("Min quantity", "Min quantity (0):", parent=self) or 0)
            except Exception:
                min_q = 0
            notes = simpledialog.askstring("Notes", "Notes (optional):", parent=self) or ""
            conn = get_conn(); cur = conn.cursor()
            try:
                cur.execute("INSERT INTO items (sku,name,unit_price,quantity,min_quantity,notes) VALUES (?,?,?,?,?,?)",
                            (sku,name,unit_price,quantity,min_q,notes))
                item_id = cur.lastrowid
                if quantity:
                    cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                                (item_id, quantity, 'init', 'Initial stock', now_str(), self.current_user['id']))
                conn.commit()
                messagebox.showinfo("Added", "Item added.")
                refresh_list()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "SKU must be unique.")
            finally:
                conn.close()

        def edit_item():
            sel = listbox.curselection()
            if not sel: messagebox.showinfo("Select", "Select an item first"); return
            text = listbox.get(sel[0]); key = text.split("|")[0].strip()
            item = get_item_by_sku_or_id(key)
            if not item: return
            name = simpledialog.askstring("Name", "Name:", initialvalue=item['name'], parent=self) or item['name']
            try:
                unit_price = float(simpledialog.askstring("Unit price", "Unit price:", initialvalue=str(item['unit_price']), parent=self) or item['unit_price'])
            except Exception:
                unit_price = item['unit_price']
            try:
                min_q = int(simpledialog.askstring("Min quantity", "Min quantity:", initialvalue=str(item['min_quantity']), parent=self) or item['min_quantity'])
            except Exception:
                min_q = item['min_quantity']
            notes = simpledialog.askstring("Notes", "Notes:", initialvalue=item['notes'] or "", parent=self) or item['notes'] or ""
            conn = get_conn(); cur = conn.cursor()
            cur.execute("UPDATE items SET name=?, unit_price=?, min_quantity=?, notes=? WHERE id=?", (name, unit_price, min_q, notes, item['id']))
            conn.commit(); conn.close()
            messagebox.showinfo("Updated", "Item updated.")
            refresh_list()

        def delete_item():
            sel = listbox.curselection()
            if not sel: messagebox.showinfo("Select", "Select an item first"); return
            text = listbox.get(sel[0]); key = text.split("|")[0].strip()
            item = get_item_by_sku_or_id(key)
            if not item: return
            if messagebox.askyesno("Confirm", f"Delete {item['sku']} - {item['name']}?"):
                conn = get_conn(); cur = conn.cursor()
                cur.execute("DELETE FROM items WHERE id=?", (item['id'],))
                cur.execute("DELETE FROM transactions WHERE item_id=?", (item['id'],))
                conn.commit(); conn.close()
                messagebox.showinfo("Deleted", "Item deleted.")
                refresh_list()

        def low_stock_report():
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT sku,name,quantity,min_quantity FROM items WHERE min_quantity>0 AND quantity<=min_quantity ORDER BY quantity ASC")
            rows = cur.fetchall(); conn.close()
            if not rows:
                messagebox.showinfo("Low stock", "No low-stock items.")
                return
            out = "\n".join(f"{r['sku']} - {r['name']}: {r['quantity']} (min {r['min_quantity']})" for r in rows)
            messagebox.showinfo("Low stock", out)

        def view_history():
            sel = listbox.curselection()
            if sel:
                text = listbox.get(sel[0]); key = text.split("|")[0].strip()
                item = get_item_by_sku_or_id(key)
                if not item: return
                conn = get_conn(); cur = conn.cursor()
                cur.execute('''SELECT t.change,t.type,t.note,t.timestamp,u.username FROM transactions t LEFT JOIN users u ON t.user_id=u.id WHERE t.item_id=? ORDER BY t.timestamp DESC''', (item['id'],))
                rows = cur.fetchall(); conn.close()
                if not rows: messagebox.showinfo("History", "No transactions for this item."); return
                out = "\n".join(f"[{r['timestamp']}] ({r['username']}) {r['change']} ({r['type']}) - {r['note']}" for r in rows)
                messagebox.showinfo("History", out)
            else:
                conn = get_conn(); cur = conn.cursor()
                cur.execute('''SELECT t.timestamp,u.username,i.sku,i.name,t.change,t.type,t.note FROM transactions t LEFT JOIN users u ON t.user_id=u.id LEFT JOIN items i ON t.item_id=i.id ORDER BY t.timestamp DESC LIMIT 200''')
                rows = cur.fetchall(); conn.close()
                if not rows: messagebox.showinfo("History", "No transactions."); return
                out = "\n".join(f"[{r['timestamp']}] ({r['username']}) {r['sku']} {r['name']}: {r['change']} ({r['type']}) - {r['note']}" for r in rows)
                messagebox.showinfo("History", out)

        # Admin-only features: user management, categories, suppliers, item CRUD
        if role == "admin":
            ttk.Button(action_frame, text="Add Item", command=add_item).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Edit Item", command=edit_item).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Delete Item", command=delete_item).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Adjust Stock", command=adjust_stock).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Low Stock Report", command=low_stock_report).pack(side="left", padx=4)
            ttk.Button(action_frame, text="View History", command=view_history).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Users", command=self.user_management).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Categories", command=self.categories_management).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Suppliers", command=self.suppliers_management).pack(side="left", padx=4)
        else:
            # clerk or other role: limited buttons
            ttk.Button(action_frame, text="Adjust Stock", command=adjust_stock).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Low Stock Report", command=low_stock_report).pack(side="left", padx=4)
            ttk.Button(action_frame, text="View History", command=view_history).pack(side="left", padx=4)

        # refresh button
        ttk.Button(right, text="Refresh List", command=refresh_list).pack(pady=4)

    # ---------- Management dialogs ----------
    def user_management(self):
        win = tk.Toplevel(self); win.title("Users"); win.geometry("400x300")
        tree = ttk.Treeview(win, columns=("id","username","role"), show="headings"); tree.pack(fill="both", expand=True)
        for c in ("id","username","role"): tree.heading(c, text=c)
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT id,username,role FROM users ORDER BY username"); rows = cur.fetchall(); conn.close()
            for r in rows: tree.insert("", tk.END, values=(r['id'], r['username'], r['role']))
        def add_user():
            username = simpledialog.askstring("Username","Username:", parent=win)
            if not username: return
            password = simpledialog.askstring("Password","Password:", parent=win)
            if not password: return
            role = simpledialog.askstring("Role","Role (admin/clerk):", parent=win) or "clerk"
            conn = get_conn(); cur = conn.cursor()
            try:
                cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)", (username, hash_password(password), role))
                conn.commit(); messagebox.showinfo("Added","User added"); refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                conn.close()
        def delete_user():
            sel = tree.selection()
            if not sel: return
            uid = tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Confirm","Delete user?"):
                conn=get_conn();cur=conn.cursor();cur.execute("DELETE FROM users WHERE id=?", (uid,));conn.commit();conn.close();refresh()
        ttk.Button(win, text="Add", command=add_user).pack(side="left", padx=4, pady=4)
        ttk.Button(win, text="Delete", command=delete_user).pack(side="left", padx=4, pady=4)
        ttk.Button(win, text="Close", command=win.destroy).pack(side="right", padx=4, pady=4)
        refresh()

    def categories_management(self):
        win = tk.Toplevel(self); win.title("Categories"); win.geometry("400x300")
        tree = ttk.Treeview(win, columns=("id","name"), show="headings"); tree.pack(fill="both", expand=True)
        for c in ("id","name"): tree.heading(c, text=c)
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            conn = get_conn(); cur = conn.cursor(); cur.execute("SELECT id,name FROM categories ORDER BY name"); rows = cur.fetchall(); conn.close()
            for r in rows: tree.insert("", tk.END, values=(r['id'], r['name']))
        def add_cat():
            name = simpledialog.askstring("Name","Category name:", parent=win)
            if not name: return
            conn=get_conn();cur=conn.cursor()
            try: cur.execute("INSERT INTO categories (name) VALUES (?)", (name,)); conn.commit(); refresh()
            except sqlite3.IntegrityError: messagebox.showerror("Error","Category exists")
            finally: conn.close()
        def delete_cat():
            sel = tree.selection()
            if not sel: return
            cid = tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Confirm","Delete category?"): conn=get_conn();cur=conn.cursor();cur.execute("DELETE FROM categories WHERE id=?", (cid,));conn.commit();conn.close();refresh()
        ttk.Button(win, text="Add", command=add_cat).pack(side="left", padx=4, pady=4)
        ttk.Button(win, text="Delete", command=delete_cat).pack(side="left", padx=4, pady=4)
        ttk.Button(win, text="Close", command=win.destroy).pack(side="right", padx=4, pady=4)
        refresh()

    def suppliers_management(self):
        win = tk.Toplevel(self); win.title("Suppliers"); win.geometry("500x350")
        tree = ttk.Treeview(win, columns=("id","name","contact"), show="headings"); tree.pack(fill="both", expand=True)
        for c in ("id","name","contact"): tree.heading(c, text=c)
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            conn=get_conn();cur=conn.cursor();cur.execute("SELECT id,name,contact FROM suppliers ORDER BY name"); rows=cur.fetchall(); conn.close()
            for r in rows: tree.insert("", tk.END, values=(r['id'], r['name'], r['contact']))
        def add_sup():
            name = simpledialog.askstring("Name","Supplier name:", parent=win)
            if not name: return
            contact = simpledialog.askstring("Contact","Contact details:", parent=win) or ""
            conn=get_conn();cur=conn.cursor(); cur.execute("INSERT INTO suppliers (name,contact) VALUES (?,?)", (name,contact)); conn.commit(); conn.close(); refresh()
        def delete_sup():
            sel = tree.selection()
            if not sel: return
            sid = tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Confirm","Delete supplier?"): conn=get_conn();cur=conn.cursor();cur.execute("DELETE FROM suppliers WHERE id=?", (sid,));conn.commit();conn.close();refresh()
        ttk.Button(win, text="Add", command=add_sup).pack(side="left", padx=4, pady=4)
        ttk.Button(win, text="Delete", command=delete_sup).pack(side="left", padx=4, pady=4)
        ttk.Button(win, text="Close", command=win.destroy).pack(side="right", padx=4, pady=4)
        refresh()

    def logout(self):
        self.current_user = None
        self.create_login_screen()

# ---------- Start ----------
def main():
    init_db()
    app = InventoryApp()
    app.mainloop()

if __name__ == "__main__":
    main()
