#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
from collections import defaultdict

# --- Database Setup ---

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def now_str():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, role TEXT,
        name TEXT, phone TEXT, email TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY, name TEXT UNIQUE, description TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY, name TEXT, contact TEXT, email TEXT, address TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY, sku TEXT UNIQUE, name TEXT, category_id INTEGER, supplier_id INTEGER,
        unit_price REAL DEFAULT 0, quantity INTEGER DEFAULT 0, min_quantity INTEGER DEFAULT 0, notes TEXT,
        created_at TEXT, last_updated TEXT,
        FOREIGN KEY(category_id) REFERENCES categories(id), FOREIGN KEY(supplier_id) REFERENCES suppliers(id))''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY, item_id INTEGER, change INTEGER, type TEXT, note TEXT, timestamp TEXT, user_id INTEGER,
        FOREIGN KEY(item_id) REFERENCES items(id), FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT,
        created_at TEXT, notes TEXT, total_orders INTEGER DEFAULT 0, total_spent REAL DEFAULT 0)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, order_number TEXT UNIQUE, customer_id INTEGER, 
        total_amount REAL, status TEXT, created_at TEXT, user_id INTEGER,
        notes TEXT, completed_at TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY, order_id INTEGER, item_id INTEGER, 
        quantity INTEGER, unit_price REAL, subtotal REAL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(item_id) REFERENCES items(id))''')
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        # Default credentials
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
    
    conn.close()

# --- Helper Functions ---

def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def list_items(q="%"):
    conn = get_conn()
    cur = conn.cursor()
    qlike = f"%{q}%"
    cur.execute("""SELECT i.*, c.name as category, s.name as supplier FROM items i 
                   LEFT JOIN categories c ON i.category_id=c.id 
                   LEFT JOIN suppliers s ON i.supplier_id=s.id 
                   WHERE i.sku LIKE ? OR i.name LIKE ? ORDER BY i.name""", (qlike, qlike))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_item_by_sku_or_id(key):
    conn = get_conn()
    cur = conn.cursor()
    if str(key).isdigit():
        cur.execute("""SELECT i.*, c.name as category, s.name as supplier FROM items i 
                       LEFT JOIN categories c ON i.category_id=c.id 
                       LEFT JOIN suppliers s ON i.supplier_id=s.id 
                       WHERE i.id=?""", (int(key),))
    else:
        cur.execute("""SELECT i.*, c.name as category, s.name as supplier FROM items i 
                       LEFT JOIN categories c ON i.category_id=c.id 
                       LEFT JOIN suppliers s ON i.supplier_id=s.id 
                       WHERE i.sku=?""", (key,))
    row = cur.fetchone()
    conn.close()
    return row

def list_categories():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def list_suppliers():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM suppliers ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def generate_order_number():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD-{timestamp}"

# --- Main Application ---

class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V.A.V.H Studio - Inventory Management System")
        self.geometry("1200x800")
        self.resizable(True, True)
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", foreground="black")
        self.style.configure("TButton", background="#0078D7", foreground="white", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#005a9e")])
        self.style.configure("Success.TButton", background="#28A745", foreground="white")
        self.style.configure("Danger.TButton", background="#DC3545", foreground="white")
        
        self.current_user = None
        self.create_login_screen()

    def create_login_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ttk.Frame(self, padding=40)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ttk.Label(frame, text="V.A.V.H Studio", font=("Arial", 24, "bold"), 
                  foreground="#0078D7").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Inventory Login", font=("Arial", 12)).grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        ttk.Label(frame, text="Username:").grid(row=2, column=0, sticky="e", pady=5, padx=5)
        user_entry = ttk.Entry(frame, width=25)
        user_entry.grid(row=2, column=1, sticky="w", pady=5)
        user_entry.focus()
        
        ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky="e", pady=5, padx=5)
        pass_entry = ttk.Entry(frame, show="*", width=25)
        pass_entry.grid(row=3, column=1, sticky="w", pady=5)

        error_label = ttk.Label(frame, text="", foreground="red")
        error_label.grid(row=4, column=0, columnspan=2, pady=5)

        def do_login(event=None):
            username = user_entry.get().strip()
            password = pass_entry.get().strip()
            
            if not username or not password:
                error_label.config(text="Enter username and password")
                return
            
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                error_label.config(text="Invalid credentials")
                pass_entry.delete(0, tk.END)
                return
            
            self.current_user = dict(user)
            self.create_main_ui()

        ttk.Button(frame, text="Login", command=do_login).grid(row=5, column=0, columnspan=2, pady=20, sticky="ew")
        ttk.Label(frame, text="Default: admin/admin", font=("Arial", 8), foreground="#999").grid(row=6, column=0, columnspan=2)
        
        self.bind("<Return>", do_login)

    def create_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self.unbind("<Return>")
        
        # Top Bar
        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(top_bar, text=f"User: {self.current_user['username']} ({self.current_user['role']})", 
                  font=("Arial", 11, "bold")).pack(side="left")
        
        if self.current_user["role"] == "admin":
            ttk.Button(top_bar, text="Create User", command=self.create_user).pack(side="left", padx=10)
        
        ttk.Button(top_bar, text="Logout", style="Danger.TButton", command=self.logout).pack(side="right")
        ttk.Button(top_bar, text="My Profile", command=self.show_profile).pack(side="right", padx=5)

        # Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.create_dashboard_tab()
        self.create_inventory_tab()
        self.create_orders_tab()
        self.create_customers_tab()
        self.create_manage_tab()
        self.create_reports_tab()

    def logout(self):
        self.current_user = None
        self.create_login_screen()

    def create_user(self):
        # Simple dialog to create a new user (Admin only)
        win = tk.Toplevel(self)
        win.title("Create User")
        win.geometry("300x250")
        
        ttk.Label(win, text="Username:").pack(pady=5)
        u_entry = ttk.Entry(win)
        u_entry.pack()
        
        ttk.Label(win, text="Password:").pack(pady=5)
        p_entry = ttk.Entry(win, show="*")
        p_entry.pack()
        
        ttk.Label(win, text="Role:").pack(pady=5)
        role_combo = ttk.Combobox(win, values=["admin", "clerk"], state="readonly")
        role_combo.set("clerk")
        role_combo.pack()
        
        def save():
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                            (u_entry.get(), hash_password(p_entry.get()), role_combo.get()))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "User created!")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))
                
        ttk.Button(win, text="Create", command=save).pack(pady=20)

    def show_profile(self):
        messagebox.showinfo("Profile", f"Username: {self.current_user['username']}\nRole: {self.current_user['role']}")

    # --- Dashboard Tab ---
    def create_dashboard_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📊 Dashboard")
        
        ttk.Label(frame, text="Overview", font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=10)
        
        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill="x", padx=10)
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Gather Stats
        cur.execute("SELECT COUNT(*), SUM(quantity) FROM items")
        items_d = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM items WHERE min_quantity > 0 AND quantity <= min_quantity")
        low_stock = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status='Completed'")
        sales_d = cur.fetchone()
        
        conn.close()
        
        stats = [
            ("Items", f"{items_d[0]} ({items_d[1] or 0} qty)"),
            ("Low Stock", str(low_stock), "red" if low_stock > 0 else "black"),
            ("Sales", f"${sales_d[1] or 0:.2f} ({sales_d[0]} orders)")
        ]
        
        for i, (label, val, *fmt) in enumerate(stats):
            f = ttk.LabelFrame(stats_frame, text=label, padding=10)
            f.pack(side="left", expand=True, fill="both", padx=5)
            fg = fmt[0] if fmt else "black"
            ttk.Label(f, text=val, font=("Arial", 18, "bold"), foreground=fg).pack()

        # Recent Activity
        ttk.Label(frame, text="Recent Transactions", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(20, 5))
        
        text_area = scrolledtext.ScrolledText(frame, height=15)
        text_area.pack(fill="both", expand=True, padx=10, pady=5)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT t.timestamp, u.username, i.name, t.change, t.type 
                       FROM transactions t 
                       JOIN users u ON t.user_id=u.id 
                       JOIN items i ON t.item_id=i.id 
                       ORDER BY t.timestamp DESC LIMIT 50""")
        
        for row in cur.fetchall():
            text_area.insert(tk.END, f"[{row['timestamp']}] {row['username']}: {row['type'].upper()} {row['name']} ({row['change']:+d})\n")
        
        text_area.config(state="disabled")
        conn.close()
        
        ttk.Button(frame, text="Refresh", command=lambda: [frame.destroy(), self.create_dashboard_tab()]).pack(pady=10)

    # --- Inventory Tab ---
    def create_inventory_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📦 Inventory")
        
        # Split: List vs Details
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)
        
        left_frame = ttk.Frame(paned, padding=5)
        right_frame = ttk.Frame(paned, padding=5)
        paned.add(left_frame, weight=1)
        paned.add(right_frame, weight=2)
        
        # Search
        search_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=search_var).pack(fill="x", pady=5)
        
        listbox = tk.Listbox(left_frame)
        listbox.pack(fill="both", expand=True)
        
        def refresh_list(e=None):
            listbox.delete(0, tk.END)
            items = list_items(search_var.get())
            for i in items:
                alert = "⚠️" if i['min_quantity'] > 0 and i['quantity'] <= i['min_quantity'] else ""
                listbox.insert(tk.END, f"{i['sku']} | {i['name']} {alert}")
        
        search_var.trace("w", lambda *args: refresh_list())
        refresh_list()
        
        # Details & Actions
        details_text = tk.Text(right_frame, height=15, state="disabled")
        details_text.pack(fill="x", pady=5)
        
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill="x", pady=5)
        
        def show_details(e):
            sel = listbox.curselection()
            if not sel: return
            sku = listbox.get(sel[0]).split(" | ")[0]
            item = get_item_by_sku_or_id(sku)
            
            details_text.config(state="normal")
            details_text.delete("1.0", tk.END)
            
            info = f"""
SKU: {item['sku']}
Name: {item['name']}
Category: {item['category']}
Supplier: {item['supplier']}
Price: ${item['unit_price']:.2f}
Quantity: {item['quantity']} (Min: {item['min_quantity']})
Notes: {item['notes']}
"""
            details_text.insert(tk.END, info)
            details_text.config(state="disabled")
            
        listbox.bind("<<ListboxSelect>>", show_details)
        
        def adjust_stock():
            sel = listbox.curselection()
            if not sel: return
            sku = listbox.get(sel[0]).split(" | ")[0]
            item = get_item_by_sku_or_id(sku)
            
            qty = simpledialog.askinteger("Adjust", f"Current: {item['quantity']}\nEnter change (+/-):")
            if qty is not None and qty != 0:
                note = simpledialog.askstring("Note", "Reason:") or "Manual adjustment"
                conn = get_conn()
                cur = conn.cursor()
                new_q = item['quantity'] + qty
                cur.execute("UPDATE items SET quantity=? WHERE id=?", (new_q, item['id']))
                cur.execute("INSERT INTO transactions (item_id, change, type, note, timestamp, user_id) VALUES (?,?,?,?,?,?)",
                            (item['id'], qty, "adjust", note, now_str(), self.current_user['id']))
                conn.commit()
                conn.close()
                refresh_list()
                show_details(None)

        def add_item_window():
            win = tk.Toplevel(self)
            win.title("Add Item")
            
            fields = ["SKU", "Name", "Unit Price", "Quantity", "Min Qty", "Notes"]
            entries = {}
            
            for i, f in enumerate(fields):
                ttk.Label(win, text=f).grid(row=i, column=0, padx=5, pady=5)
                e = ttk.Entry(win)
                e.grid(row=i, column=1, padx=5, pady=5)
                entries[f] = e
            
            ttk.Label(win, text="Category").grid(row=6, column=0)
            cats = list_categories()
            cat_cb = ttk.Combobox(win, values=[c['name'] for c in cats])
            cat_cb.grid(row=6, column=1)
            
            ttk.Label(win, text="Supplier").grid(row=7, column=0)
            sups = list_suppliers()
            sup_cb = ttk.Combobox(win, values=[s['name'] for s in sups])
            sup_cb.grid(row=7, column=1)
            
            def save_item():
                try:
                    c_id = next((c['id'] for c in cats if c['name'] == cat_cb.get()), None)
                    s_id = next((s['id'] for s in sups if s['name'] == sup_cb.get()), None)
                    
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""INSERT INTO items (sku, name, category_id, supplier_id, unit_price, quantity, min_quantity, notes, created_at)
                                   VALUES (?,?,?,?,?,?,?,?,?)""",
                                   (entries["SKU"].get(), entries["Name"].get(), c_id, s_id,
                                    float(entries["Unit Price"].get() or 0), int(entries["Quantity"].get() or 0),
                                    int(entries["Min Qty"].get() or 0), entries["Notes"].get(), now_str()))
                    conn.commit()
                    conn.close()
                    refresh_list()
                    win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
            
            ttk.Button(win, text="Save", command=save_item).grid(row=8, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Adjust Stock", command=adjust_stock).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Add New Item", command=add_item_window).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=refresh_list).pack(side="left", padx=5)

    # --- Orders Tab ---
    def create_orders_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🛒 Orders")
        
        # Order List
        columns = ("Order #", "Customer", "Amount", "Status", "Date")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for c in columns: tree.heading(c, text=c)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        def refresh_orders():
            for i in tree.get_children(): tree.delete(i)
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""SELECT o.*, c.name as cname FROM orders o 
                           LEFT JOIN customers c ON o.customer_id=c.id 
                           ORDER BY o.created_at DESC LIMIT 50""")
            for row in cur.fetchall():
                tree.insert("", "end", values=(row['order_number'], row['cname'], 
                                               f"${row['total_amount']:.2f}", row['status'], row['created_at']))
            conn.close()
        
        refresh_orders()
        
        # New Order Window
        def new_order_window():
            win = tk.Toplevel(self)
            win.title("New Order")
            win.geometry("900x600")
            
            # Left: Customer & Items selection
            left = ttk.Frame(win, padding=10)
            left.pack(side="left", fill="both", expand=True)
            
            # Customer Selection
            cust_frame = ttk.LabelFrame(left, text="Customer")
            cust_frame.pack(fill="x", pady=5)
            
            customers = []
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM customers")
            customers = cur.fetchall()
            conn.close()
            
            cust_cb = ttk.Combobox(cust_frame, values=[f"{c['id']} - {c['name']}" for c in customers])
            cust_cb.pack(fill="x", padx=5, pady=5)
            
            # Item Selection
            item_frame = ttk.LabelFrame(left, text="Add Item")
            item_frame.pack(fill="x", pady=5)
            
            search_var = tk.StringVar()
            ttk.Entry(item_frame, textvariable=search_var).pack(fill="x", padx=5, pady=5)
            
            item_list = tk.Listbox(item_list_frame := ttk.Frame(item_frame), height=10)
            item_list.pack(fill="x", side="left", expand=True)
            scrollbar = ttk.Scrollbar(item_list_frame, command=item_list.yview)
            scrollbar.pack(side="right", fill="y")
            item_list.config(yscrollcommand=scrollbar.set)
            item_list_frame.pack(fill="x", padx=5)

            def update_items(*args):
                item_list.delete(0, tk.END)
                rows = list_items(search_var.get())
                for r in rows:
                    item_list.insert(tk.END, f"{r['sku']} | {r['name']} | ${r['unit_price']} | Stock: {r['quantity']}")
            
            search_var.trace("w", update_items)
            update_items()
            
            qty_entry = ttk.Entry(item_frame, width=10)
            qty_entry.insert(0, "1")
            qty_entry.pack(pady=5)
            
            # Right: Cart
            right = ttk.Frame(win, padding=10)
            right.pack(side="right", fill="both", expand=True)
            
            cart_tree = ttk.Treeview(right, columns=("SKU", "Name", "Qty", "Subtotal"), show="headings")
            for c in ["SKU", "Name", "Qty", "Subtotal"]: cart_tree.heading(c, text=c)
            cart_tree.pack(fill="both", expand=True)
            
            total_lbl = ttk.Label(right, text="Total: $0.00", font=("Arial", 14, "bold"))
            total_lbl.pack(pady=10)
            
            cart = [] # List of dicts
            
            def add_to_cart():
                sel = item_list.curselection()
                if not sel: return
                txt = item_list.get(sel[0])
                sku = txt.split("|")[0].strip()
                item = get_item_by_sku_or_id(sku)
                
                try:
                    q = int(qty_entry.get())
                    if q > item['quantity']:
                        messagebox.showwarning("Stock", "Not enough stock!")
                        return
                except: return
                
                subtotal = q * item['unit_price']
                cart.append({"id": item['id'], "sku": item['sku'], "name": item['name'], 
                             "qty": q, "price": item['unit_price'], "subtotal": subtotal})
                
                refresh_cart()
            
            def refresh_cart():
                for i in cart_tree.get_children(): cart_tree.delete(i)
                total = 0
                for c in cart:
                    cart_tree.insert("", "end", values=(c['sku'], c['name'], c['qty'], f"${c['subtotal']:.2f}"))
                    total += c['subtotal']
                total_lbl.config(text=f"Total: ${total:.2f}")
                
            ttk.Button(item_frame, text="Add to Order", command=add_to_cart).pack(pady=5)
            
            def checkout():
                if not cust_cb.get():
                    messagebox.showerror("Error", "Select Customer")
                    return
                if not cart:
                    messagebox.showerror("Error", "Cart empty")
                    return
                
                cust_id = int(cust_cb.get().split(" - ")[0])
                total = sum(c['subtotal'] for c in cart)
                
                conn = get_conn()
                cur = conn.cursor()
                
                try:
                    # Create Order
                    order_num = generate_order_number()
                    cur.execute("""INSERT INTO orders (order_number, customer_id, total_amount, status, created_at, user_id, completed_at)
                                   VALUES (?, ?, ?, 'Completed', ?, ?, ?)""",
                                   (order_num, cust_id, total, now_str(), self.current_user['id'], now_str()))
                    order_id = cur.lastrowid
                    
                    # Add Items and Update Stock
                    for item in cart:
                        cur.execute("""INSERT INTO order_items (order_id, item_id, quantity, unit_price, subtotal)
                                       VALUES (?,?,?,?,?)""",
                                       (order_id, item['id'], item['qty'], item['price'], item['subtotal']))
                        
                        # Deduct Stock
                        cur.execute("UPDATE items SET quantity = quantity - ? WHERE id=?", (item['qty'], item['id']))
                        
                        # Log Transaction
                        cur.execute("""INSERT INTO transactions (item_id, change, type, note, timestamp, user_id)
                                       VALUES (?, ?, 'sale', ?, ?, ?)""",
                                       (item['id'], -item['qty'], f"Order {order_num}", now_str(), self.current_user['id']))
                        
                    conn.commit()
                    messagebox.showinfo("Success", f"Order {order_num} Created!")
                    win.destroy()
                    refresh_orders()
                    
                except Exception as e:
                    conn.rollback()
                    messagebox.showerror("Error", str(e))
                finally:
                    conn.close()

            ttk.Button(right, text="Checkout / Complete Order", style="Success.TButton", command=checkout).pack(fill="x", pady=10)

        
        btn_bar = ttk.Frame(frame)
        btn_bar.pack(fill="x", padx=10)
        ttk.Button(btn_bar, text="New Order", command=new_order_window).pack(side="left")
        ttk.Button(btn_bar, text="Refresh", command=refresh_orders).pack(side="left", padx=5)

    # --- Customers Tab ---
    def create_customers_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="👥 Customers")
        
        columns = ("ID", "Name", "Phone", "Email")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for c in columns: tree.heading(c, text=c)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        def refresh_customers():
            for i in tree.get_children(): tree.delete(i)
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM customers")
            for r in cur.fetchall():
                tree.insert("", "end", values=(r['id'], r['name'], r['phone'], r['email']))
            conn.close()
        
        refresh_customers()
        
        def add_customer():
            name = simpledialog.askstring("New Customer", "Name:")
            if name:
                phone = simpledialog.askstring("New Customer", "Phone:")
                email = simpledialog.askstring("New Customer", "Email:")
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("INSERT INTO customers (name, phone, email, created_at) VALUES (?,?,?,?)",
                            (name, phone, email, now_str()))
                conn.commit()
                conn.close()
                refresh_customers()
        
        ttk.Button(frame, text="Add Customer", command=add_customer).pack(pady=5)
        
    # --- Manage Tab ---
    def create_manage_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⚙️ Manage")
        
        # Categories
        cat_frame = ttk.LabelFrame(frame, text="Categories")
        cat_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        cat_list = tk.Listbox(cat_frame)
        cat_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        def refresh_cats():
            cat_list.delete(0, tk.END)
            for c in list_categories(): cat_list.insert(tk.END, c['name'])
            
        refresh_cats()
        
        def add_cat():
            name = simpledialog.askstring("Category", "Name:")
            if name:
                try:
                    conn = get_conn()
                    conn.cursor().execute("INSERT INTO categories (name) VALUES (?)", (name,))
                    conn.commit()
                    conn.close()
                    refresh_cats()
                except: messagebox.showerror("Error", "Category likely exists")

        ttk.Button(cat_frame, text="Add Category", command=add_cat).pack(pady=5)
        
        # Suppliers
        sup_frame = ttk.LabelFrame(frame, text="Suppliers")
        sup_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        sup_list = tk.Listbox(sup_frame)
        sup_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        def refresh_sups():
            sup_list.delete(0, tk.END)
            for s in list_suppliers(): sup_list.insert(tk.END, s['name'])
        
        refresh_sups()
        
        def add_sup():
            name = simpledialog.askstring("Supplier", "Name:")
            if name:
                conn = get_conn()
                conn.cursor().execute("INSERT INTO suppliers (name) VALUES (?)", (name,))
                conn.commit()
                conn.close()
                refresh_sups()
                
        ttk.Button(sup_frame, text="Add Supplier", command=add_sup).pack(pady=5)

    # --- Reports Tab ---
    def create_reports_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📈 Reports")
        
        text_area = scrolledtext.ScrolledText(frame)
        text_area.pack(fill="both", expand=True, padx=10, pady=10)
        
        def generate_report():
            conn = get_conn()
            cur = conn.cursor()
            
            report = "--- SALES REPORT ---\n\n"
            
            # Total Sales
            cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status='Completed'")
            data = cur.fetchone()
            report += f"Total Completed Orders: {data[0]}\n"
            report += f"Total Revenue: ${data[1] or 0:.2f}\n\n"
            
            # Top Items
            report += "--- TOP SELLING ITEMS ---\n"
            cur.execute("""SELECT i.name, SUM(oi.quantity) as sold 
                           FROM order_items oi 
                           JOIN items i ON oi.item_id=i.id 
                           GROUP BY i.id ORDER BY sold DESC LIMIT 10""")
            for r in cur.fetchall():
                report += f"{r['name']}: {r['sold']} units\n"
                
            text_area.delete("1.0", tk.END)
            text_area.insert(tk.END, report)
            conn.close()
            
        ttk.Button(frame, text="Generate General Report", command=generate_report).pack(pady=5)

if __name__ == "__main__":
    init_db()
    app = InventoryApp()
    app.mainloop()