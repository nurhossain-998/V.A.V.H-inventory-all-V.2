#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from collections import defaultdict
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def now_str():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

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
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
    
    conn.close()

def validate_email(email):
    """Basic email validation"""
    if not email:
        return True
    return '@' in email and '.' in email.split('@')[1]

def validate_phone(phone):
    """Basic phone validation"""
    if not phone:
        return True
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) >= 10

def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_user_field(user_id, field, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()

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
        cur.execute("SELECT * FROM items WHERE id=?", (int(key),))
    else:
        cur.execute("SELECT * FROM items WHERE sku=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row

def generate_order_number():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD-{timestamp}"

def search_customer(query):
    conn = get_conn()
    cur = conn.cursor()
    qlike = f"%{query}%"
    cur.execute("""SELECT * FROM customers 
                   WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                   ORDER BY name""", (qlike, qlike, qlike))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    return row

def list_orders(status_filter=None, limit=100):
    conn = get_conn()
    cur = conn.cursor()
    if status_filter:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       WHERE o.status=?
                       ORDER BY o.created_at DESC""", (status_filter,))
    else:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       ORDER BY o.created_at DESC LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_order_details(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT oi.*, i.sku, i.name as item_name
                   FROM order_items oi
                   LEFT JOIN items i ON oi.item_id=i.id
                   WHERE oi.order_id=?""", (order_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

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

def get_sales_report(start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if start_date and end_date:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders 
                       WHERE status='Completed' AND created_at BETWEEN ? AND ?""", 
                    (start_date, end_date))
    else:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders WHERE status='Completed'""")
    
    report = cur.fetchone()
    conn.close()
    return report

def get_top_selling_items(limit=10):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT i.name, i.sku, SUM(oi.quantity) as total_sold, 
                   SUM(oi.subtotal) as total_revenue
                   FROM order_items oi
                   JOIN items i ON oi.item_id = i.id
                   JOIN orders o ON oi.order_id = o.id
                   WHERE o.status = 'Completed'
                   GROUP BY i.id
                   ORDER BY total_sold DESC
                   LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V.A.V.H Studio - Advanced Inventory & Order Management")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.configure(bg="white")
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="white")
        self.style.configure("TLabel", background="white", foreground="black")
        self.style.configure("TButton", background="#0078D7", foreground="white", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#3399FF")])
        self.style.configure("Success.TButton", background="#28A745", foreground="white")
        self.style.configure("Danger.TButton", background="#DC3545", foreground="white")
        
        self.current_user = None
        self.create_login_screen()

    def create_login_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="V.A.V.H Studio", font=("Arial", 24, "bold"), 
                 foreground="#0078D7").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Advanced Inventory Management", font=("Arial", 12), 
                 foreground="#666").grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
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
                error_label.config(text="Please enter both username and password")
                return
            
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                error_label.config(text="Incorrect username or password")
                pass_entry.delete(0, tk.END)
                return
            
            self.current_user = dict(user)
            self.create_main_ui()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Login", command=do_login).pack()
        
        ttk.Label(frame, text="Default: admin/admin or clerk/clerk", 
                 font=("Arial", 9), foreground="#999").grid(row=6, column=0, columnspan=2)
        
        self.bind("<Return>", do_login)

    def create_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        
        # Top bar
        top = ttk.Frame(self, style="TFrame")
        top.pack(fill="x", padx=10, pady=5)
        
        user_frame = ttk.Frame(top)
        user_frame.pack(side="left")
        ttk.Label(user_frame, text=f"👤 {self.current_user['username']}", 
                 foreground="#0078D7", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ttk.Label(user_frame, text=f"({self.current_user['role']})", 
                 foreground="#666", font=("Arial", 9)).pack(side="left")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side="right")
        
        if self.current_user["role"] == "admin":
            ttk.Button(btn_frame, text="Create User", command=self.create_user).pack(side="left", padx=2)
        
        ttk.Button(btn_frame, text="Profile", command=self.show_profile).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Logout", command=self.logout, 
                  style="Danger.TButton").pack(side="left", padx=2)

        # Notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="📊 Dashboard")
        self.create_dashboard_tab(dashboard_frame)
        
        # Inventory tab
        inventory_frame = ttk.Frame(notebook)
        notebook.add(inventory_frame, text="📦 Inventory")
        self.create_inventory_tab(inventory_frame)
        
        # Orders tab
        orders_frame = ttk.Frame(notebook)
        notebook.add(orders_frame, text="🛒 Orders")
        self.create_orders_tab(orders_frame)
        
        # Customers tab
        customers_frame = ttk.Frame(notebook)
        notebook.add(customers_frame, text="👥 Customers")
        self.create_customers_tab(customers_frame)
        
        # Categories & Suppliers tab
        manage_frame = ttk.Frame(notebook)
        notebook.add(manage_frame, text="⚙️ Manage")
        self.create_manage_tab(manage_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(notebook)
        notebook.add(reports_frame, text="📈 Reports")
        self.create_reports_tab(reports_frame)

    def create_dashboard_tab(self, parent):
        # Header
        header = ttk.Frame(parent, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Dashboard Overview", 
                 font=("Arial", 16, "bold"), foreground="#0078D7").pack(anchor="w")
        ttk.Label(header, text=f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                 font=("Arial", 9), foreground="#666").pack(anchor="w")
        
        # Stats cards
        stats_frame = ttk.Frame(parent, padding=10)
        stats_frame.pack(fill="x")
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Total items
        cur.execute("SELECT COUNT(*), SUM(quantity) FROM items")
        items_data = cur.fetchone()
        
        # Low stock items
        cur.execute("SELECT COUNT(*) FROM items WHERE min_quantity > 0 AND quantity <= min_quantity")
        low_stock = cur.fetchone()[0]
        
        # Total orders
        cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status='Completed'")
        orders_data = cur.fetchone()
        
        # Pending orders
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
        pending = cur.fetchone()[0]
        
        # Total customers
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
        
        conn.close()
        
        # Create stat cards
        cards = [
            ("Total Items", items_data[0], f"{items_data[1] or 0} units in stock", "#0078D7"),
            ("Low Stock Alerts", low_stock, "Items need reorder", "#DC3545" if low_stock > 0 else "#28A745"),
            ("Completed Orders", orders_data[0], f"${orders_data[1] or 0:.2f} revenue", "#28A745"),
            ("Pending Orders", pending, "Awaiting processing", "#FFC107" if pending > 0 else "#28A745"),
            ("Total Customers", customers, "In database", "#17A2B8"),
        ]
        
        for i, (title, value, subtitle, color) in enumerate(cards):
            card = ttk.LabelFrame(stats_frame, text=title, padding=15)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="ew")
            
            ttk.Label(card, text=str(value), font=("Arial", 24, "bold"), 
                     foreground=color).pack()
            ttk.Label(card, text=subtitle, font=("Arial", 9), 
                     foreground="#666").pack()
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        
        # Recent activity
        activity_frame = ttk.LabelFrame(parent, text="Recent Activity", padding=10)
        activity_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text = scrolledtext.ScrolledText(activity_frame, height=10, wrap=tk.WORD)
        text.pack(fill="both", expand=True)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT t.timestamp, u.username, i.name, t.change, t.type, t.note
                      FROM transactions t
                      LEFT JOIN users u ON t.user_id = u.id
                      LEFT JOIN items i ON t.item_id = i.id
                      ORDER BY t.timestamp DESC LIMIT 20""")
        transactions = cur.fetchall()
        conn.close()
        
        for t in transactions:
            text.insert(tk.END, f"[{t['timestamp']}] {t['username']}: {t['name']} - {t['change']:+d} ({t['type']}) - {t['note']}\n")
        
        text.config(state="disabled")
        
        # Quick actions
        actions_frame = ttk.Frame(parent, padding=10)
        actions_frame.pack(fill="x")
        
        ttk.Button(actions_frame, text="🔄 Refresh Dashboard", 
                  command=lambda: self.create_dashboard_tab(parent)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="📊 View Full Reports", 
                  command=lambda: self.focus_tab(5)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="⚠️ View Low Stock", 
                  command=self.show_low_stock_detailed).pack(side="left", padx=5)

    def focus_tab(self, index):
        """Helper to switch to a specific tab"""
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.select(index)
                break

    def show_low_stock_detailed(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT sku, name, quantity, min_quantity, unit_price 
                      FROM items WHERE min_quantity > 0 AND quantity <= min_quantity 
                      ORDER BY quantity ASC""")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            messagebox.showinfo("Low Stock", "No low-stock items found!")
            return
        
        win = tk.Toplevel(self)
        win.title("Low Stock Report")
        win.geometry("700x400")
        
        columns = ('SKU', 'Name', 'Current', 'Min', 'Unit Price', 'Reorder Cost')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        total_cost = 0
        for row in rows:
            reorder_qty = row['min_quantity'] - row['quantity'] + 5
            cost = reorder_qty * row['unit_price']
            total_cost += cost
            tree.insert('', 'end', values=(
                row['sku'], row['name'], row['quantity'], row['min_quantity'],
                f"${row['unit_price']:.2f}", f"${cost:.2f}"
            ))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(win, text=f"Total Estimated Reorder Cost: ${total_cost:.2f}", 
                 font=("Arial", 12, "bold"), foreground="#DC3545").pack(pady=10)

    def create_inventory_tab(self, parent):
        pan = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pan.pack(fill="both", expand=True)
        
        left = ttk.Frame(pan, width=400)
        right = ttk.Frame(pan)
        pan.add(left, weight=1)
        pan.add(right, weight=2)

        # Search frame
        search_frame = ttk.Frame(left, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="🔍 Search SKU/Name:", font=("Arial", 10, "bold")).pack(anchor="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 10))
        search_entry.pack(fill="x", pady=5)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                           selectbackground="#0078D7", selectforeground="white",
                           font=("Arial", 9), yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def refresh_list(event=None):
            q = search_var.get() or "%"
            items = list_items(q)
            listbox.delete(0, tk.END)
            for it in items:
                status = "🔴" if it['min_quantity'] > 0 and it['quantity'] <= it['min_quantity'] else "🟢"
                listbox.insert(tk.END, f"{status} {it['sku']} | {it['name']} | Qty: {it['quantity']}")

        search_entry.bind("<KeyRelease>", lambda e: refresh_list())
        refresh_list()

        # Details panel
        details_frame = ttk.LabelFrame(right, text="Item Details", padding=10)
        details_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        details = tk.Text(details_frame, height=15, bg="white", fg="black", 
                         insertbackground="black", font=("Courier", 10))
        details.pack(fill="both", expand=True)

        def show_selected(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            # Remove emoji and get SKU
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                details.delete("1.0", tk.END)
                details.insert(tk.END, "Item not found")
                return
            
            status = "⚠️ LOW STOCK" if item['min_quantity'] > 0 and item['quantity'] <= item['min_quantity'] else "✓ In Stock"
            
            out = [
                f"{'='*50}",
                f"SKU: {item['sku']}",
                f"Name: {item['name']}",
                f"{'='*50}",
                f"Category: {item.get('category') or 'None'}",
                f"Supplier: {item.get('supplier') or 'None'}",
                f"",
                f"Unit Price: ${item['unit_price']:.2f}",
                f"Quantity: {item['quantity']} {status}",
                f"Min Quantity: {item['min_quantity']}",
                f"Total Value: ${item['unit_price'] * item['quantity']:.2f}",
                f"",
                f"Created: {item.get('created_at') or 'N/A'}",
                f"Last Updated: {item.get('last_updated') or 'N/A'}",
                f"",
                f"Notes: {item['notes'] or 'None'}"
            ]
            details.delete("1.0", tk.END)
            details.insert(tk.END, "\n".join(out))

        listbox.bind("<<ListboxSelect>>", show_selected)

        # Action buttons
        action_frame = ttk.Frame(right, padding=8)
        action_frame.pack(fill="x", padx=8, pady=8)

        def adjust_stock():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            try:
                change_str = simpledialog.askstring("Adjust Stock", 
                    f"Current quantity: {item['quantity']}\nEnter change (negative to decrease):", 
                    parent=self)
                if not change_str:
                    return
                change = int(change_str)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number")
                return
            
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            new_q = item['quantity'] + change
            
            if new_q < 0:
                messagebox.showerror("Error", "Resulting quantity would be negative")
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE items SET quantity=?, last_updated=? WHERE id=?", 
                          (new_q, now_str(), item['id']))
                cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                          (item['id'], change, 'adjust', note, now_str(), self.current_user['id']))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"New quantity: {new_q}")
                refresh_list()
                show_selected()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update stock: {str(e)}")

        def add_item():
            win = tk.Toplevel(self)
            win.title("Add New Item")
            win.geometry("500x600")
            
            # Form fields
            fields_frame = ttk.Frame(win, padding=20)
            fields_frame.pack(fill="both", expand=True)
            
            ttk.Label(fields_frame, text="SKU:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5, padx=5)
            sku_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=sku_var, width=30).grid(row=0, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Name:*", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5, padx=5)
            name_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=name_var, width=30).grid(row=1, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Category:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5, padx=5)
            categories = list_categories()
            cat_#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from collections import defaultdict
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def now_str():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

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
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
    
    conn.close()

def validate_email(email):
    """Basic email validation"""
    if not email:
        return True
    return '@' in email and '.' in email.split('@')[1]

def validate_phone(phone):
    """Basic phone validation"""
    if not phone:
        return True
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) >= 10

def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_user_field(user_id, field, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()

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
        cur.execute("SELECT * FROM items WHERE id=?", (int(key),))
    else:
        cur.execute("SELECT * FROM items WHERE sku=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row

def generate_order_number():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD-{timestamp}"

def search_customer(query):
    conn = get_conn()
    cur = conn.cursor()
    qlike = f"%{query}%"
    cur.execute("""SELECT * FROM customers 
                   WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                   ORDER BY name""", (qlike, qlike, qlike))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    return row

def list_orders(status_filter=None, limit=100):
    conn = get_conn()
    cur = conn.cursor()
    if status_filter:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       WHERE o.status=?
                       ORDER BY o.created_at DESC""", (status_filter,))
    else:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       ORDER BY o.created_at DESC LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_order_details(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT oi.*, i.sku, i.name as item_name
                   FROM order_items oi
                   LEFT JOIN items i ON oi.item_id=i.id
                   WHERE oi.order_id=?""", (order_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

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

def get_sales_report(start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if start_date and end_date:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders 
                       WHERE status='Completed' AND created_at BETWEEN ? AND ?""", 
                    (start_date, end_date))
    else:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders WHERE status='Completed'""")
    
    report = cur.fetchone()
    conn.close()
    return report

def get_top_selling_items(limit=10):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT i.name, i.sku, SUM(oi.quantity) as total_sold, 
                   SUM(oi.subtotal) as total_revenue
                   FROM order_items oi
                   JOIN items i ON oi.item_id = i.id
                   JOIN orders o ON oi.order_id = o.id
                   WHERE o.status = 'Completed'
                   GROUP BY i.id
                   ORDER BY total_sold DESC
                   LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V.A.V.H Studio - Advanced Inventory & Order Management")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.configure(bg="white")
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="white")
        self.style.configure("TLabel", background="white", foreground="black")
        self.style.configure("TButton", background="#0078D7", foreground="white", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#3399FF")])
        self.style.configure("Success.TButton", background="#28A745", foreground="white")
        self.style.configure("Danger.TButton", background="#DC3545", foreground="white")
        
        self.current_user = None
        self.create_login_screen()

    def create_login_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="V.A.V.H Studio", font=("Arial", 24, "bold"), 
                 foreground="#0078D7").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Advanced Inventory Management", font=("Arial", 12), 
                 foreground="#666").grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
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
                error_label.config(text="Please enter both username and password")
                return
            
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                error_label.config(text="Incorrect username or password")
                pass_entry.delete(0, tk.END)
                return
            
            self.current_user = dict(user)
            self.create_main_ui()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Login", command=do_login).pack()
        
        ttk.Label(frame, text="Default: admin/admin or clerk/clerk", 
                 font=("Arial", 9), foreground="#999").grid(row=6, column=0, columnspan=2)
        
        self.bind("<Return>", do_login)

    def create_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        
        # Top bar
        top = ttk.Frame(self, style="TFrame")
        top.pack(fill="x", padx=10, pady=5)
        
        user_frame = ttk.Frame(top)
        user_frame.pack(side="left")
        ttk.Label(user_frame, text=f"👤 {self.current_user['username']}", 
                 foreground="#0078D7", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ttk.Label(user_frame, text=f"({self.current_user['role']})", 
                 foreground="#666", font=("Arial", 9)).pack(side="left")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side="right")
        
        if self.current_user["role"] == "admin":
            ttk.Button(btn_frame, text="Create User", command=self.create_user).pack(side="left", padx=2)
        
        ttk.Button(btn_frame, text="Profile", command=self.show_profile).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Logout", command=self.logout, 
                  style="Danger.TButton").pack(side="left", padx=2)

        # Notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="📊 Dashboard")
        self.create_dashboard_tab(dashboard_frame)
        
        # Inventory tab
        inventory_frame = ttk.Frame(notebook)
        notebook.add(inventory_frame, text="📦 Inventory")
        self.create_inventory_tab(inventory_frame)
        
        # Orders tab
        orders_frame = ttk.Frame(notebook)
        notebook.add(orders_frame, text="🛒 Orders")
        self.create_orders_tab(orders_frame)
        
        # Customers tab
        customers_frame = ttk.Frame(notebook)
        notebook.add(customers_frame, text="👥 Customers")
        self.create_customers_tab(customers_frame)
        
        # Categories & Suppliers tab
        manage_frame = ttk.Frame(notebook)
        notebook.add(manage_frame, text="⚙️ Manage")
        self.create_manage_tab(manage_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(notebook)
        notebook.add(reports_frame, text="📈 Reports")
        self.create_reports_tab(reports_frame)

    def create_dashboard_tab(self, parent):
        # Header
        header = ttk.Frame(parent, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Dashboard Overview", 
                 font=("Arial", 16, "bold"), foreground="#0078D7").pack(anchor="w")
        ttk.Label(header, text=f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                 font=("Arial", 9), foreground="#666").pack(anchor="w")
        
        # Stats cards
        stats_frame = ttk.Frame(parent, padding=10)
        stats_frame.pack(fill="x")
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Total items
        cur.execute("SELECT COUNT(*), SUM(quantity) FROM items")
        items_data = cur.fetchone()
        
        # Low stock items
        cur.execute("SELECT COUNT(*) FROM items WHERE min_quantity > 0 AND quantity <= min_quantity")
        low_stock = cur.fetchone()[0]
        
        # Total orders
        cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status='Completed'")
        orders_data = cur.fetchone()
        
        # Pending orders
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
        pending = cur.fetchone()[0]
        
        # Total customers
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
        
        conn.close()
        
        # Create stat cards
        cards = [
            ("Total Items", items_data[0], f"{items_data[1] or 0} units in stock", "#0078D7"),
            ("Low Stock Alerts", low_stock, "Items need reorder", "#DC3545" if low_stock > 0 else "#28A745"),
            ("Completed Orders", orders_data[0], f"${orders_data[1] or 0:.2f} revenue", "#28A745"),
            ("Pending Orders", pending, "Awaiting processing", "#FFC107" if pending > 0 else "#28A745"),
            ("Total Customers", customers, "In database", "#17A2B8"),
        ]
        
        for i, (title, value, subtitle, color) in enumerate(cards):
            card = ttk.LabelFrame(stats_frame, text=title, padding=15)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="ew")
            
            ttk.Label(card, text=str(value), font=("Arial", 24, "bold"), 
                     foreground=color).pack()
            ttk.Label(card, text=subtitle, font=("Arial", 9), 
                     foreground="#666").pack()
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        
        # Recent activity
        activity_frame = ttk.LabelFrame(parent, text="Recent Activity", padding=10)
        activity_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text = scrolledtext.ScrolledText(activity_frame, height=10, wrap=tk.WORD)
        text.pack(fill="both", expand=True)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT t.timestamp, u.username, i.name, t.change, t.type, t.note
                      FROM transactions t
                      LEFT JOIN users u ON t.user_id = u.id
                      LEFT JOIN items i ON t.item_id = i.id
                      ORDER BY t.timestamp DESC LIMIT 20""")
        transactions = cur.fetchall()
        conn.close()
        
        for t in transactions:
            text.insert(tk.END, f"[{t['timestamp']}] {t['username']}: {t['name']} - {t['change']:+d} ({t['type']}) - {t['note']}\n")
        
        text.config(state="disabled")
        
        # Quick actions
        actions_frame = ttk.Frame(parent, padding=10)
        actions_frame.pack(fill="x")
        
        ttk.Button(actions_frame, text="🔄 Refresh Dashboard", 
                  command=lambda: self.create_dashboard_tab(parent)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="📊 View Full Reports", 
                  command=lambda: self.focus_tab(5)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="⚠️ View Low Stock", 
                  command=self.show_low_stock_detailed).pack(side="left", padx=5)

    def focus_tab(self, index):
        """Helper to switch to a specific tab"""
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.select(index)
                break

    def show_low_stock_detailed(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT sku, name, quantity, min_quantity, unit_price 
                      FROM items WHERE min_quantity > 0 AND quantity <= min_quantity 
                      ORDER BY quantity ASC""")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            messagebox.showinfo("Low Stock", "No low-stock items found!")
            return
        
        win = tk.Toplevel(self)
        win.title("Low Stock Report")
        win.geometry("700x400")
        
        columns = ('SKU', 'Name', 'Current', 'Min', 'Unit Price', 'Reorder Cost')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        total_cost = 0
        for row in rows:
            reorder_qty = row['min_quantity'] - row['quantity'] + 5
            cost = reorder_qty * row['unit_price']
            total_cost += cost
            tree.insert('', 'end', values=(
                row['sku'], row['name'], row['quantity'], row['min_quantity'],
                f"${row['unit_price']:.2f}", f"${cost:.2f}"
            ))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(win, text=f"Total Estimated Reorder Cost: ${total_cost:.2f}", 
                 font=("Arial", 12, "bold"), foreground="#DC3545").pack(pady=10)

    def create_inventory_tab(self, parent):
        pan = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pan.pack(fill="both", expand=True)
        
        left = ttk.Frame(pan, width=400)
        right = ttk.Frame(pan)
        pan.add(left, weight=1)
        pan.add(right, weight=2)

        # Search frame
        search_frame = ttk.Frame(left, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="🔍 Search SKU/Name:", font=("Arial", 10, "bold")).pack(anchor="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 10))
        search_entry.pack(fill="x", pady=5)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                           selectbackground="#0078D7", selectforeground="white",
                           font=("Arial", 9), yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def refresh_list(event=None):
            q = search_var.get() or "%"
            items = list_items(q)
            listbox.delete(0, tk.END)
            for it in items:
                status = "🔴" if it['min_quantity'] > 0 and it['quantity'] <= it['min_quantity'] else "🟢"
                listbox.insert(tk.END, f"{status} {it['sku']} | {it['name']} | Qty: {it['quantity']}")

        search_entry.bind("<KeyRelease>", lambda e: refresh_list())
        refresh_list()

        # Details panel
        details_frame = ttk.LabelFrame(right, text="Item Details", padding=10)
        details_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        details = tk.Text(details_frame, height=15, bg="white", fg="black", 
                         insertbackground="black", font=("Courier", 10))
        details.pack(fill="both", expand=True)

        def show_selected(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            # Remove emoji and get SKU
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                details.delete("1.0", tk.END)
                details.insert(tk.END, "Item not found")
                return
            
            status = "⚠️ LOW STOCK" if item['min_quantity'] > 0 and item['quantity'] <= item['min_quantity'] else "✓ In Stock"
            
            out = [
                f"{'='*50}",
                f"SKU: {item['sku']}",
                f"Name: {item['name']}",
                f"{'='*50}",
                f"Category: {item.get('category') or 'None'}",
                f"Supplier: {item.get('supplier') or 'None'}",
                f"",
                f"Unit Price: ${item['unit_price']:.2f}",
                f"Quantity: {item['quantity']} {status}",
                f"Min Quantity: {item['min_quantity']}",
                f"Total Value: ${item['unit_price'] * item['quantity']:.2f}",
                f"",
                f"Created: {item.get('created_at') or 'N/A'}",
                f"Last Updated: {item.get('last_updated') or 'N/A'}",
                f"",
                f"Notes: {item['notes'] or 'None'}"
            ]
            details.delete("1.0", tk.END)
            details.insert(tk.END, "\n".join(out))

        listbox.bind("<<ListboxSelect>>", show_selected)

        # Action buttons
        action_frame = ttk.Frame(right, padding=8)
        action_frame.pack(fill="x", padx=8, pady=8)

        def adjust_stock():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            try:
                change_str = simpledialog.askstring("Adjust Stock", 
                    f"Current quantity: {item['quantity']}\nEnter change (negative to decrease):", 
                    parent=self)
                if not change_str:
                    return
                change = int(change_str)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number")
                return
            
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            new_q = item['quantity'] + change
            
            if new_q < 0:
                messagebox.showerror("Error", "Resulting quantity would be negative")
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE items SET quantity=?, last_updated=? WHERE id=?", 
                          (new_q, now_str(), item['id']))
                cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                          (item['id'], change, 'adjust', note, now_str(), self.current_user['id']))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"New quantity: {new_q}")
                refresh_list()
                show_selected()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update stock: {str(e)}")

        def add_item():
            win = tk.Toplevel(self)
            win.title("Add New Item")
            win.geometry("500x600")
            
            # Form fields
            fields_frame = ttk.Frame(win, padding=20)
            fields_frame.pack(fill="both", expand=True)
            
            ttk.Label(fields_frame, text="SKU:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5, padx=5)
            sku_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=sku_var, width=30).grid(row=0, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Name:*", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5, padx=5)
            name_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=name_var, width=30).grid(row=1, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Category:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5, padx=5)
            categories = list_categories()
            cat_var = tk.StringVar()
            cat_combo = ttk.Combobox(fields_frame, textvariable=cat_var, width=28)
            cat_combo['values'] = ['None'] + [c['name'] for c in categories]
            cat_combo.set('None')
            cat_combo.grid(row=2, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Supplier:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="e", pady=5, padx=5)
            suppliers = list_suppliers()
            sup_var = tk.StringVar()
            sup_combo = ttk.Combobox(fields_frame, textvariable=sup_var, width=28)
            sup_combo['values'] = ['None'] + [s['name'] for s in suppliers]
            sup_combo.set('None')
            sup_combo.grid(row=3, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Unit Price:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="e", pady=5, padx=5)
            price_var = tk.StringVar(value="0.00")
            ttk.Entry(fields_frame, textvariable=price_var, width=30).grid(row=4, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Initial Quantity:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="e", pady=5, padx=5)
            qty_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=qty_var, width=30).grid(row=5, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Min Quantity:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="e", pady=5, padx=5)
            min_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=min_var, width=30).grid(row=6, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Notes:", font=("Arial", 10, "bold")).grid(row=7, column=0, sticky="ne", pady=5, padx=5)
            notes_text = tk.Text(fields_frame, height=4, width=30)
            notes_text.grid(row=7, column=1, sticky="w", pady=5)
            
            def save_item():
                sku = sku_var.get().strip()
                name = name_var.get().strip()
                
                if not sku or not name:
                    messagebox.showerror("Error", "SKU and Name are required")
                    return
                
                try:
                    unit_price = float(price_var.get())
                    quantity = int(qty_var.get())
                    min_q = int(min_var.get())
                except ValueError:
                    messagebox.showerror("Error", "Invalid price or quantity")
                    return
                
                # Get category and supplier IDs
                cat_id = None
                sup_id = None
                
                cat_name = cat_var.get()
                if cat_name != 'None':
                    cat = next((c for c in categories if c['name'] == cat_name), None)
                    if cat:
                        cat_id = cat['id']
                
                sup_name = sup_var.get()
                if sup_name != 'None':
                    sup = next((s for s in suppliers if s['name'] == sup_name), None)
                    if sup:
                        sup_id = sup['id']
                
                notes = notes_text.get("1.0", tk.END).strip()
                
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""INSERT INTO items (sku,name,category_id,supplier_id,unit_price,quantity,min_quantity,notes,created_at,last_updated) 
                                  VALUES (?,?,?,?,?,?,?,?,?,?)""",
                              (sku, name, cat_id, sup_id, unit_price, quantity, min_q, notes, now_str(), now_str()))
                    item_id = cur.lastrowid
                    if quantity > 0:
                        cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                                  (item_id, quantity, 'init', 'Initial stock', now_str(), self.current_user['id']))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Item added successfully!")
                    win.destroy()
                    refresh_list()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error", "SKU must be unique")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add item: {str(e)}")
            
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="Save Item", command=save_item, 
                      style="Success.TButton").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

        def delete_item():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            if not messagebox.askyesno("Confirm Delete", 
                f"Are you sure you want to delete:\n\n{item['sku']} - {item['name']}\n\nThis action cannot be undone!"):
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("DELETE FROM items WHERE id=?", (item['id'],))
                cur.execute("DELETE FROM transactions WHERE item_id=?", (item['id'],))
                conn.commit()
                conn.close()
                messagebox.showinfo("Deleted", "Item deleted successfully")
                refresh_list()
                details.delete("1.0", tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete item: {str(e)}")

        def export_inventory():
            try:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    title="Export Inventory"
                )
                if not file_path:
                    return
                
                items = list_items()
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['SKU', 'Name', 'Category', 'Supplier', 'Unit Price', 'Quantity', 'Min Quantity', 'Total Value', 'Notes'])
                    for item in items:
                        writer.writerow([
                            item['sku'], item['name'], item.get('category', ''), item.get('supplier', ''),
                            item['unit_price'], item['quantity'], item['min_quantity'],
                            item['unit_price'] * item['quantity'], item['notes'] or ''
                        ])
                messagebox.showinfo("Success", f"Inventory exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

        role = self.current_user['role']
        if role == "admin":
            ttk.Button(action_frame, text="➕ Add Item", command=add_item, 
                      style="Success.TButton").pack(side="left", padx=4)
            ttk.Button(action_frame, text="🗑️ Delete Item", command=delete_item, 
                      style="Danger.TButton").pack(side="left", padx=4)
        
        ttk.Button(action_frame, text="📊 Adjust Stock", command=adjust_stock).pack(side="left", padx=4)
        ttk.Button(action_frame, text="⚠️ Low Stock", command=self.show_low_stock_detailed).pack(side="left", padx=4)
        ttk.Button(action_frame, text="📥 Export CSV", command=export_inventory).pack(side="left", padx=4)
        ttk.Button(action_frame, text="🔄 Refresh", command=refresh_list).pack(side="left", padx=4)#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from collections import defaultdict
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def now_str():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

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
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
    
    conn.close()

def validate_email(email):
    """Basic email validation"""
    if not email:
        return True
    return '@' in email and '.' in email.split('@')[1]

def validate_phone(phone):
    """Basic phone validation"""
    if not phone:
        return True
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) >= 10

def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_user_field(user_id, field, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()

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
        cur.execute("SELECT * FROM items WHERE id=?", (int(key),))
    else:
        cur.execute("SELECT * FROM items WHERE sku=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row

def generate_order_number():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD-{timestamp}"

def search_customer(query):
    conn = get_conn()
    cur = conn.cursor()
    qlike = f"%{query}%"
    cur.execute("""SELECT * FROM customers 
                   WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                   ORDER BY name""", (qlike, qlike, qlike))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    return row

def list_orders(status_filter=None, limit=100):
    conn = get_conn()
    cur = conn.cursor()
    if status_filter:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       WHERE o.status=?
                       ORDER BY o.created_at DESC""", (status_filter,))
    else:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       ORDER BY o.created_at DESC LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_order_details(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT oi.*, i.sku, i.name as item_name
                   FROM order_items oi
                   LEFT JOIN items i ON oi.item_id=i.id
                   WHERE oi.order_id=?""", (order_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

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

def get_sales_report(start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if start_date and end_date:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders 
                       WHERE status='Completed' AND created_at BETWEEN ? AND ?""", 
                    (start_date, end_date))
    else:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders WHERE status='Completed'""")
    
    report = cur.fetchone()
    conn.close()
    return report

def get_top_selling_items(limit=10):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT i.name, i.sku, SUM(oi.quantity) as total_sold, 
                   SUM(oi.subtotal) as total_revenue
                   FROM order_items oi
                   JOIN items i ON oi.item_id = i.id
                   JOIN orders o ON oi.order_id = o.id
                   WHERE o.status = 'Completed'
                   GROUP BY i.id
                   ORDER BY total_sold DESC
                   LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V.A.V.H Studio - Advanced Inventory & Order Management")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.configure(bg="white")
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="white")
        self.style.configure("TLabel", background="white", foreground="black")
        self.style.configure("TButton", background="#0078D7", foreground="white", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#3399FF")])
        self.style.configure("Success.TButton", background="#28A745", foreground="white")
        self.style.configure("Danger.TButton", background="#DC3545", foreground="white")
        
        self.current_user = None
        self.create_login_screen()

    def create_login_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="V.A.V.H Studio", font=("Arial", 24, "bold"), 
                 foreground="#0078D7").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Advanced Inventory Management", font=("Arial", 12), 
                 foreground="#666").grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
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
                error_label.config(text="Please enter both username and password")
                return
            
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                error_label.config(text="Incorrect username or password")
                pass_entry.delete(0, tk.END)
                return
            
            self.current_user = dict(user)
            self.create_main_ui()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Login", command=do_login).pack()
        
        ttk.Label(frame, text="Default: admin/admin or clerk/clerk", 
                 font=("Arial", 9), foreground="#999").grid(row=6, column=0, columnspan=2)
        
        self.bind("<Return>", do_login)

    def create_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        
        # Top bar
        top = ttk.Frame(self, style="TFrame")
        top.pack(fill="x", padx=10, pady=5)
        
        user_frame = ttk.Frame(top)
        user_frame.pack(side="left")
        ttk.Label(user_frame, text=f"👤 {self.current_user['username']}", 
                 foreground="#0078D7", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ttk.Label(user_frame, text=f"({self.current_user['role']})", 
                 foreground="#666", font=("Arial", 9)).pack(side="left")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side="right")
        
        if self.current_user["role"] == "admin":
            ttk.Button(btn_frame, text="Create User", command=self.create_user).pack(side="left", padx=2)
        
        ttk.Button(btn_frame, text="Profile", command=self.show_profile).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Logout", command=self.logout, 
                  style="Danger.TButton").pack(side="left", padx=2)

        # Notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="📊 Dashboard")
        self.create_dashboard_tab(dashboard_frame)
        
        # Inventory tab
        inventory_frame = ttk.Frame(notebook)
        notebook.add(inventory_frame, text="📦 Inventory")
        self.create_inventory_tab(inventory_frame)
        
        # Orders tab
        orders_frame = ttk.Frame(notebook)
        notebook.add(orders_frame, text="🛒 Orders")
        self.create_orders_tab(orders_frame)
        
        # Customers tab
        customers_frame = ttk.Frame(notebook)
        notebook.add(customers_frame, text="👥 Customers")
        self.create_customers_tab(customers_frame)
        
        # Categories & Suppliers tab
        manage_frame = ttk.Frame(notebook)
        notebook.add(manage_frame, text="⚙️ Manage")
        self.create_manage_tab(manage_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(notebook)
        notebook.add(reports_frame, text="📈 Reports")
        self.create_reports_tab(reports_frame)

    def create_dashboard_tab(self, parent):
        # Header
        header = ttk.Frame(parent, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Dashboard Overview", 
                 font=("Arial", 16, "bold"), foreground="#0078D7").pack(anchor="w")
        ttk.Label(header, text=f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                 font=("Arial", 9), foreground="#666").pack(anchor="w")
        
        # Stats cards
        stats_frame = ttk.Frame(parent, padding=10)
        stats_frame.pack(fill="x")
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Total items
        cur.execute("SELECT COUNT(*), SUM(quantity) FROM items")
        items_data = cur.fetchone()
        
        # Low stock items
        cur.execute("SELECT COUNT(*) FROM items WHERE min_quantity > 0 AND quantity <= min_quantity")
        low_stock = cur.fetchone()[0]
        
        # Total orders
        cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status='Completed'")
        orders_data = cur.fetchone()
        
        # Pending orders
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
        pending = cur.fetchone()[0]
        
        # Total customers
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
        
        conn.close()
        
        # Create stat cards
        cards = [
            ("Total Items", items_data[0], f"{items_data[1] or 0} units in stock", "#0078D7"),
            ("Low Stock Alerts", low_stock, "Items need reorder", "#DC3545" if low_stock > 0 else "#28A745"),
            ("Completed Orders", orders_data[0], f"${orders_data[1] or 0:.2f} revenue", "#28A745"),
            ("Pending Orders", pending, "Awaiting processing", "#FFC107" if pending > 0 else "#28A745"),
            ("Total Customers", customers, "In database", "#17A2B8"),
        ]
        
        for i, (title, value, subtitle, color) in enumerate(cards):
            card = ttk.LabelFrame(stats_frame, text=title, padding=15)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="ew")
            
            ttk.Label(card, text=str(value), font=("Arial", 24, "bold"), 
                     foreground=color).pack()
            ttk.Label(card, text=subtitle, font=("Arial", 9), 
                     foreground="#666").pack()
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        
        # Recent activity
        activity_frame = ttk.LabelFrame(parent, text="Recent Activity", padding=10)
        activity_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text = scrolledtext.ScrolledText(activity_frame, height=10, wrap=tk.WORD)
        text.pack(fill="both", expand=True)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT t.timestamp, u.username, i.name, t.change, t.type, t.note
                      FROM transactions t
                      LEFT JOIN users u ON t.user_id = u.id
                      LEFT JOIN items i ON t.item_id = i.id
                      ORDER BY t.timestamp DESC LIMIT 20""")
        transactions = cur.fetchall()
        conn.close()
        
        for t in transactions:
            text.insert(tk.END, f"[{t['timestamp']}] {t['username']}: {t['name']} - {t['change']:+d} ({t['type']}) - {t['note']}\n")
        
        text.config(state="disabled")
        
        # Quick actions
        actions_frame = ttk.Frame(parent, padding=10)
        actions_frame.pack(fill="x")
        
        ttk.Button(actions_frame, text="🔄 Refresh Dashboard", 
                  command=lambda: self.create_dashboard_tab(parent)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="📊 View Full Reports", 
                  command=lambda: self.focus_tab(5)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="⚠️ View Low Stock", 
                  command=self.show_low_stock_detailed).pack(side="left", padx=5)

    def focus_tab(self, index):
        """Helper to switch to a specific tab"""
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.select(index)
                break

    def show_low_stock_detailed(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT sku, name, quantity, min_quantity, unit_price 
                      FROM items WHERE min_quantity > 0 AND quantity <= min_quantity 
                      ORDER BY quantity ASC""")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            messagebox.showinfo("Low Stock", "No low-stock items found!")
            return
        
        win = tk.Toplevel(self)
        win.title("Low Stock Report")
        win.geometry("700x400")
        
        columns = ('SKU', 'Name', 'Current', 'Min', 'Unit Price', 'Reorder Cost')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        total_cost = 0
        for row in rows:
            reorder_qty = row['min_quantity'] - row['quantity'] + 5
            cost = reorder_qty * row['unit_price']
            total_cost += cost
            tree.insert('', 'end', values=(
                row['sku'], row['name'], row['quantity'], row['min_quantity'],
                f"${row['unit_price']:.2f}", f"${cost:.2f}"
            ))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(win, text=f"Total Estimated Reorder Cost: ${total_cost:.2f}", 
                 font=("Arial", 12, "bold"), foreground="#DC3545").pack(pady=10)

    def create_inventory_tab(self, parent):
        pan = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pan.pack(fill="both", expand=True)
        
        left = ttk.Frame(pan, width=400)
        right = ttk.Frame(pan)
        pan.add(left, weight=1)
        pan.add(right, weight=2)

        # Search frame
        search_frame = ttk.Frame(left, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="🔍 Search SKU/Name:", font=("Arial", 10, "bold")).pack(anchor="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 10))
        search_entry.pack(fill="x", pady=5)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                           selectbackground="#0078D7", selectforeground="white",
                           font=("Arial", 9), yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def refresh_list(event=None):
            q = search_var.get() or "%"
            items = list_items(q)
            listbox.delete(0, tk.END)
            for it in items:
                status = "🔴" if it['min_quantity'] > 0 and it['quantity'] <= it['min_quantity'] else "🟢"
                listbox.insert(tk.END, f"{status} {it['sku']} | {it['name']} | Qty: {it['quantity']}")

        search_entry.bind("<KeyRelease>", lambda e: refresh_list())
        refresh_list()

        # Details panel
        details_frame = ttk.LabelFrame(right, text="Item Details", padding=10)
        details_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        details = tk.Text(details_frame, height=15, bg="white", fg="black", 
                         insertbackground="black", font=("Courier", 10))
        details.pack(fill="both", expand=True)

        def show_selected(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            # Remove emoji and get SKU
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                details.delete("1.0", tk.END)
                details.insert(tk.END, "Item not found")
                return
            
            status = "⚠️ LOW STOCK" if item['min_quantity'] > 0 and item['quantity'] <= item['min_quantity'] else "✓ In Stock"
            
            out = [
                f"{'='*50}",
                f"SKU: {item['sku']}",
                f"Name: {item['name']}",
                f"{'='*50}",
                f"Category: {item.get('category') or 'None'}",
                f"Supplier: {item.get('supplier') or 'None'}",
                f"",
                f"Unit Price: ${item['unit_price']:.2f}",
                f"Quantity: {item['quantity']} {status}",
                f"Min Quantity: {item['min_quantity']}",
                f"Total Value: ${item['unit_price'] * item['quantity']:.2f}",
                f"",
                f"Created: {item.get('created_at') or 'N/A'}",
                f"Last Updated: {item.get('last_updated') or 'N/A'}",
                f"",
                f"Notes: {item['notes'] or 'None'}"
            ]
            details.delete("1.0", tk.END)
            details.insert(tk.END, "\n".join(out))

        listbox.bind("<<ListboxSelect>>", show_selected)

        # Action buttons
        action_frame = ttk.Frame(right, padding=8)
        action_frame.pack(fill="x", padx=8, pady=8)

        def adjust_stock():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            try:
                change_str = simpledialog.askstring("Adjust Stock", 
                    f"Current quantity: {item['quantity']}\nEnter change (negative to decrease):", 
                    parent=self)
                if not change_str:
                    return
                change = int(change_str)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number")
                return
            
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            new_q = item['quantity'] + change
            
            if new_q < 0:
                messagebox.showerror("Error", "Resulting quantity would be negative")
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE items SET quantity=?, last_updated=? WHERE id=?", 
                          (new_q, now_str(), item['id']))
                cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                          (item['id'], change, 'adjust', note, now_str(), self.current_user['id']))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"New quantity: {new_q}")
                refresh_list()
                show_selected()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update stock: {str(e)}")

        def add_item():
            win = tk.Toplevel(self)
            win.title("Add New Item")
            win.geometry("500x600")
            
            # Form fields
            fields_frame = ttk.Frame(win, padding=20)
            fields_frame.pack(fill="both", expand=True)
            
            ttk.Label(fields_frame, text="SKU:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5, padx=5)
            sku_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=sku_var, width=30).grid(row=0, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Name:*", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5, padx=5)
            name_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=name_var, width=30).grid(row=1, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Category:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5, padx=5)
            categories = list_categories()
            cat_var = tk.StringVar()
            cat_combo = ttk.Combobox(fields_frame, textvariable=cat_var, width=28)
            cat_combo['values'] = ['None'] + [c['name'] for c in categories]
            cat_combo.set('None')
            cat_combo.grid(row=2, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Supplier:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="e", pady=5, padx=5)
            suppliers = list_suppliers()
            sup_var = tk.StringVar()
            sup_combo = ttk.Combobox(fields_frame, textvariable=sup_var, width=28)
            sup_combo['values'] = ['None'] + [s['name'] for s in suppliers]
            sup_combo.set('None')
            sup_combo.grid(row=3, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Unit Price:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="e", pady=5, padx=5)
            price_var = tk.StringVar(value="0.00")
            ttk.Entry(fields_frame, textvariable=price_var, width=30).grid(row=4, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Initial Quantity:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="e", pady=5, padx=5)
            qty_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=qty_var, width=30).grid(row=5, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Min Quantity:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="e", pady=5, padx=5)
            min_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=min_var, width=30).grid(row=6, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Notes:", font=("Arial", 10, "bold")).grid(row=7, column=0, sticky="ne", pady=5, padx=5)
            notes_text = tk.Text(fields_frame, height=4, width=30)
            notes_text.grid(row=7, column=1, sticky="w", pady=5)
            
            def save_item():
                sku = sku_var.get().strip()
                name = name_var.get().strip()
                
                if not sku or not name:
                    messagebox.showerror("Error", "SKU and Name are required")
                    return
                
                try:
                    unit_price = float(price_var.get())
                    quantity = int(qty_var.get())
                    min_q = int(min_var.get())
                except ValueError:
                    messagebox.showerror("Error", "Invalid price or quantity")
                    return
                
                # Get category and supplier IDs
                cat_id = None
                sup_id = None
                
                cat_name = cat_var.get()
                if cat_name != 'None':
                    cat = next((c for c in categories if c['name'] == cat_name), None)
                    if cat:
                        cat_id = cat['id']
                
                sup_name = sup_var.get()
                if sup_name != 'None':
                    sup = next((s for s in suppliers if s['name'] == sup_name), None)
                    if sup:
                        sup_id = sup['id']
                
                notes = notes_text.get("1.0", tk.END).strip()
                
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""INSERT INTO items (sku,name,category_id,supplier_id,unit_price,quantity,min_quantity,notes,created_at,last_updated) 
                                  VALUES (?,?,?,?,?,?,?,?,?,?)""",
                              (sku, name, cat_id, sup_id, unit_price, quantity, min_q, notes, now_str(), now_str()))
                    item_id = cur.lastrowid
                    if quantity > 0:
                        cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                                  (item_id, quantity, 'init', 'Initial stock', now_str(), self.current_user['id']))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Item added successfully!")
                    win.destroy()
                    refresh_list()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error", "SKU must be unique")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add item: {str(e)}")
            
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="Save Item", command=save_item, 
                      style="Success.TButton").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

        def delete_item():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            if not messagebox.askyesno("Confirm Delete", 
                f"Are you sure you want to delete:\n\n{item['sku']} - {item['name']}\n\nThis action cannot be undone!"):
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("DELETE FROM items WHERE id=?", (item['id'],))
                cur.execute("DELETE FROM transactions WHERE item_id=?", (item['id'],))
                conn.commit()
                conn.close()
                messagebox.showinfo("Deleted", "Item deleted successfully")
                refresh_list()
                details.delete("1.0", tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete item: {str(e)}")

        def export_inventory():
            try:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    title="Export Inventory"
                )
                if not file_path:
                    return
                
                items = list_items()
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['SKU', 'Name', 'Category', 'Supplier', 'Unit Price', 'Quantity', 'Min Quantity', 'Total Value', 'Notes'])
                    for item in items:
                        writer.writerow([
                            item['sku'], item['name'], item.get('category', ''), item.get('supplier', ''),
                            item['unit_price'], item['quantity'], item['min_quantity'],
                            item['unit_price'] * item['quantity'], item['notes'] or ''
                        ])
                messagebox.showinfo("Success", f"Inventory exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

        role = self.current_user['role']
        if role == "admin":
            ttk.Button(action_frame, text="➕ Add Item", command=add_item, 
                      style="Success.TButton").pack(side="left", padx=4)
            ttk.Button(action_frame, text="🗑️ Delete Item", command=delete_item, 
                      style="Danger.TButton").pack(side="left", padx=4)
        
        ttk.Button(action_frame, text="📊 Adjust Stock", command=adjust_stock).pack(side="left", padx=4)
        ttk.Button(action_frame, text="⚠️ Low Stock", command=self.show_low_stock_detailed).pack(side="left", padx=4)
        ttk.Button(action_frame, text="📥 Export CSV", command=export_inventory).pack(side="left", padx=4)
        ttk.Button(action_frame, text="🔄 Refresh", command=refresh_list).pack(side="left", padx=4)

    def create_orders_tab(self, parent):
        # Top buttons
        btn_frame = ttk.Frame(parent, padding=8)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="➕ Create New Order", command=self.create_order_window,
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Refresh", command=lambda: self.refresh_orders_list()).pack(side="left", padx=5)
        
        # Filter frame
        filter_frame = ttk.Frame(parent, padding=8)
        filter_frame.pack(fill="x")
        ttk.Label(filter_frame, text="Filter by Status:").pack(side="left", padx=5)
        
        self.order_status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.order_status_var, 
                                    values=["All", "Pending", "Processing", "Completed", "Cancelled"],
                                    state="readonly", width=15)
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_orders_list())
        
        # Orders listbox
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.orders_listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                                         selectbackground="#0078D7", selectforeground="white",
                                         font=("Arial", 9), yscrollcommand=scrollbar.set)
        self.orders_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.orders_listbox.yview)
        
        self.orders_listbox.bind("<Double-Button-1>", lambda e: self.view_order_details())
        
        # Action buttons
        action_frame = ttk.Frame(parent, padding=8)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="👁️ View Details", command=self.view_order_details).pack(side="left", padx=5)
        ttk.Button(action_frame, text="✏️ Update Status", command=self.update_order_status).pack(side="left", padx=5)
        ttk.Button(action_frame, text="📥 Export Orders", command=self.export_orders).pack(side="left", padx=5)
        
        self.refresh_orders_list()

    def refresh_orders_list(self):
        status = self.order_status_var.get()
        status_filter = None if status == "All" else status
        orders = list_orders(status_filter)
        
        self.orders_listbox.delete(0, tk.END)
        for order in orders:
            status_emoji = {"Pending": "⏳", "Processing": "🔄", "Completed": "✅", "Cancelled": "❌"}.get(order['status'], "")
            self.orders_listbox.insert(tk.END, 
                f"{status_emoji} {order['order_number']} | {order['customer_name']} | ${order['total_amount']:.2f} | {order['status']} | {order['created_at']}")

    def export_orders(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export Orders"
            )
            if not file_path:
                return
            
            status = self.order_status_var.get()
            status_filter = None if status == "All" else status
            orders = list_orders(status_filter, limit=10000)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Order Number', 'Customer', 'Phone', 'Total', 'Status', 'Created', 'User'])
                for order in orders:
                    writer.writerow([
                        order['order_number'], order['customer_name'], order.get('customer_phone', ''),
                        order['total_amount'], order['status'], order['created_at'], order.get('username', '')
                    ])
            messagebox.showinfo("Success", f"Orders exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from collections import defaultdict
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def now_str():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

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
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
    
    conn.close()

def validate_email(email):
    """Basic email validation"""
    if not email:
        return True
    return '@' in email and '.' in email.split('@')[1]

def validate_phone(phone):
    """Basic phone validation"""
    if not phone:
        return True
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) >= 10

def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_user_field(user_id, field, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()

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
        cur.execute("SELECT * FROM items WHERE id=?", (int(key),))
    else:
        cur.execute("SELECT * FROM items WHERE sku=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row

def generate_order_number():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD-{timestamp}"

def search_customer(query):
    conn = get_conn()
    cur = conn.cursor()
    qlike = f"%{query}%"
    cur.execute("""SELECT * FROM customers 
                   WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                   ORDER BY name""", (qlike, qlike, qlike))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    return row

def list_orders(status_filter=None, limit=100):
    conn = get_conn()
    cur = conn.cursor()
    if status_filter:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       WHERE o.status=?
                       ORDER BY o.created_at DESC""", (status_filter,))
    else:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       ORDER BY o.created_at DESC LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_order_details(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT oi.*, i.sku, i.name as item_name
                   FROM order_items oi
                   LEFT JOIN items i ON oi.item_id=i.id
                   WHERE oi.order_id=?""", (order_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

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

def get_sales_report(start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if start_date and end_date:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders 
                       WHERE status='Completed' AND created_at BETWEEN ? AND ?""", 
                    (start_date, end_date))
    else:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders WHERE status='Completed'""")
    
    report = cur.fetchone()
    conn.close()
    return report

def get_top_selling_items(limit=10):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT i.name, i.sku, SUM(oi.quantity) as total_sold, 
                   SUM(oi.subtotal) as total_revenue
                   FROM order_items oi
                   JOIN items i ON oi.item_id = i.id
                   JOIN orders o ON oi.order_id = o.id
                   WHERE o.status = 'Completed'
                   GROUP BY i.id
                   ORDER BY total_sold DESC
                   LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V.A.V.H Studio - Advanced Inventory & Order Management")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.configure(bg="white")
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="white")
        self.style.configure("TLabel", background="white", foreground="black")
        self.style.configure("TButton", background="#0078D7", foreground="white", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#3399FF")])
        self.style.configure("Success.TButton", background="#28A745", foreground="white")
        self.style.configure("Danger.TButton", background="#DC3545", foreground="white")
        
        self.current_user = None
        self.create_login_screen()

    def create_login_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="V.A.V.H Studio", font=("Arial", 24, "bold"), 
                 foreground="#0078D7").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Advanced Inventory Management", font=("Arial", 12), 
                 foreground="#666").grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
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
                error_label.config(text="Please enter both username and password")
                return
            
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                error_label.config(text="Incorrect username or password")
                pass_entry.delete(0, tk.END)
                return
            
            self.current_user = dict(user)
            self.create_main_ui()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Login", command=do_login).pack()
        
        ttk.Label(frame, text="Default: admin/admin or clerk/clerk", 
                 font=("Arial", 9), foreground="#999").grid(row=6, column=0, columnspan=2)
        
        self.bind("<Return>", do_login)

    def create_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        
        # Top bar
        top = ttk.Frame(self, style="TFrame")
        top.pack(fill="x", padx=10, pady=5)
        
        user_frame = ttk.Frame(top)
        user_frame.pack(side="left")
        ttk.Label(user_frame, text=f"👤 {self.current_user['username']}", 
                 foreground="#0078D7", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ttk.Label(user_frame, text=f"({self.current_user['role']})", 
                 foreground="#666", font=("Arial", 9)).pack(side="left")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side="right")
        
        if self.current_user["role"] == "admin":
            ttk.Button(btn_frame, text="Create User", command=self.create_user).pack(side="left", padx=2)
        
        ttk.Button(btn_frame, text="Profile", command=self.show_profile).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Logout", command=self.logout, 
                  style="Danger.TButton").pack(side="left", padx=2)

        # Notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="📊 Dashboard")
        self.create_dashboard_tab(dashboard_frame)
        
        # Inventory tab
        inventory_frame = ttk.Frame(notebook)
        notebook.add(inventory_frame, text="📦 Inventory")
        self.create_inventory_tab(inventory_frame)
        
        # Orders tab
        orders_frame = ttk.Frame(notebook)
        notebook.add(orders_frame, text="🛒 Orders")
        self.create_orders_tab(orders_frame)
        
        # Customers tab
        customers_frame = ttk.Frame(notebook)
        notebook.add(customers_frame, text="👥 Customers")
        self.create_customers_tab(customers_frame)
        
        # Categories & Suppliers tab
        manage_frame = ttk.Frame(notebook)
        notebook.add(manage_frame, text="⚙️ Manage")
        self.create_manage_tab(manage_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(notebook)
        notebook.add(reports_frame, text="📈 Reports")
        self.create_reports_tab(reports_frame)

    def create_dashboard_tab(self, parent):
        # Header
        header = ttk.Frame(parent, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Dashboard Overview", 
                 font=("Arial", 16, "bold"), foreground="#0078D7").pack(anchor="w")
        ttk.Label(header, text=f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                 font=("Arial", 9), foreground="#666").pack(anchor="w")
        
        # Stats cards
        stats_frame = ttk.Frame(parent, padding=10)
        stats_frame.pack(fill="x")
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Total items
        cur.execute("SELECT COUNT(*), SUM(quantity) FROM items")
        items_data = cur.fetchone()
        
        # Low stock items
        cur.execute("SELECT COUNT(*) FROM items WHERE min_quantity > 0 AND quantity <= min_quantity")
        low_stock = cur.fetchone()[0]
        
        # Total orders
        cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status='Completed'")
        orders_data = cur.fetchone()
        
        # Pending orders
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
        pending = cur.fetchone()[0]
        
        # Total customers
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
        
        conn.close()
        
        # Create stat cards
        cards = [
            ("Total Items", items_data[0], f"{items_data[1] or 0} units in stock", "#0078D7"),
            ("Low Stock Alerts", low_stock, "Items need reorder", "#DC3545" if low_stock > 0 else "#28A745"),
            ("Completed Orders", orders_data[0], f"${orders_data[1] or 0:.2f} revenue", "#28A745"),
            ("Pending Orders", pending, "Awaiting processing", "#FFC107" if pending > 0 else "#28A745"),
            ("Total Customers", customers, "In database", "#17A2B8"),
        ]
        
        for i, (title, value, subtitle, color) in enumerate(cards):
            card = ttk.LabelFrame(stats_frame, text=title, padding=15)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="ew")
            
            ttk.Label(card, text=str(value), font=("Arial", 24, "bold"), 
                     foreground=color).pack()
            ttk.Label(card, text=subtitle, font=("Arial", 9), 
                     foreground="#666").pack()
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        
        # Recent activity
        activity_frame = ttk.LabelFrame(parent, text="Recent Activity", padding=10)
        activity_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text = scrolledtext.ScrolledText(activity_frame, height=10, wrap=tk.WORD)
        text.pack(fill="both", expand=True)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT t.timestamp, u.username, i.name, t.change, t.type, t.note
                      FROM transactions t
                      LEFT JOIN users u ON t.user_id = u.id
                      LEFT JOIN items i ON t.item_id = i.id
                      ORDER BY t.timestamp DESC LIMIT 20""")
        transactions = cur.fetchall()
        conn.close()
        
        for t in transactions:
            text.insert(tk.END, f"[{t['timestamp']}] {t['username']}: {t['name']} - {t['change']:+d} ({t['type']}) - {t['note']}\n")
        
        text.config(state="disabled")
        
        # Quick actions
        actions_frame = ttk.Frame(parent, padding=10)
        actions_frame.pack(fill="x")
        
        ttk.Button(actions_frame, text="🔄 Refresh Dashboard", 
                  command=lambda: self.create_dashboard_tab(parent)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="📊 View Full Reports", 
                  command=lambda: self.focus_tab(5)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="⚠️ View Low Stock", 
                  command=self.show_low_stock_detailed).pack(side="left", padx=5)

    def focus_tab(self, index):
        """Helper to switch to a specific tab"""
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.select(index)
                break

    def show_low_stock_detailed(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT sku, name, quantity, min_quantity, unit_price 
                      FROM items WHERE min_quantity > 0 AND quantity <= min_quantity 
                      ORDER BY quantity ASC""")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            messagebox.showinfo("Low Stock", "No low-stock items found!")
            return
        
        win = tk.Toplevel(self)
        win.title("Low Stock Report")
        win.geometry("700x400")
        
        columns = ('SKU', 'Name', 'Current', 'Min', 'Unit Price', 'Reorder Cost')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        total_cost = 0
        for row in rows:
            reorder_qty = row['min_quantity'] - row['quantity'] + 5
            cost = reorder_qty * row['unit_price']
            total_cost += cost
            tree.insert('', 'end', values=(
                row['sku'], row['name'], row['quantity'], row['min_quantity'],
                f"${row['unit_price']:.2f}", f"${cost:.2f}"
            ))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(win, text=f"Total Estimated Reorder Cost: ${total_cost:.2f}", 
                 font=("Arial", 12, "bold"), foreground="#DC3545").pack(pady=10)

    def create_inventory_tab(self, parent):
        pan = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pan.pack(fill="both", expand=True)
        
        left = ttk.Frame(pan, width=400)
        right = ttk.Frame(pan)
        pan.add(left, weight=1)
        pan.add(right, weight=2)

        # Search frame
        search_frame = ttk.Frame(left, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="🔍 Search SKU/Name:", font=("Arial", 10, "bold")).pack(anchor="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 10))
        search_entry.pack(fill="x", pady=5)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                           selectbackground="#0078D7", selectforeground="white",
                           font=("Arial", 9), yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def refresh_list(event=None):
            q = search_var.get() or "%"
            items = list_items(q)
            listbox.delete(0, tk.END)
            for it in items:
                status = "🔴" if it['min_quantity'] > 0 and it['quantity'] <= it['min_quantity'] else "🟢"
                listbox.insert(tk.END, f"{status} {it['sku']} | {it['name']} | Qty: {it['quantity']}")

        search_entry.bind("<KeyRelease>", lambda e: refresh_list())
        refresh_list()

        # Details panel
        details_frame = ttk.LabelFrame(right, text="Item Details", padding=10)
        details_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        details = tk.Text(details_frame, height=15, bg="white", fg="black", 
                         insertbackground="black", font=("Courier", 10))
        details.pack(fill="both", expand=True)

        def show_selected(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            # Remove emoji and get SKU
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                details.delete("1.0", tk.END)
                details.insert(tk.END, "Item not found")
                return
            
            status = "⚠️ LOW STOCK" if item['min_quantity'] > 0 and item['quantity'] <= item['min_quantity'] else "✓ In Stock"
            
            out = [
                f"{'='*50}",
                f"SKU: {item['sku']}",
                f"Name: {item['name']}",
                f"{'='*50}",
                f"Category: {item.get('category') or 'None'}",
                f"Supplier: {item.get('supplier') or 'None'}",
                f"",
                f"Unit Price: ${item['unit_price']:.2f}",
                f"Quantity: {item['quantity']} {status}",
                f"Min Quantity: {item['min_quantity']}",
                f"Total Value: ${item['unit_price'] * item['quantity']:.2f}",
                f"",
                f"Created: {item.get('created_at') or 'N/A'}",
                f"Last Updated: {item.get('last_updated') or 'N/A'}",
                f"",
                f"Notes: {item['notes'] or 'None'}"
            ]
            details.delete("1.0", tk.END)
            details.insert(tk.END, "\n".join(out))

        listbox.bind("<<ListboxSelect>>", show_selected)

        # Action buttons
        action_frame = ttk.Frame(right, padding=8)
        action_frame.pack(fill="x", padx=8, pady=8)

        def adjust_stock():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            try:
                change_str = simpledialog.askstring("Adjust Stock", 
                    f"Current quantity: {item['quantity']}\nEnter change (negative to decrease):", 
                    parent=self)
                if not change_str:
                    return
                change = int(change_str)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number")
                return
            
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            new_q = item['quantity'] + change
            
            if new_q < 0:
                messagebox.showerror("Error", "Resulting quantity would be negative")
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE items SET quantity=?, last_updated=? WHERE id=?", 
                          (new_q, now_str(), item['id']))
                cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                          (item['id'], change, 'adjust', note, now_str(), self.current_user['id']))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"New quantity: {new_q}")
                refresh_list()
                show_selected()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update stock: {str(e)}")

        def add_item():
            win = tk.Toplevel(self)
            win.title("Add New Item")
            win.geometry("500x600")
            
            # Form fields
            fields_frame = ttk.Frame(win, padding=20)
            fields_frame.pack(fill="both", expand=True)
            
            ttk.Label(fields_frame, text="SKU:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5, padx=5)
            sku_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=sku_var, width=30).grid(row=0, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Name:*", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5, padx=5)
            name_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=name_var, width=30).grid(row=1, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Category:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5, padx=5)
            categories = list_categories()
            cat_var = tk.StringVar()
            cat_combo = ttk.Combobox(fields_frame, textvariable=cat_var, width=28)
            cat_combo['values'] = ['None'] + [c['name'] for c in categories]
            cat_combo.set('None')
            cat_combo.grid(row=2, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Supplier:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="e", pady=5, padx=5)
            suppliers = list_suppliers()
            sup_var = tk.StringVar()
            sup_combo = ttk.Combobox(fields_frame, textvariable=sup_var, width=28)
            sup_combo['values'] = ['None'] + [s['name'] for s in suppliers]
            sup_combo.set('None')
            sup_combo.grid(row=3, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Unit Price:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="e", pady=5, padx=5)
            price_var = tk.StringVar(value="0.00")
            ttk.Entry(fields_frame, textvariable=price_var, width=30).grid(row=4, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Initial Quantity:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="e", pady=5, padx=5)
            qty_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=qty_var, width=30).grid(row=5, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Min Quantity:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="e", pady=5, padx=5)
            min_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=min_var, width=30).grid(row=6, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Notes:", font=("Arial", 10, "bold")).grid(row=7, column=0, sticky="ne", pady=5, padx=5)
            notes_text = tk.Text(fields_frame, height=4, width=30)
            notes_text.grid(row=7, column=1, sticky="w", pady=5)
            
            def save_item():
                sku = sku_var.get().strip()
                name = name_var.get().strip()
                
                if not sku or not name:
                    messagebox.showerror("Error", "SKU and Name are required")
                    return
                
                try:
                    unit_price = float(price_var.get())
                    quantity = int(qty_var.get())
                    min_q = int(min_var.get())
                except ValueError:
                    messagebox.showerror("Error", "Invalid price or quantity")
                    return
                
                # Get category and supplier IDs
                cat_id = None
                sup_id = None
                
                cat_name = cat_var.get()
                if cat_name != 'None':
                    cat = next((c for c in categories if c['name'] == cat_name), None)
                    if cat:
                        cat_id = cat['id']
                
                sup_name = sup_var.get()
                if sup_name != 'None':
                    sup = next((s for s in suppliers if s['name'] == sup_name), None)
                    if sup:
                        sup_id = sup['id']
                
                notes = notes_text.get("1.0", tk.END).strip()
                
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""INSERT INTO items (sku,name,category_id,supplier_id,unit_price,quantity,min_quantity,notes,created_at,last_updated) 
                                  VALUES (?,?,?,?,?,?,?,?,?,?)""",
                              (sku, name, cat_id, sup_id, unit_price, quantity, min_q, notes, now_str(), now_str()))
                    item_id = cur.lastrowid
                    if quantity > 0:
                        cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                                  (item_id, quantity, 'init', 'Initial stock', now_str(), self.current_user['id']))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Item added successfully!")
                    win.destroy()
                    refresh_list()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error", "SKU must be unique")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add item: {str(e)}")
            
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="Save Item", command=save_item, 
                      style="Success.TButton").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

        def delete_item():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            if not messagebox.askyesno("Confirm Delete", 
                f"Are you sure you want to delete:\n\n{item['sku']} - {item['name']}\n\nThis action cannot be undone!"):
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("DELETE FROM items WHERE id=?", (item['id'],))
                cur.execute("DELETE FROM transactions WHERE item_id=?", (item['id'],))
                conn.commit()
                conn.close()
                messagebox.showinfo("Deleted", "Item deleted successfully")
                refresh_list()
                details.delete("1.0", tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete item: {str(e)}")

        def export_inventory():
            try:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    title="Export Inventory"
                )
                if not file_path:
                    return
                
                items = list_items()
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['SKU', 'Name', 'Category', 'Supplier', 'Unit Price', 'Quantity', 'Min Quantity', 'Total Value', 'Notes'])
                    for item in items:
                        writer.writerow([
                            item['sku'], item['name'], item.get('category', ''), item.get('supplier', ''),
                            item['unit_price'], item['quantity'], item['min_quantity'],
                            item['unit_price'] * item['quantity'], item['notes'] or ''
                        ])
                messagebox.showinfo("Success", f"Inventory exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def create_order_window(self):
        win = tk.Toplevel(self)
        win.title("Create New Order")
        win.geometry("950x750")
        
        # Customer section
        customer_frame = ttk.LabelFrame(win, text="Customer Information", padding=10)
        customer_frame.pack(fill="x", padx=10, pady=10)
        
        search_frame = ttk.Frame(customer_frame)
        search_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=5)
        
        ttk.Label(search_frame, text="Search Customer:").pack(side="left", padx=5)
        customer_search_var = tk.StringVar()
        customer_search = ttk.Entry(search_frame, textvariable=customer_search_var, width=30)
        customer_search.pack(side="left", padx=5)
        
        customer_list = tk.Listbox(customer_frame, height=3, width=60, font=("Arial", 9))
        customer_list.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        
        selected_customer = {"id": None}
        
        def search_customers(event=None):
            query = customer_search_var.get()
            if len(query) < 2:
                return
            customers = search_customer(query)
            customer_list.delete(0, tk.END)
            for c in customers:
                customer_list.insert(tk.END, f"{c['id']} | {c['name']} | {c['phone'] or 'N/A'} | {c['email'] or 'N/A'}")
        
        def select_customer(event=None):
            sel = customer_list.curselection()
            if not sel:
                return
            text = customer_list.get(sel[0])
            cid = int(text.split("|")[0].strip())
            customer = get_customer(cid)
            if customer:
                selected_customer["id"] = customer["id"]
                name_var.set(customer["name"])
                phone_var.set(customer["phone"] or "")
                email_var.set(customer["email"] or "")
                address_var.set(customer["address"] or "")
        
        customer_search.bind("<KeyRelease>", search_customers)
        customer_list.bind("<<ListboxSelect>>", select_customer)
        
        ttk.Button(search_frame, text="➕ New Customer", 
                  command=lambda: self.create_new_customer_inline(selected_customer, name_var, phone_var, email_var, address_var)).pack(side="left", padx=5)
        
        # Customer details
        details_frame = ttk.Frame(customer_frame)
        details_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Label(details_frame, text="Name:*").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=name_var, width=35).grid(row=0, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Phone:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        phone_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=phone_var, width=35).grid(row=1, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Email:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        email_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=email_var, width=35).grid(row=2, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Address:").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        address_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=address_var, width=50).grid(row=3, column=1, columnspan=2, sticky="ew", pady=3)
        
        # Items section
        items_frame = ttk.LabelFrame(win, text="Order Items", padding=10)
        items_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Item search
        search_frame = ttk.Frame(items_frame)
        search_frame.pack(fill="x", pady=5)
        
        ttk.Label(search_frame, text="Item ID/SKU:").pack(side="left", padx=5)
        item_search_var = tk.StringVar()
        item_search = ttk.Entry(search_frame, textvariable=item_search_var, width=20)
        item_search.pack(side="left", padx=5)
        
        ttk.Label(search_frame, text="Quantity:").pack(side="left", padx=5)
        quantity_var = tk.StringVar(value="1")
        quantity_entry = ttk.Entry(search_frame, textvariable=quantity_var, width=10)
        quantity_entry.pack(side="left", padx=5)
        
        order_items = []
        
        def add_item_to_order():
            item_key = item_search_var.get().strip()
            if not item_key:
                messagebox.showwarning("Warning", "Enter item ID or SKU")
                return
            
            item = get_item_by_sku_or_id(item_key)
            if not item:
                messagebox.showerror("Error", "Item not found")
                return
            
            try:
                qty = int(quantity_var.get())
                if qty <= 0:
                    raise ValueError()
            except:
                messagebox.showerror("Error", "Invalid quantity")
                return
            
            if item['quantity'] < qty:
                if not messagebox.askyesno("Warning", f"Only {item['quantity']} units available. Continue anyway?"):
                    return
            
            subtotal = item['unit_price'] * qty
            order_items.append({
                'item_id': item['id'],
                'sku': item['sku'],
                'name': item['name'],
                'quantity': qty,
                'unit_price': item['unit_price'],
                'subtotal': subtotal
            })
            
            refresh_order_items()
            item_search_var.set("")
            quantity_var.set("1")
        
        ttk.Button(search_frame, text="➕ Add Item", command=add_item_to_order, 
                  style="Success.TButton").pack(side="left", padx=5)
        
        # Order items tree
        columns = ('SKU', 'Name', 'Qty', 'Unit Price', 'Subtotal')
        tree_frame = ttk.Frame(items_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)
        
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")
        
        items_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=items_tree.yview)
        
        for col in columns:
            items_tree.heading(col, text=col)
            items_tree.column(col, width=100)
        items_tree.pack(fill="both", expand=True)
        
        total_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(items_frame, textvariable=total_var, font=("Arial", 14, "bold"), foreground="#0078D7").pack(pady=5)
        
        def refresh_order_items():
            for item in items_tree.get_children():
                items_tree.delete(item)
            
            total = 0
            for item in order_items:
                items_tree.insert('', 'end', values=(
                    item['sku'], item['name'], item['quantity'], 
                    f"${item['unit_price']:.2f}", f"${item['subtotal']:.2f}"
                ))
                total += item['subtotal']
            total_var.set(f"Total: ${total:.2f}")
        
        def remove_selected_item():
            selected = items_tree.selection()
            if not selected:
                return
            index = items_tree.index(selected[0])
            order_items.pop(index)
            refresh_order_items()
        
        ttk.Button(items_frame, text="🗑️ Remove Selected", command=remove_selected_item, 
                  style="Danger.TButton").pack(pady=5)
        
        # Notes
        notes_frame = ttk.Frame(win, padding=10)
        notes_frame.pack(fill="x")
        ttk.Label(notes_frame, text="Order Notes:").pack(anchor="w")
        notes_text = tk.Text(notes_frame, height=3)
        notes_text.pack(fill="x")
        
        # Submit button
        def submit_order():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Customer name is required")
                return
            
            if not order_items:
                messagebox.showerror("Error", "Add at least one item")
                return
            
            # Validate email if provided
            if email_var.get() and not validate_email(email_var.get()):
                messagebox.showerror("Error", "Invalid email format")
                return
            
            conn = get_conn()
            cur = conn.cursor()
            
            try:
                # Create or update customer
                if selected_customer["id"]:
                    cur.execute("""UPDATE customers SET name=?, phone=?, email=?, address=? WHERE id=?""",
                               (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), selected_customer["id"]))
                    customer_id = selected_customer["id"]
                else:
                    cur.execute("""INSERT INTO customers (name, phone, email, address, created_at, total_orders, total_spent) 
                                  VALUES (?, ?, ?, ?, ?, 0, 0)""",
                               (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), now_str()))
                    customer_id = cur.lastrowid
                
                # Calculate total
                total = sum(item['subtotal'] for item in order_items)
                
                # Create order
                order_number = generate_order_number()
                cur.execute("""INSERT INTO orders (order_number, customer_id, total_amount, status, created_at, user_id, notes)
                              VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (order_number, customer_id, total, 'Pending', now_str(), self.current_user['id'], 
                            notes_text.get("1.0", tk.END).strip()))
                order_id = cur.lastrowid
                
                # Add order items and update inventory
                for item in order_items:
                    cur.execute("""INSERT INTO order_items (order_id, item_id, quantity, unit_price, subtotal)
                                  VALUES (?, ?, ?, ?, ?)""",
                               (order_id, item['item_id'], item['quantity'], item['unit_price'], item['subtotal']))
                    
                    # Update inventory
                    cur.execute("UPDATE items SET quantity = quantity - ?, last_updated=? WHERE id = ?",
                               (item['quantity'], now_str(), item['item_id']))
                    
                    # Record transaction
                    cur.execute("""INSERT INTO transactions (item_id, change, type, note, timestamp, user_id)
                                  VALUES (?, ?, ?, ?, ?, ?)""",
                               (item['item_id'], -item['quantity'], 'order', f'Order {order_number}', now_str(), self.current_user['id']))
                
                # Update customer stats
                cur.execute("""UPDATE customers SET total_orders = total_orders + 1, total_spent = total_spent + ? 
                              WHERE id = ?""", (total, customer_id))
                
                conn.commit()
                messagebox.showinfo("Success", f"Order {order_number} created successfully!\nTotal: ${total:.2f}")
                win.destroy()
                self.refresh_orders_list()
                
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error", f"Failed to create order: {str(e)}")
            finally:
                conn.close()
        
        btn_frame = ttk.Frame(win, padding=10)
        btn_frame.pack()
        ttk.Button(btn_frame, text="✅ Create Order", command=submit_order, 
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

        role = self.current_user['role']
        if role == "admin":
            ttk.Button(action_frame, text="➕ Add Item", command=add_item, 
                      style="Success.TButton").pack(side="left", padx=4)
            ttk.Button(action_frame, text="🗑️ Delete Item", command=delete_item, 
                      style="Danger.TButton").pack(side="left", padx=4)
        
        ttk.Button(action_frame, text="📊 Adjust Stock", command=adjust_stock).pack(side="left", padx=4)
        ttk.Button(action_frame, text="⚠️ Low Stock", command=self.show_low_stock_detailed).pack(side="left", padx=4)
        ttk.Button(action_frame, text="📥 Export CSV", command=export_inventory).pack(side="left", padx=4)
        ttk.Button(action_frame, text="🔄 Refresh", command=refresh_list).pack(side="left", padx=4)

    def create_orders_tab(self, parent):
        # Top buttons
        btn_frame = ttk.Frame(parent, padding=8)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="➕ Create New Order", command=self.create_order_window,
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Refresh", command=lambda: self.refresh_orders_list()).pack(side="left", padx=5)
        
        # Filter frame
        filter_frame = ttk.Frame(parent, padding=8)
        filter_frame.pack(fill="x")
        ttk.Label(filter_frame, text="Filter by Status:").pack(side="left", padx=5)
        
        self.order_status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.order_status_var, 
                                    values=["All", "Pending", "Processing", "Completed", "Cancelled"],
                                    state="readonly", width=15)
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_orders_list())
        
        # Orders listbox
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.orders_listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                                         selectbackground="#0078D7", selectforeground="white",
                                         font=("Arial", 9), yscrollcommand=scrollbar.set)
        self.orders_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.orders_listbox.yview)
        
        self.orders_listbox.bind("<Double-Button-1>", lambda e: self.view_order_details())
        
        # Action buttons
        action_frame = ttk.Frame(parent, padding=8)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="👁️ View Details", command=self.view_order_details).pack(side="left", padx=5)
        ttk.Button(action_frame, text="✏️ Update Status", command=self.update_order_status).pack(side="left", padx=5)
        ttk.Button(action_frame, text="📥 Export Orders", command=self.export_orders).pack(side="left", padx=5)
        
        self.refresh_orders_list()

    def refresh_orders_list(self):
        status = self.order_status_var.get()
        status_filter = None if status == "All" else status
        orders = list_orders(status_filter)
        
        self.orders_listbox.delete(0, tk.END)
        for order in orders:
            status_emoji = {"Pending": "⏳", "Processing": "🔄", "Completed": "✅", "Cancelled": "❌"}.get(order['status'], "")
            self.orders_listbox.insert(tk.END, 
                f"{status_emoji} {order['order_number']} | {order['customer_name']} | ${order['total_amount']:.2f} | {order['status']} | {order['created_at']}")

    def export_orders(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export Orders"
            )
            if not file_path:
                return
            
            status = self.order_status_var.get()
            status_filter = None if status == "All" else status
            orders = list_orders(status_filter, limit=10000)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Order Number', 'Customer', 'Phone', 'Total', 'Status', 'Created', 'User'])
                for order in orders:
                    writer.writerow([
                        order['order_number'], order['customer_name'], order.get('customer_phone', ''),
                        order['total_amount'], order['status'], order['created_at'], order.get('username', '')
                    ])
            messagebox.showinfo("Success", f"Orders exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from collections import defaultdict
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def now_str():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

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
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
    
    conn.close()

def validate_email(email):
    """Basic email validation"""
    if not email:
        return True
    return '@' in email and '.' in email.split('@')[1]

def validate_phone(phone):
    """Basic phone validation"""
    if not phone:
        return True
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) >= 10

def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_user_field(user_id, field, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()

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
        cur.execute("SELECT * FROM items WHERE id=?", (int(key),))
    else:
        cur.execute("SELECT * FROM items WHERE sku=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row

def generate_order_number():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD-{timestamp}"

def search_customer(query):
    conn = get_conn()
    cur = conn.cursor()
    qlike = f"%{query}%"
    cur.execute("""SELECT * FROM customers 
                   WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                   ORDER BY name""", (qlike, qlike, qlike))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    return row

def list_orders(status_filter=None, limit=100):
    conn = get_conn()
    cur = conn.cursor()
    if status_filter:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       WHERE o.status=?
                       ORDER BY o.created_at DESC""", (status_filter,))
    else:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       ORDER BY o.created_at DESC LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_order_details(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT oi.*, i.sku, i.name as item_name
                   FROM order_items oi
                   LEFT JOIN items i ON oi.item_id=i.id
                   WHERE oi.order_id=?""", (order_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

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

def get_sales_report(start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if start_date and end_date:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders 
                       WHERE status='Completed' AND created_at BETWEEN ? AND ?""", 
                    (start_date, end_date))
    else:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders WHERE status='Completed'""")
    
    report = cur.fetchone()
    conn.close()
    return report

def get_top_selling_items(limit=10):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT i.name, i.sku, SUM(oi.quantity) as total_sold, 
                   SUM(oi.subtotal) as total_revenue
                   FROM order_items oi
                   JOIN items i ON oi.item_id = i.id
                   JOIN orders o ON oi.order_id = o.id
                   WHERE o.status = 'Completed'
                   GROUP BY i.id
                   ORDER BY total_sold DESC
                   LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V.A.V.H Studio - Advanced Inventory & Order Management")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.configure(bg="white")
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="white")
        self.style.configure("TLabel", background="white", foreground="black")
        self.style.configure("TButton", background="#0078D7", foreground="white", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#3399FF")])
        self.style.configure("Success.TButton", background="#28A745", foreground="white")
        self.style.configure("Danger.TButton", background="#DC3545", foreground="white")
        
        self.current_user = None
        self.create_login_screen()

    def create_login_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="V.A.V.H Studio", font=("Arial", 24, "bold"), 
                 foreground="#0078D7").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Advanced Inventory Management", font=("Arial", 12), 
                 foreground="#666").grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
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
                error_label.config(text="Please enter both username and password")
                return
            
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                error_label.config(text="Incorrect username or password")
                pass_entry.delete(0, tk.END)
                return
            
            self.current_user = dict(user)
            self.create_main_ui()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Login", command=do_login).pack()
        
        ttk.Label(frame, text="Default: admin/admin or clerk/clerk", 
                 font=("Arial", 9), foreground="#999").grid(row=6, column=0, columnspan=2)
        
        self.bind("<Return>", do_login)

    def create_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        
        # Top bar
        top = ttk.Frame(self, style="TFrame")
        top.pack(fill="x", padx=10, pady=5)
        
        user_frame = ttk.Frame(top)
        user_frame.pack(side="left")
        ttk.Label(user_frame, text=f"👤 {self.current_user['username']}", 
                 foreground="#0078D7", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ttk.Label(user_frame, text=f"({self.current_user['role']})", 
                 foreground="#666", font=("Arial", 9)).pack(side="left")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side="right")
        
        if self.current_user["role"] == "admin":
            ttk.Button(btn_frame, text="Create User", command=self.create_user).pack(side="left", padx=2)
        
        ttk.Button(btn_frame, text="Profile", command=self.show_profile).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Logout", command=self.logout, 
                  style="Danger.TButton").pack(side="left", padx=2)

        # Notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="📊 Dashboard")
        self.create_dashboard_tab(dashboard_frame)
        
        # Inventory tab
        inventory_frame = ttk.Frame(notebook)
        notebook.add(inventory_frame, text="📦 Inventory")
        self.create_inventory_tab(inventory_frame)
        
        # Orders tab
        orders_frame = ttk.Frame(notebook)
        notebook.add(orders_frame, text="🛒 Orders")
        self.create_orders_tab(orders_frame)
        
        # Customers tab
        customers_frame = ttk.Frame(notebook)
        notebook.add(customers_frame, text="👥 Customers")
        self.create_customers_tab(customers_frame)
        
        # Categories & Suppliers tab
        manage_frame = ttk.Frame(notebook)
        notebook.add(manage_frame, text="⚙️ Manage")
        self.create_manage_tab(manage_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(notebook)
        notebook.add(reports_frame, text="📈 Reports")
        self.create_reports_tab(reports_frame)

    def create_dashboard_tab(self, parent):
        # Header
        header = ttk.Frame(parent, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Dashboard Overview", 
                 font=("Arial", 16, "bold"), foreground="#0078D7").pack(anchor="w")
        ttk.Label(header, text=f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                 font=("Arial", 9), foreground="#666").pack(anchor="w")
        
        # Stats cards
        stats_frame = ttk.Frame(parent, padding=10)
        stats_frame.pack(fill="x")
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Total items
        cur.execute("SELECT COUNT(*), SUM(quantity) FROM items")
        items_data = cur.fetchone()
        
        # Low stock items
        cur.execute("SELECT COUNT(*) FROM items WHERE min_quantity > 0 AND quantity <= min_quantity")
        low_stock = cur.fetchone()[0]
        
        # Total orders
        cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status='Completed'")
        orders_data = cur.fetchone()
        
        # Pending orders
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
        pending = cur.fetchone()[0]
        
        # Total customers
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
        
        conn.close()
        
        # Create stat cards
        cards = [
            ("Total Items", items_data[0], f"{items_data[1] or 0} units in stock", "#0078D7"),
            ("Low Stock Alerts", low_stock, "Items need reorder", "#DC3545" if low_stock > 0 else "#28A745"),
            ("Completed Orders", orders_data[0], f"${orders_data[1] or 0:.2f} revenue", "#28A745"),
            ("Pending Orders", pending, "Awaiting processing", "#FFC107" if pending > 0 else "#28A745"),
            ("Total Customers", customers, "In database", "#17A2B8"),
        ]
        
        for i, (title, value, subtitle, color) in enumerate(cards):
            card = ttk.LabelFrame(stats_frame, text=title, padding=15)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="ew")
            
            ttk.Label(card, text=str(value), font=("Arial", 24, "bold"), 
                     foreground=color).pack()
            ttk.Label(card, text=subtitle, font=("Arial", 9), 
                     foreground="#666").pack()
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        
        # Recent activity
        activity_frame = ttk.LabelFrame(parent, text="Recent Activity", padding=10)
        activity_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text = scrolledtext.ScrolledText(activity_frame, height=10, wrap=tk.WORD)
        text.pack(fill="both", expand=True)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT t.timestamp, u.username, i.name, t.change, t.type, t.note
                      FROM transactions t
                      LEFT JOIN users u ON t.user_id = u.id
                      LEFT JOIN items i ON t.item_id = i.id
                      ORDER BY t.timestamp DESC LIMIT 20""")
        transactions = cur.fetchall()
        conn.close()
        
        for t in transactions:
            text.insert(tk.END, f"[{t['timestamp']}] {t['username']}: {t['name']} - {t['change']:+d} ({t['type']}) - {t['note']}\n")
        
        text.config(state="disabled")
        
        # Quick actions
        actions_frame = ttk.Frame(parent, padding=10)
        actions_frame.pack(fill="x")
        
        ttk.Button(actions_frame, text="🔄 Refresh Dashboard", 
                  command=lambda: self.create_dashboard_tab(parent)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="📊 View Full Reports", 
                  command=lambda: self.focus_tab(5)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="⚠️ View Low Stock", 
                  command=self.show_low_stock_detailed).pack(side="left", padx=5)

    def focus_tab(self, index):
        """Helper to switch to a specific tab"""
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.select(index)
                break

    def show_low_stock_detailed(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT sku, name, quantity, min_quantity, unit_price 
                      FROM items WHERE min_quantity > 0 AND quantity <= min_quantity 
                      ORDER BY quantity ASC""")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            messagebox.showinfo("Low Stock", "No low-stock items found!")
            return
        
        win = tk.Toplevel(self)
        win.title("Low Stock Report")
        win.geometry("700x400")
        
        columns = ('SKU', 'Name', 'Current', 'Min', 'Unit Price', 'Reorder Cost')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        total_cost = 0
        for row in rows:
            reorder_qty = row['min_quantity'] - row['quantity'] + 5
            cost = reorder_qty * row['unit_price']
            total_cost += cost
            tree.insert('', 'end', values=(
                row['sku'], row['name'], row['quantity'], row['min_quantity'],
                f"${row['unit_price']:.2f}", f"${cost:.2f}"
            ))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(win, text=f"Total Estimated Reorder Cost: ${total_cost:.2f}", 
                 font=("Arial", 12, "bold"), foreground="#DC3545").pack(pady=10)

    def create_inventory_tab(self, parent):
        pan = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pan.pack(fill="both", expand=True)
        
        left = ttk.Frame(pan, width=400)
        right = ttk.Frame(pan)
        pan.add(left, weight=1)
        pan.add(right, weight=2)

        # Search frame
        search_frame = ttk.Frame(left, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="🔍 Search SKU/Name:", font=("Arial", 10, "bold")).pack(anchor="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 10))
        search_entry.pack(fill="x", pady=5)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                           selectbackground="#0078D7", selectforeground="white",
                           font=("Arial", 9), yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def refresh_list(event=None):
            q = search_var.get() or "%"
            items = list_items(q)
            listbox.delete(0, tk.END)
            for it in items:
                status = "🔴" if it['min_quantity'] > 0 and it['quantity'] <= it['min_quantity'] else "🟢"
                listbox.insert(tk.END, f"{status} {it['sku']} | {it['name']} | Qty: {it['quantity']}")

        search_entry.bind("<KeyRelease>", lambda e: refresh_list())
        refresh_list()

        # Details panel
        details_frame = ttk.LabelFrame(right, text="Item Details", padding=10)
        details_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        details = tk.Text(details_frame, height=15, bg="white", fg="black", 
                         insertbackground="black", font=("Courier", 10))
        details.pack(fill="both", expand=True)

        def show_selected(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            # Remove emoji and get SKU
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                details.delete("1.0", tk.END)
                details.insert(tk.END, "Item not found")
                return
            
            status = "⚠️ LOW STOCK" if item['min_quantity'] > 0 and item['quantity'] <= item['min_quantity'] else "✓ In Stock"
            
            out = [
                f"{'='*50}",
                f"SKU: {item['sku']}",
                f"Name: {item['name']}",
                f"{'='*50}",
                f"Category: {item.get('category') or 'None'}",
                f"Supplier: {item.get('supplier') or 'None'}",
                f"",
                f"Unit Price: ${item['unit_price']:.2f}",
                f"Quantity: {item['quantity']} {status}",
                f"Min Quantity: {item['min_quantity']}",
                f"Total Value: ${item['unit_price'] * item['quantity']:.2f}",
                f"",
                f"Created: {item.get('created_at') or 'N/A'}",
                f"Last Updated: {item.get('last_updated') or 'N/A'}",
                f"",
                f"Notes: {item['notes'] or 'None'}"
            ]
            details.delete("1.0", tk.END)
            details.insert(tk.END, "\n".join(out))

        listbox.bind("<<ListboxSelect>>", show_selected)

        # Action buttons
        action_frame = ttk.Frame(right, padding=8)
        action_frame.pack(fill="x", padx=8, pady=8)

        def adjust_stock():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            try:
                change_str = simpledialog.askstring("Adjust Stock", 
                    f"Current quantity: {item['quantity']}\nEnter change (negative to decrease):", 
                    parent=self)
                if not change_str:
                    return
                change = int(change_str)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number")
                return
            
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            new_q = item['quantity'] + change
            
            if new_q < 0:
                messagebox.showerror("Error", "Resulting quantity would be negative")
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE items SET quantity=?, last_updated=? WHERE id=?", 
                          (new_q, now_str(), item['id']))
                cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                          (item['id'], change, 'adjust', note, now_str(), self.current_user['id']))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"New quantity: {new_q}")
                refresh_list()
                show_selected()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update stock: {str(e)}")

        def add_item():
            win = tk.Toplevel(self)
            win.title("Add New Item")
            win.geometry("500x600")
            
            # Form fields
            fields_frame = ttk.Frame(win, padding=20)
            fields_frame.pack(fill="both", expand=True)
            
            ttk.Label(fields_frame, text="SKU:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5, padx=5)
            sku_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=sku_var, width=30).grid(row=0, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Name:*", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5, padx=5)
            name_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=name_var, width=30).grid(row=1, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Category:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5, padx=5)
            categories = list_categories()
            cat_var = tk.StringVar()
            cat_combo = ttk.Combobox(fields_frame, textvariable=cat_var, width=28)
            cat_combo['values'] = ['None'] + [c['name'] for c in categories]
            cat_combo.set('None')
            cat_combo.grid(row=2, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Supplier:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="e", pady=5, padx=5)
            suppliers = list_suppliers()
            sup_var = tk.StringVar()
            sup_combo = ttk.Combobox(fields_frame, textvariable=sup_var, width=28)
            sup_combo['values'] = ['None'] + [s['name'] for s in suppliers]
            sup_combo.set('None')
            sup_combo.grid(row=3, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Unit Price:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="e", pady=5, padx=5)
            price_var = tk.StringVar(value="0.00")
            ttk.Entry(fields_frame, textvariable=price_var, width=30).grid(row=4, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Initial Quantity:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="e", pady=5, padx=5)
            qty_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=qty_var, width=30).grid(row=5, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Min Quantity:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="e", pady=5, padx=5)
            min_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=min_var, width=30).grid(row=6, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Notes:", font=("Arial", 10, "bold")).grid(row=7, column=0, sticky="ne", pady=5, padx=5)
            notes_text = tk.Text(fields_frame, height=4, width=30)
            notes_text.grid(row=7, column=1, sticky="w", pady=5)
            
            def save_item():
                sku = sku_var.get().strip()
                name = name_var.get().strip()
                
                if not sku or not name:
                    messagebox.showerror("Error", "SKU and Name are required")
                    return
                
                try:
                    unit_price = float(price_var.get())
                    quantity = int(qty_var.get())
                    min_q = int(min_var.get())
                except ValueError:
                    messagebox.showerror("Error", "Invalid price or quantity")
                    return
                
                # Get category and supplier IDs
                cat_id = None
                sup_id = None
                
                cat_name = cat_var.get()
                if cat_name != 'None':
                    cat = next((c for c in categories if c['name'] == cat_name), None)
                    if cat:
                        cat_id = cat['id']
                
                sup_name = sup_var.get()
                if sup_name != 'None':
                    sup = next((s for s in suppliers if s['name'] == sup_name), None)
                    if sup:
                        sup_id = sup['id']
                
                notes = notes_text.get("1.0", tk.END).strip()
                
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""INSERT INTO items (sku,name,category_id,supplier_id,unit_price,quantity,min_quantity,notes,created_at,last_updated) 
                                  VALUES (?,?,?,?,?,?,?,?,?,?)""",
                              (sku, name, cat_id, sup_id, unit_price, quantity, min_q, notes, now_str(), now_str()))
                    item_id = cur.lastrowid
                    if quantity > 0:
                        cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                                  (item_id, quantity, 'init', 'Initial stock', now_str(), self.current_user['id']))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Item added successfully!")
                    win.destroy()
                    refresh_list()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error", "SKU must be unique")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add item: {str(e)}")
            
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="Save Item", command=save_item, 
                      style="Success.TButton").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

    def create_new_customer_inline(self, selected_customer, name_var, phone_var, email_var, address_var):
        name = simpledialog.askstring("New Customer", "Customer Name:*", parent=self)
        if not name:
            return
        phone = simpledialog.askstring("New Customer", "Phone:", parent=self) or ""
        email = simpledialog.askstring("New Customer", "Email:", parent=self) or ""
        
        if email and not validate_email(email):
            messagebox.showerror("Error", "Invalid email format")
            return
        
        address = simpledialog.askstring("New Customer", "Address:", parent=self) or ""
        
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""INSERT INTO customers (name, phone, email, address, created_at, total_orders, total_spent) 
                          VALUES (?, ?, ?, ?, ?, 0, 0)""",
                       (name, phone, email, address, now_str()))
            customer_id = cur.lastrowid
            conn.commit()
            conn.close()
            
            selected_customer["id"] = customer_id
            name_var.set(name)
            phone_var.set(phone)
            email_var.set(email)
            address_var.set(address)
            messagebox.showinfo("Success", "Customer created!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create customer: {str(e)}")

    def view_order_details(self):
        sel = self.orders_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Order", "Please select an order first")
            return
        
        text = self.orders_listbox.get(sel[0])
        order_number = text.split("|")[0].strip().split()[-1]
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone, c.email, c.address, u.username
                      FROM orders o
                      LEFT JOIN customers c ON o.customer_id=c.id
                      LEFT JOIN users u ON o.user_id=u.id
                      WHERE o.order_number=?""", (order_number,))
        order = cur.fetchone()
        
        if not order:
            messagebox.showerror("Error", "Order not found")
            conn.close()
            return
        
        items = get_order_details(order['id'])
        conn.close()
        
        win = tk.Toplevel(self)
        win.title(f"Order Details - {order_number}")
        win.geometry("800x650")
        
        # Order info
        info_frame = ttk.LabelFrame(win, text="Order Information", padding=15)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        status_color = {"Pending": "#FFC107", "Processing": "#17A2B8", 
                       "Completed": "#28A745", "Cancelled": "#DC3545"}.get(order['status'], "#666")
        
        info_text = f"""Order Number: {order['order_number']}
Status: {order['status']}
Date: {order['created_at']}
Created by: {order['username']}
Total Amount: ${order['total_amount']:.2f}

Customer: {order['customer_name']}
Phone: {order['phone'] or 'N/A'}
Email: {order['email'] or 'N/A'}
Address: {order['address'] or 'N/A'}

Notes: {order['notes'] or 'None'}"""
        
        ttk.Label(info_frame, text=info_text, justify="left", font=("Courier", 10)).pack(anchor="w")
        
        # Items
        items_frame = ttk.LabelFrame(win, text="Order Items", padding=10)
        items_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ('SKU', 'Name', 'Qty', 'Unit Price', 'Subtotal')
        tree = ttk.Treeview(items_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for item in items:
            tree.insert('', 'end', values=(
                item['sku'], item['item_name'], item['quantity'],
                f"${item['unit_price']:.2f}", f"${item['subtotal']:.2f}"
            ))
        
        tree.pack(fill="both", expand=True)
        
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    def update_order_status(self):
        sel = self.orders_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Order", "Please select an order first")
            return
        
        text = self.orders_listbox.get(sel[0])
        order_number = text.split("|")[0].strip().split()[-1]
        
        win = tk.Toplevel(self)
        win.title("Update Order Status")
        win.geometry("350x200")
        
        ttk.Label(win, text=f"Order: {order_number}", font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Label(win, text="Select new status:").pack(pady=5)
        
        status_var = tk.StringVar(value="Pending")
        for status in ["Pending", "Processing", "Completed", "Cancelled"]:
            ttk.Radiobutton(win, text=status, variable=status_var, value=status).pack(anchor="w", padx=50)
        
        def save_status():
            new_status = status_var.get()
            try:
                conn = get_conn()
                cur = conn.cursor()
                
                if new_status == "Completed":
                    cur.execute("UPDATE orders SET status=?, completed_at=? WHERE order_number=?", 
                              (new_status, now_str(), order_number))
                else:
                    cur.execute("UPDATE orders SET status=? WHERE order_number=?", 
                              (new_status, order_number))
                
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Order status updated")
                win.destroy()
                self.refresh_orders_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update status: {str(e)}")
        
        ttk.Button(win, text="Save", command=save_status, style="Success.TButton").pack(pady=15)

    def create_customers_tab(self, parent):
        # Top buttons
        btn_frame = ttk.Frame(parent, padding=8)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="➕ Add Customer", command=self.add_customer, 
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Refresh", command=lambda: self.refresh_customers_list()).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📥 Export", command=self.export_customers).pack(side="left", padx=5)
        
        # Search
        search_frame = ttk.Frame(parent, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="🔍 Search:").pack(side="left", padx=5)
        self.customer_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.customer_search_var, width=30)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_customers_list())
        
        # Customers list
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.customers_listbox = tk.Listbox(list_frame, bg="white", fg="black",
                                           selectbackground="#0078D7", selectforeground="white",
                                           font=("Arial", 9), yscrollcommand=scrollbar.set)
        self.customers_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.customers_listbox.yview)
        
        self.customers_listbox.bind("<Double-Button-1>", lambda e: self.edit_customer())
        
        # Action buttons
        action_frame = ttk.Frame(parent, padding=8)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="✏️ Edit", command=self.edit_customer).pack(side="left", padx=5)
        ttk.Button(action_frame, text="🗑️ Delete", command=self.delete_customer, 
                  style="Danger.TButton").pack(side="left", padx=5)
        ttk.Button(action_frame, text="📋 View History", command=self.view_customer_history).pack(side="left", padx=5)
        
        self.refresh_customers_list()

    def refresh_customers_list(self):
        query = self.customer_search_var.get() if hasattr(self, 'customer_search_var') else ""
        customers = search_customer(query) if query else search_customer("%")
        
        self.customers_listbox.delete(0, tk.END)
        for c in customers:
            orders = c.get('total_orders', 0)
            spent = c.get('total_spent', 0)
            self.customers_listbox.insert(tk.END,
                f"{c['id']} | {c['name']} | {c['phone'] or 'N/A'} | {c['email'] or 'N/A'} | Orders: {orders} | Spent: ${spent:.2f}")

    def export_customers(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export Customers"
            )
            if not file_path:
                return
            
            customers = search_customer("%")
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Name', 'Phone', 'Email', 'Address', 'Total Orders', 'Total Spent', 'Created'])
                for c in customers:
                    writer.writerow([
                        c['id'], c['name'], c.get('phone', ''), c.get('email', ''),
                        c.get('address', ''), c.get('total_orders', 0), c.get('total_spent', 0),
                        c.get('created_at', '')
                    ])
            messagebox.showinfo("Success", f"Customers exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def view_customer_history(self):
        sel = self.customers_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Customer", "Please select a customer first")
            return
        
        text = self.customers_listbox.get(sel[0])
        cid = int(text.split("|")[0].strip())
        customer = get_customer(cid)
        
        if not customer:
            return
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT * FROM orders WHERE customer_id=? ORDER BY created_at DESC""", (cid,))
        orders = cur.fetchall()
        conn.close()
        
        win = tk.Toplevel(self)
        win.title(f"Order History - {customer['name']}")
        win.geometry("800x500")
        
        info_frame = ttk.Frame(win, padding=10)
        info_frame.pack(fill="x")
        ttk.Label(info_frame, text=f"Customer: {customer['name']}", 
                 font=("Arial", 14, "bold")).pack(anchor="w")
        ttk.Label(info_frame, text=f"Total Orders: {customer.get('total_orders', 0)} | Total Spent: ${customer.get('total_spent', 0):.2f}", 
                 font=("Arial", 10)).pack(anchor="w")
        
        columns = ('Order #', 'Date', 'Total', 'Status')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        for order in orders:
            tree.insert('', 'end', values=(
                order['order_number'], order['created_at'], 
                f"${order['total_amount']:.2f}", order['status']
            ))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

        def delete_item():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            if not messagebox.askyesno("Confirm Delete", 
                f"Are you sure you want to delete:\n\n{item['sku']} - {item['name']}\n\nThis action cannot be undone!"):
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("DELETE FROM items WHERE id=?", (item['id'],))
                cur.execute("DELETE FROM transactions WHERE item_id=?", (item['id'],))
                conn.commit()
                conn.close()
                messagebox.showinfo("Deleted", "Item deleted successfully")
                refresh_list()
                details.delete("1.0", tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete item: {str(e)}")

        def export_inventory():
            try:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    title="Export Inventory"
                )
                if not file_path:
                    return
                
                items = list_items()
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['SKU', 'Name', 'Category', 'Supplier', 'Unit Price', 'Quantity', 'Min Quantity', 'Total Value', 'Notes'])
                    for item in items:
                        writer.writerow([
                            item['sku'], item['name'], item.get('category', ''), item.get('supplier', ''),
                            item['unit_price'], item['quantity'], item['min_quantity'],
                            item['unit_price'] * item['quantity'], item['notes'] or ''
                        ])
                messagebox.showinfo("Success", f"Inventory exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def create_order_window(self):
        win = tk.Toplevel(self)
        win.title("Create New Order")
        win.geometry("950x750")
        
        # Customer section
        customer_frame = ttk.LabelFrame(win, text="Customer Information", padding=10)
        customer_frame.pack(fill="x", padx=10, pady=10)
        
        search_frame = ttk.Frame(customer_frame)
        search_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=5)
        
        ttk.Label(search_frame, text="Search Customer:").pack(side="left", padx=5)
        customer_search_var = tk.StringVar()
        customer_search = ttk.Entry(search_frame, textvariable=customer_search_var, width=30)
        customer_search.pack(side="left", padx=5)
        
        customer_list = tk.Listbox(customer_frame, height=3, width=60, font=("Arial", 9))
        customer_list.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        
        selected_customer = {"id": None}
        
        def search_customers(event=None):
            query = customer_search_var.get()
            if len(query) < 2:
                return
            customers = search_customer(query)
            customer_list.delete(0, tk.END)
            for c in customers:
                customer_list.insert(tk.END, f"{c['id']} | {c['name']} | {c['phone'] or 'N/A'} | {c['email'] or 'N/A'}")
        
        def select_customer(event=None):
            sel = customer_list.curselection()
            if not sel:
                return
            text = customer_list.get(sel[0])
            cid = int(text.split("|")[0].strip())
            customer = get_customer(cid)
            if customer:
                selected_customer["id"] = customer["id"]
                name_var.set(customer["name"])
                phone_var.set(customer["phone"] or "")
                email_var.set(customer["email"] or "")
                address_var.set(customer["address"] or "")
        
        customer_search.bind("<KeyRelease>", search_customers)
        customer_list.bind("<<ListboxSelect>>", select_customer)
        
        ttk.Button(search_frame, text="➕ New Customer", 
                  command=lambda: self.create_new_customer_inline(selected_customer, name_var, phone_var, email_var, address_var)).pack(side="left", padx=5)
        
        # Customer details
        details_frame = ttk.Frame(customer_frame)
        details_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Label(details_frame, text="Name:*").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=name_var, width=35).grid(row=0, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Phone:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        phone_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=phone_var, width=35).grid(row=1, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Email:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        email_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=email_var, width=35).grid(row=2, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Address:").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        address_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=address_var, width=50).grid(row=3, column=1, columnspan=2, sticky="ew", pady=3)
        
        # Items section
        items_frame = ttk.LabelFrame(win, text="Order Items", padding=10)
        items_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Item search
        search_frame = ttk.Frame(items_frame)
        search_frame.pack(fill="x", pady=5)
        
        ttk.Label(search_frame, text="Item ID/SKU:").pack(side="left", padx=5)
        item_search_var = tk.StringVar()
        item_search = ttk.Entry(search_frame, textvariable=item_search_var, width=20)
        item_search.pack(side="left", padx=5)
        
        ttk.Label(search_frame, text="Quantity:").pack(side="left", padx=5)
        quantity_var = tk.StringVar(value="1")
        quantity_entry = ttk.Entry(search_frame, textvariable=quantity_var, width=10)
        quantity_entry.pack(side="left", padx=5)
        
        order_items = []
        
        def add_item_to_order():
            item_key = item_search_var.get().strip()
            if not item_key:
                messagebox.showwarning("Warning", "Enter item ID or SKU")
                return
            
            item = get_item_by_sku_or_id(item_key)
            if not item:
                messagebox.showerror("Error", "Item not found")
                return
            
            try:
                qty = int(quantity_var.get())
                if qty <= 0:
                    raise ValueError()
            except:
                messagebox.showerror("Error", "Invalid quantity")
                return
            
            if item['quantity'] < qty:
                if not messagebox.askyesno("Warning", f"Only {item['quantity']} units available. Continue anyway?"):
                    return
            
            subtotal = item['unit_price'] * qty
            order_items.append({
                'item_id': item['id'],
                'sku': item['sku'],
                'name': item['name'],
                'quantity': qty,
                'unit_price': item['unit_price'],
                'subtotal': subtotal
            })
            
            refresh_order_items()
            item_search_var.set("")
            quantity_var.set("1")
        
        ttk.Button(search_frame, text="➕ Add Item", command=add_item_to_order, 
                  style="Success.TButton").pack(side="left", padx=5)
        
        # Order items tree
        columns = ('SKU', 'Name', 'Qty', 'Unit Price', 'Subtotal')
        tree_frame = ttk.Frame(items_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)
        
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")
        
        items_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=items_tree.yview)
        
        for col in columns:
            items_tree.heading(col, text=col)
            items_tree.column(col, width=100)
        items_tree.pack(fill="both", expand=True)
        
        total_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(items_frame, textvariable=total_var, font=("Arial", 14, "bold"), foreground="#0078D7").pack(pady=5)
        
        def refresh_order_items():
            for item in items_tree.get_children():
                items_tree.delete(item)
            
            total = 0
            for item in order_items:
                items_tree.insert('', 'end', values=(
                    item['sku'], item['name'], item['quantity'], 
                    f"${item['unit_price']:.2f}", f"${item['subtotal']:.2f}"
                ))
                total += item['subtotal']
            total_var.set(f"Total: ${total:.2f}")
        
        def remove_selected_item():
            selected = items_tree.selection()
            if not selected:
                return
            index = items_tree.index(selected[0])
            order_items.pop(index)
            refresh_order_items()
        
        ttk.Button(items_frame, text="🗑️ Remove Selected", command=remove_selected_item, 
                  style="Danger.TButton").pack(pady=5)
        
        # Notes
        notes_frame = ttk.Frame(win, padding=10)
        notes_frame.pack(fill="x")
        ttk.Label(notes_frame, text="Order Notes:").pack(anchor="w")
        notes_text = tk.Text(notes_frame, height=3)
        notes_text.pack(fill="x")
        
        # Submit button
        def submit_order():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Customer name is required")
                return
            
            if not order_items:
                messagebox.showerror("Error", "Add at least one item")
                return
            
            # Validate email if provided
            if email_var.get() and not validate_email(email_var.get()):
                messagebox.showerror("Error", "Invalid email format")
                return
            
            conn = get_conn()
            cur = conn.cursor()
            
            try:
                # Create or update customer
                if selected_customer["id"]:
                    cur.execute("""UPDATE customers SET name=?, phone=?, email=?, address=? WHERE id=?""",
                               (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), selected_customer["id"]))
                    customer_id = selected_customer["id"]
                else:
                    cur.execute("""INSERT INTO customers (name, phone, email, address, created_at, total_orders, total_spent) 
                                  VALUES (?, ?, ?, ?, ?, 0, 0)""",
                               (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), now_str()))
                    customer_id = cur.lastrowid
                
                # Calculate total
                total = sum(item['subtotal'] for item in order_items)
                
                # Create order
                order_number = generate_order_number()
                cur.execute("""INSERT INTO orders (order_number, customer_id, total_amount, status, created_at, user_id, notes)
                              VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (order_number, customer_id, total, 'Pending', now_str(), self.current_user['id'], 
                            notes_text.get("1.0", tk.END).strip()))
                order_id = cur.lastrowid
                
                # Add order items and update inventory
                for item in order_items:
                    cur.execute("""INSERT INTO order_items (order_id, item_id, quantity, unit_price, subtotal)
                                  VALUES (?, ?, ?, ?, ?)""",
                               (order_id, item['item_id'], item['quantity'], item['unit_price'], item['subtotal']))
                    
                    # Update inventory
                    cur.execute("UPDATE items SET quantity = quantity - ?, last_updated=? WHERE id = ?",
                               (item['quantity'], now_str(), item['item_id']))
                    
                    # Record transaction
                    cur.execute("""INSERT INTO transactions (item_id, change, type, note, timestamp, user_id)
                                  VALUES (?, ?, ?, ?, ?, ?)""",
                               (item['item_id'], -item['quantity'], 'order', f'Order {order_number}', now_str(), self.current_user['id']))
                
                # Update customer stats
                cur.execute("""UPDATE customers SET total_orders = total_orders + 1, total_spent = total_spent + ? 
                              WHERE id = ?""", (total, customer_id))
                
                conn.commit()
                messagebox.showinfo("Success", f"Order {order_number} created successfully!\nTotal: ${total:.2f}")
                win.destroy()
                self.refresh_orders_list()
                
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error", f"Failed to create order: {str(e)}")
            finally:
                conn.close()
        
        btn_frame = ttk.Frame(win, padding=10)
        btn_frame.pack()
        ttk.Button(btn_frame, text="✅ Create Order", command=submit_order, 
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

        role = self.current_user['role']
        if role == "admin":
            ttk.Button(action_frame, text="➕ Add Item", command=add_item, 
                      style="Success.TButton").pack(side="left", padx=4)
            ttk.Button(action_frame, text="🗑️ Delete Item", command=delete_item, 
                      style="Danger.TButton").pack(side="left", padx=4)
        
        ttk.Button(action_frame, text="📊 Adjust Stock", command=adjust_stock).pack(side="left", padx=4)
        ttk.Button(action_frame, text="⚠️ Low Stock", command=self.show_low_stock_detailed).pack(side="left", padx=4)
        ttk.Button(action_frame, text="📥 Export CSV", command=export_inventory).pack(side="left", padx=4)
        ttk.Button(action_frame, text="🔄 Refresh", command=refresh_list).pack(side="left", padx=4)

    def create_orders_tab(self, parent):
        # Top buttons
        btn_frame = ttk.Frame(parent, padding=8)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="➕ Create New Order", command=self.create_order_window,
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Refresh", command=lambda: self.refresh_orders_list()).pack(side="left", padx=5)
        
        # Filter frame
        filter_frame = ttk.Frame(parent, padding=8)
        filter_frame.pack(fill="x")
        ttk.Label(filter_frame, text="Filter by Status:").pack(side="left", padx=5)
        
        self.order_status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.order_status_var, 
                                    values=["All", "Pending", "Processing", "Completed", "Cancelled"],
                                    state="readonly", width=15)
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_orders_list())
        
        # Orders listbox
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.orders_listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                                         selectbackground="#0078D7", selectforeground="white",
                                         font=("Arial", 9), yscrollcommand=scrollbar.set)
        self.orders_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.orders_listbox.yview)
        
        self.orders_listbox.bind("<Double-Button-1>", lambda e: self.view_order_details())
        
        # Action buttons
        action_frame = ttk.Frame(parent, padding=8)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="👁️ View Details", command=self.view_order_details).pack(side="left", padx=5)
        ttk.Button(action_frame, text="✏️ Update Status", command=self.update_order_status).pack(side="left", padx=5)
        ttk.Button(action_frame, text="📥 Export Orders", command=self.export_orders).pack(side="left", padx=5)
        
        self.refresh_orders_list()

    def refresh_orders_list(self):
        status = self.order_status_var.get()
        status_filter = None if status == "All" else status
        orders = list_orders(status_filter)
        
        self.orders_listbox.delete(0, tk.END)
        for order in orders:
            status_emoji = {"Pending": "⏳", "Processing": "🔄", "Completed": "✅", "Cancelled": "❌"}.get(order['status'], "")
            self.orders_listbox.insert(tk.END, 
                f"{status_emoji} {order['order_number']} | {order['customer_name']} | ${order['total_amount']:.2f} | {order['status']} | {order['created_at']}")

    def export_orders(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export Orders"
            )
            if not file_path:
                return
            
            status = self.order_status_var.get()
            status_filter = None if status == "All" else status
            orders = list_orders(status_filter, limit=10000)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Order Number', 'Customer', 'Phone', 'Total', 'Status', 'Created', 'User'])
                for order in orders:
                    writer.writerow([
                        order['order_number'], order['customer_name'], order.get('customer_phone', ''),
                        order['total_amount'], order['status'], order['created_at'], order.get('username', '')
                    ])
            messagebox.showinfo("Success", f"Orders exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from collections import defaultdict
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def now_str():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

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
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
    
    conn.close()

def validate_email(email):
    """Basic email validation"""
    if not email:
        return True
    return '@' in email and '.' in email.split('@')[1]

def validate_phone(phone):
    """Basic phone validation"""
    if not phone:
        return True
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) >= 10

def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_user_field(user_id, field, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()

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
        cur.execute("SELECT * FROM items WHERE id=?", (int(key),))
    else:
        cur.execute("SELECT * FROM items WHERE sku=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row

def generate_order_number():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD-{timestamp}"

def search_customer(query):
    conn = get_conn()
    cur = conn.cursor()
    qlike = f"%{query}%"
    cur.execute("""SELECT * FROM customers 
                   WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                   ORDER BY name""", (qlike, qlike, qlike))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    return row

def list_orders(status_filter=None, limit=100):
    conn = get_conn()
    cur = conn.cursor()
    if status_filter:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       WHERE o.status=?
                       ORDER BY o.created_at DESC""", (status_filter,))
    else:
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone as customer_phone, u.username
                       FROM orders o
                       LEFT JOIN customers c ON o.customer_id=c.id
                       LEFT JOIN users u ON o.user_id=u.id
                       ORDER BY o.created_at DESC LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_order_details(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT oi.*, i.sku, i.name as item_name
                   FROM order_items oi
                   LEFT JOIN items i ON oi.item_id=i.id
                   WHERE oi.order_id=?""", (order_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

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

def get_sales_report(start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if start_date and end_date:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders 
                       WHERE status='Completed' AND created_at BETWEEN ? AND ?""", 
                    (start_date, end_date))
    else:
        cur.execute("""SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
                       AVG(total_amount) as avg_order_value
                       FROM orders WHERE status='Completed'""")
    
    report = cur.fetchone()
    conn.close()
    return report

def get_top_selling_items(limit=10):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT i.name, i.sku, SUM(oi.quantity) as total_sold, 
                   SUM(oi.subtotal) as total_revenue
                   FROM order_items oi
                   JOIN items i ON oi.item_id = i.id
                   JOIN orders o ON oi.order_id = o.id
                   WHERE o.status = 'Completed'
                   GROUP BY i.id
                   ORDER BY total_sold DESC
                   LIMIT ?""", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V.A.V.H Studio - Advanced Inventory & Order Management")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.configure(bg="white")
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="white")
        self.style.configure("TLabel", background="white", foreground="black")
        self.style.configure("TButton", background="#0078D7", foreground="white", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#3399FF")])
        self.style.configure("Success.TButton", background="#28A745", foreground="white")
        self.style.configure("Danger.TButton", background="#DC3545", foreground="white")
        
        self.current_user = None
        self.create_login_screen()

    def create_login_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="V.A.V.H Studio", font=("Arial", 24, "bold"), 
                 foreground="#0078D7").grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(frame, text="Advanced Inventory Management", font=("Arial", 12), 
                 foreground="#666").grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
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
                error_label.config(text="Please enter both username and password")
                return
            
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                error_label.config(text="Incorrect username or password")
                pass_entry.delete(0, tk.END)
                return
            
            self.current_user = dict(user)
            self.create_main_ui()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Login", command=do_login).pack()
        
        ttk.Label(frame, text="Default: admin/admin or clerk/clerk", 
                 font=("Arial", 9), foreground="#999").grid(row=6, column=0, columnspan=2)
        
        self.bind("<Return>", do_login)

    def create_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        
        # Top bar
        top = ttk.Frame(self, style="TFrame")
        top.pack(fill="x", padx=10, pady=5)
        
        user_frame = ttk.Frame(top)
        user_frame.pack(side="left")
        ttk.Label(user_frame, text=f"👤 {self.current_user['username']}", 
                 foreground="#0078D7", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ttk.Label(user_frame, text=f"({self.current_user['role']})", 
                 foreground="#666", font=("Arial", 9)).pack(side="left")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side="right")
        
        if self.current_user["role"] == "admin":
            ttk.Button(btn_frame, text="Create User", command=self.create_user).pack(side="left", padx=2)
        
        ttk.Button(btn_frame, text="Profile", command=self.show_profile).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Logout", command=self.logout, 
                  style="Danger.TButton").pack(side="left", padx=2)

        # Notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="📊 Dashboard")
        self.create_dashboard_tab(dashboard_frame)
        
        # Inventory tab
        inventory_frame = ttk.Frame(notebook)
        notebook.add(inventory_frame, text="📦 Inventory")
        self.create_inventory_tab(inventory_frame)
        
        # Orders tab
        orders_frame = ttk.Frame(notebook)
        notebook.add(orders_frame, text="🛒 Orders")
        self.create_orders_tab(orders_frame)
        
        # Customers tab
        customers_frame = ttk.Frame(notebook)
        notebook.add(customers_frame, text="👥 Customers")
        self.create_customers_tab(customers_frame)
        
        # Categories & Suppliers tab
        manage_frame = ttk.Frame(notebook)
        notebook.add(manage_frame, text="⚙️ Manage")
        self.create_manage_tab(manage_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(notebook)
        notebook.add(reports_frame, text="📈 Reports")
        self.create_reports_tab(reports_frame)

    def create_dashboard_tab(self, parent):
        # Header
        header = ttk.Frame(parent, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Dashboard Overview", 
                 font=("Arial", 16, "bold"), foreground="#0078D7").pack(anchor="w")
        ttk.Label(header, text=f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                 font=("Arial", 9), foreground="#666").pack(anchor="w")
        
        # Stats cards
        stats_frame = ttk.Frame(parent, padding=10)
        stats_frame.pack(fill="x")
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Total items
        cur.execute("SELECT COUNT(*), SUM(quantity) FROM items")
        items_data = cur.fetchone()
        
        # Low stock items
        cur.execute("SELECT COUNT(*) FROM items WHERE min_quantity > 0 AND quantity <= min_quantity")
        low_stock = cur.fetchone()[0]
        
        # Total orders
        cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status='Completed'")
        orders_data = cur.fetchone()
        
        # Pending orders
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
        pending = cur.fetchone()[0]
        
        # Total customers
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
        
        conn.close()
        
        # Create stat cards
        cards = [
            ("Total Items", items_data[0], f"{items_data[1] or 0} units in stock", "#0078D7"),
            ("Low Stock Alerts", low_stock, "Items need reorder", "#DC3545" if low_stock > 0 else "#28A745"),
            ("Completed Orders", orders_data[0], f"${orders_data[1] or 0:.2f} revenue", "#28A745"),
            ("Pending Orders", pending, "Awaiting processing", "#FFC107" if pending > 0 else "#28A745"),
            ("Total Customers", customers, "In database", "#17A2B8"),
        ]
        
        for i, (title, value, subtitle, color) in enumerate(cards):
            card = ttk.LabelFrame(stats_frame, text=title, padding=15)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="ew")
            
            ttk.Label(card, text=str(value), font=("Arial", 24, "bold"), 
                     foreground=color).pack()
            ttk.Label(card, text=subtitle, font=("Arial", 9), 
                     foreground="#666").pack()
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        
        # Recent activity
        activity_frame = ttk.LabelFrame(parent, text="Recent Activity", padding=10)
        activity_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text = scrolledtext.ScrolledText(activity_frame, height=10, wrap=tk.WORD)
        text.pack(fill="both", expand=True)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT t.timestamp, u.username, i.name, t.change, t.type, t.note
                      FROM transactions t
                      LEFT JOIN users u ON t.user_id = u.id
                      LEFT JOIN items i ON t.item_id = i.id
                      ORDER BY t.timestamp DESC LIMIT 20""")
        transactions = cur.fetchall()
        conn.close()
        
        for t in transactions:
            text.insert(tk.END, f"[{t['timestamp']}] {t['username']}: {t['name']} - {t['change']:+d} ({t['type']}) - {t['note']}\n")
        
        text.config(state="disabled")
        
        # Quick actions
        actions_frame = ttk.Frame(parent, padding=10)
        actions_frame.pack(fill="x")
        
        ttk.Button(actions_frame, text="🔄 Refresh Dashboard", 
                  command=lambda: self.create_dashboard_tab(parent)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="📊 View Full Reports", 
                  command=lambda: self.focus_tab(5)).pack(side="left", padx=5)
        ttk.Button(actions_frame, text="⚠️ View Low Stock", 
                  command=self.show_low_stock_detailed).pack(side="left", padx=5)

    def focus_tab(self, index):
        """Helper to switch to a specific tab"""
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Notebook):
                widget.select(index)
                break

    def show_low_stock_detailed(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT sku, name, quantity, min_quantity, unit_price 
                      FROM items WHERE min_quantity > 0 AND quantity <= min_quantity 
                      ORDER BY quantity ASC""")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            messagebox.showinfo("Low Stock", "No low-stock items found!")
            return
        
        win = tk.Toplevel(self)
        win.title("Low Stock Report")
        win.geometry("700x400")
        
        columns = ('SKU', 'Name', 'Current', 'Min', 'Unit Price', 'Reorder Cost')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        total_cost = 0
        for row in rows:
            reorder_qty = row['min_quantity'] - row['quantity'] + 5
            cost = reorder_qty * row['unit_price']
            total_cost += cost
            tree.insert('', 'end', values=(
                row['sku'], row['name'], row['quantity'], row['min_quantity'],
                f"${row['unit_price']:.2f}", f"${cost:.2f}"
            ))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(win, text=f"Total Estimated Reorder Cost: ${total_cost:.2f}", 
                 font=("Arial", 12, "bold"), foreground="#DC3545").pack(pady=10)

    def create_inventory_tab(self, parent):
        pan = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pan.pack(fill="both", expand=True)
        
        left = ttk.Frame(pan, width=400)
        right = ttk.Frame(pan)
        pan.add(left, weight=1)
        pan.add(right, weight=2)

        # Search frame
        search_frame = ttk.Frame(left, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="🔍 Search SKU/Name:", font=("Arial", 10, "bold")).pack(anchor="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 10))
        search_entry.pack(fill="x", pady=5)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                           selectbackground="#0078D7", selectforeground="white",
                           font=("Arial", 9), yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def refresh_list(event=None):
            q = search_var.get() or "%"
            items = list_items(q)
            listbox.delete(0, tk.END)
            for it in items:
                status = "🔴" if it['min_quantity'] > 0 and it['quantity'] <= it['min_quantity'] else "🟢"
                listbox.insert(tk.END, f"{status} {it['sku']} | {it['name']} | Qty: {it['quantity']}")

        search_entry.bind("<KeyRelease>", lambda e: refresh_list())
        refresh_list()

        # Details panel
        details_frame = ttk.LabelFrame(right, text="Item Details", padding=10)
        details_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        details = tk.Text(details_frame, height=15, bg="white", fg="black", 
                         insertbackground="black", font=("Courier", 10))
        details.pack(fill="both", expand=True)

        def show_selected(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            # Remove emoji and get SKU
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                details.delete("1.0", tk.END)
                details.insert(tk.END, "Item not found")
                return
            
            status = "⚠️ LOW STOCK" if item['min_quantity'] > 0 and item['quantity'] <= item['min_quantity'] else "✓ In Stock"
            
            out = [
                f"{'='*50}",
                f"SKU: {item['sku']}",
                f"Name: {item['name']}",
                f"{'='*50}",
                f"Category: {item.get('category') or 'None'}",
                f"Supplier: {item.get('supplier') or 'None'}",
                f"",
                f"Unit Price: ${item['unit_price']:.2f}",
                f"Quantity: {item['quantity']} {status}",
                f"Min Quantity: {item['min_quantity']}",
                f"Total Value: ${item['unit_price'] * item['quantity']:.2f}",
                f"",
                f"Created: {item.get('created_at') or 'N/A'}",
                f"Last Updated: {item.get('last_updated') or 'N/A'}",
                f"",
                f"Notes: {item['notes'] or 'None'}"
            ]
            details.delete("1.0", tk.END)
            details.insert(tk.END, "\n".join(out))

        listbox.bind("<<ListboxSelect>>", show_selected)

        # Action buttons
        action_frame = ttk.Frame(right, padding=8)
        action_frame.pack(fill="x", padx=8, pady=8)

        def adjust_stock():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            try:
                change_str = simpledialog.askstring("Adjust Stock", 
                    f"Current quantity: {item['quantity']}\nEnter change (negative to decrease):", 
                    parent=self)
                if not change_str:
                    return
                change = int(change_str)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number")
                return
            
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            new_q = item['quantity'] + change
            
            if new_q < 0:
                messagebox.showerror("Error", "Resulting quantity would be negative")
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE items SET quantity=?, last_updated=? WHERE id=?", 
                          (new_q, now_str(), item['id']))
                cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                          (item['id'], change, 'adjust', note, now_str(), self.current_user['id']))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", f"New quantity: {new_q}")
                refresh_list()
                show_selected()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update stock: {str(e)}")

        def add_item():
            win = tk.Toplevel(self)
            win.title("Add New Item")
            win.geometry("500x600")
            
            # Form fields
            fields_frame = ttk.Frame(win, padding=20)
            fields_frame.pack(fill="both", expand=True)
            
            ttk.Label(fields_frame, text="SKU:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5, padx=5)
            sku_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=sku_var, width=30).grid(row=0, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Name:*", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5, padx=5)
            name_var = tk.StringVar()
            ttk.Entry(fields_frame, textvariable=name_var, width=30).grid(row=1, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Category:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5, padx=5)
            categories = list_categories()
            cat_var = tk.StringVar()
            cat_combo = ttk.Combobox(fields_frame, textvariable=cat_var, width=28)
            cat_combo['values'] = ['None'] + [c['name'] for c in categories]
            cat_combo.set('None')
            cat_combo.grid(row=2, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Supplier:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="e", pady=5, padx=5)
            suppliers = list_suppliers()
            sup_var = tk.StringVar()
            sup_combo = ttk.Combobox(fields_frame, textvariable=sup_var, width=28)
            sup_combo['values'] = ['None'] + [s['name'] for s in suppliers]
            sup_combo.set('None')
            sup_combo.grid(row=3, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Unit Price:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="e", pady=5, padx=5)
            price_var = tk.StringVar(value="0.00")
            ttk.Entry(fields_frame, textvariable=price_var, width=30).grid(row=4, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Initial Quantity:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="e", pady=5, padx=5)
            qty_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=qty_var, width=30).grid(row=5, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Min Quantity:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="e", pady=5, padx=5)
            min_var = tk.StringVar(value="0")
            ttk.Entry(fields_frame, textvariable=min_var, width=30).grid(row=6, column=1, sticky="w", pady=5)
            
            ttk.Label(fields_frame, text="Notes:", font=("Arial", 10, "bold")).grid(row=7, column=0, sticky="ne", pady=5, padx=5)
            notes_text = tk.Text(fields_frame, height=4, width=30)
            notes_text.grid(row=7, column=1, sticky="w", pady=5)
            
            def save_item():
                sku = sku_var.get().strip()
                name = name_var.get().strip()
                
                if not sku or not name:
                    messagebox.showerror("Error", "SKU and Name are required")
                    return
                
                try:
                    unit_price = float(price_var.get())
                    quantity = int(qty_var.get())
                    min_q = int(min_var.get())
                except ValueError:
                    messagebox.showerror("Error", "Invalid price or quantity")
                    return
                
                # Get category and supplier IDs
                cat_id = None
                sup_id = None
                
                cat_name = cat_var.get()
                if cat_name != 'None':
                    cat = next((c for c in categories if c['name'] == cat_name), None)
                    if cat:
                        cat_id = cat['id']
                
                sup_name = sup_var.get()
                if sup_name != 'None':
                    sup = next((s for s in suppliers if s['name'] == sup_name), None)
                    if sup:
                        sup_id = sup['id']
                
                notes = notes_text.get("1.0", tk.END).strip()
                
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""INSERT INTO items (sku,name,category_id,supplier_id,unit_price,quantity,min_quantity,notes,created_at,last_updated) 
                                  VALUES (?,?,?,?,?,?,?,?,?,?)""",
                              (sku, name, cat_id, sup_id, unit_price, quantity, min_q, notes, now_str(), now_str()))
                    item_id = cur.lastrowid
                    if quantity > 0:
                        cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                                  (item_id, quantity, 'init', 'Initial stock', now_str(), self.current_user['id']))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Item added successfully!")
                    win.destroy()
                    refresh_list()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error", "SKU must be unique")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add item: {str(e)}")
            
            btn_frame = ttk.Frame(win)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="Save Item", command=save_item, 
                      style="Success.TButton").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

    def create_new_customer_inline(self, selected_customer, name_var, phone_var, email_var, address_var):
        name = simpledialog.askstring("New Customer", "Customer Name:*", parent=self)
        if not name:
            return
        phone = simpledialog.askstring("New Customer", "Phone:", parent=self) or ""
        email = simpledialog.askstring("New Customer", "Email:", parent=self) or ""
        
        if email and not validate_email(email):
            messagebox.showerror("Error", "Invalid email format")
            return
        
        address = simpledialog.askstring("New Customer", "Address:", parent=self) or ""
        
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""INSERT INTO customers (name, phone, email, address, created_at, total_orders, total_spent) 
                          VALUES (?, ?, ?, ?, ?, 0, 0)""",
                       (name, phone, email, address, now_str()))
            customer_id = cur.lastrowid
            conn.commit()
            conn.close()
            
            selected_customer["id"] = customer_id
            name_var.set(name)
            phone_var.set(phone)
            email_var.set(email)
            address_var.set(address)
            messagebox.showinfo("Success", "Customer created!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create customer: {str(e)}")

    def view_order_details(self):
        sel = self.orders_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Order", "Please select an order first")
            return
        
        text = self.orders_listbox.get(sel[0])
        order_number = text.split("|")[0].strip().split()[-1]
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT o.*, c.name as customer_name, c.phone, c.email, c.address, u.username
                      FROM orders o
                      LEFT JOIN customers c ON o.customer_id=c.id
                      LEFT JOIN users u ON o.user_id=u.id
                      WHERE o.order_number=?""", (order_number,))
        order = cur.fetchone()
        
        if not order:
            messagebox.showerror("Error", "Order not found")
            conn.close()
            return
        
        items = get_order_details(order['id'])
        conn.close()
        
        win = tk.Toplevel(self)
        win.title(f"Order Details - {order_number}")
        win.geometry("800x650")
        
        # Order info
        info_frame = ttk.LabelFrame(win, text="Order Information", padding=15)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        status_color = {"Pending": "#FFC107", "Processing": "#17A2B8", 
                       "Completed": "#28A745", "Cancelled": "#DC3545"}.get(order['status'], "#666")
        
        info_text = f"""Order Number: {order['order_number']}
Status: {order['status']}
Date: {order['created_at']}
Created by: {order['username']}
Total Amount: ${order['total_amount']:.2f}

Customer: {order['customer_name']}
Phone: {order['phone'] or 'N/A'}
Email: {order['email'] or 'N/A'}
Address: {order['address'] or 'N/A'}

Notes: {order['notes'] or 'None'}"""
        
        ttk.Label(info_frame, text=info_text, justify="left", font=("Courier", 10)).pack(anchor="w")
        
        # Items
        items_frame = ttk.LabelFrame(win, text="Order Items", padding=10)
        items_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ('SKU', 'Name', 'Qty', 'Unit Price', 'Subtotal')
        tree = ttk.Treeview(items_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for item in items:
            tree.insert('', 'end', values=(
                item['sku'], item['item_name'], item['quantity'],
                f"${item['unit_price']:.2f}", f"${item['subtotal']:.2f}"
            ))
        
        tree.pack(fill="both", expand=True)
        
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    def add_customer(self):
        win = tk.Toplevel(self)
        win.title("Add Customer")
        win.geometry("450x350")
        
        frame = ttk.Frame(win, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Name:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=35).grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Phone:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5)
        phone_var = tk.StringVar()
        ttk.Entry(frame, textvariable=phone_var, width=35).grid(row=1, column=1, pady=5)
        
        ttk.Label(frame, text="Email:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5)
        email_var = tk.StringVar()
        ttk.Entry(frame, textvariable=email_var, width=35).grid(row=2, column=1, pady=5)
        
        ttk.Label(frame, text="Address:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="ne", pady=5)
        address_text = tk.Text(frame, height=4, width=35)
        address_text.grid(row=3, column=1, pady=5)
        
        ttk.Label(frame, text="Notes:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="ne", pady=5)
        notes_text = tk.Text(frame, height=3, width=35)
        notes_text.grid(row=4, column=1, pady=5)
        
        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            
            email = email_var.get().strip()
            if email and not validate_email(email):
                messagebox.showerror("Error", "Invalid email format")
                return
            
            phone = phone_var.get().strip()
            if phone and not validate_phone(phone):
                messagebox.showwarning("Warning", "Phone number seems invalid")
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("""INSERT INTO customers (name, phone, email, address, created_at, notes, total_orders, total_spent)
                              VALUES (?, ?, ?, ?, ?, ?, 0, 0)""",
                           (name, phone, email, address_text.get("1.0", tk.END).strip(), 
                            now_str(), notes_text.get("1.0", tk.END).strip()))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Customer added successfully!")
                win.destroy()
                self.refresh_customers_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add customer: {str(e)}")
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Save", command=save, style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

    def edit_customer(self):
        sel = self.customers_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Customer", "Please select a customer first")
            return
        
        text = self.customers_listbox.get(sel[0])
        cid = int(text.split("|")[0].strip())
        customer = get_customer(cid)
        
        if not customer:
            return
        
        win = tk.Toplevel(self)
        win.title("Edit Customer")
        win.geometry("450x350")
        
        frame = ttk.Frame(win, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Name:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5)
        name_var = tk.StringVar(value=customer['name'])
        ttk.Entry(frame, textvariable=name_var, width=35).grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Phone:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5)
        phone_var = tk.StringVar(value=customer['phone'] or "")
        ttk.Entry(frame, textvariable=phone_var, width=35).grid(row=1, column=1, pady=5)
        
        ttk.Label(frame, text="Email:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5)
        email_var = tk.StringVar(value=customer['email'] or "")
        ttk.Entry(frame, textvariable=email_var, width=35).grid(row=2, column=1, pady=5)
        
        ttk.Label(frame, text="Address:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="ne", pady=5)
        address_text = tk.Text(frame, height=4, width=35)
        address_text.insert("1.0", customer['address'] or "")
        address_text.grid(row=3, column=1, pady=5)
        
        ttk.Label(frame, text="Notes:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="ne", pady=5)
        notes_text = tk.Text(frame, height=3, width=35)
        notes_text.insert("1.0", customer.get('notes', '') or "")
        notes_text.grid(row=4, column=1, pady=5)
        
        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            
            email = email_var.get().strip()
            if email and not validate_email(email):
                messagebox.showerror("Error", "Invalid email format")
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("""UPDATE customers SET name=?, phone=?, email=?, address=?, notes=? WHERE id=?""",
                           (name, phone_var.get().strip(), email, 
                            address_text.get("1.0", tk.END).strip(), 
                            notes_text.get("1.0", tk.END).strip(), cid))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Customer updated successfully!")
                win.destroy()
                self.refresh_customers_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update customer: {str(e)}")
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Save", command=save, style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

    def delete_customer(self):
        sel = self.customers_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Customer", "Please select a customer first")
            return
        
        text = self.customers_listbox.get(sel[0])
        cid = int(text.split("|")[0].strip())
        customer = get_customer(cid)
        
        if not customer:
            return
        
        # Check if customer has orders
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders WHERE customer_id=?", (cid,))
        order_count = cur.fetchone()[0]
        conn.close()
        
        if order_count > 0:
            if not messagebox.askyesno("Warning", 
                f"This customer has {order_count} orders. Deleting will remove all order history. Continue?"):
                return
        
        if messagebox.askyesno("Confirm Delete", f"Delete customer '{customer['name']}'?"):
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("DELETE FROM customers WHERE id=?", (cid,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Deleted", "Customer deleted successfully")
                self.refresh_customers_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete customer: {str(e)}")

    def create_manage_tab(self, parent):
        # Categories section
        cat_frame = ttk.LabelFrame(parent, text="Categories", padding=10)
        cat_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        cat_list_frame = ttk.Frame(cat_frame)
        cat_list_frame.pack(fill="both", expand=True)
        
        cat_scrollbar = ttk.Scrollbar(cat_list_frame)
        cat_scrollbar.pack(side="right", fill="y")
        
        cat_listbox = tk.Listbox(cat_list_frame, bg="white", fg="black",
                                 selectbackground="#0078D7", selectforeground="white",
                                 yscrollcommand=cat_scrollbar.set, height=8)
        cat_listbox.pack(side="left", fill="both", expand=True)
        cat_scrollbar.config(command=cat_listbox.yview)
        
        def refresh_categories():
            categories = list_categories()
            cat_listbox.delete(0, tk.END)
            for cat in categories:
                cat_listbox.insert(tk.END, f"{cat['id']} | {cat['name']} | {cat.get('description', '') or 'No description'}")
        
        def add_category():
            name = simpledialog.askstring("Add Category", "Category Name:", parent=self)
            if not name:
                return
            desc = simpledialog.askstring("Add Category", "Description (optional):", parent=self) or ""
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (name, desc))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Category added")
                refresh_categories()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Category name must be unique")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add category: {str(e)}")
        
        def delete_category():
            sel = cat_listbox.curselection()
            if not sel:
                return
            text = cat_listbox.get(sel[0])
            cat_id = int(text.split("|")[0].strip())
            
            if messagebox.askyesno("Confirm", "Delete this category?"):
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM categories WHERE id=?", (cat_id,))
                    conn.commit()
                    conn.close()
                    refresh_categories()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete: {str(e)}")
        
        cat_btn_frame = ttk.Frame(cat_frame)
        cat_btn_frame.pack(fill="x", pady=5)
        ttk.Button(cat_btn_frame, text="➕ Add", command=add_category).pack(side="left", padx=5)
        ttk.Button(cat_btn_frame, text="🗑️ Delete", command=delete_category).pack(side="left", padx=5)
        
        refresh_categories()
        
        # Suppliers section
        sup_frame = ttk.LabelFrame(parent, text="Suppliers", padding=10)
        sup_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        sup_list_frame = ttk.Frame(sup_frame)
        sup_list_frame.pack(fill="both", expand=True)
        
        sup_scrollbar = ttk.Scrollbar(sup_list_frame)
        sup_scrollbar.pack(side="right", fill="y")
        
        sup_listbox = tk.Listbox(sup_list_frame, bg="white", fg="black",
                                 selectbackground="#0078D7", selectforeground="white",
                                 yscrollcommand=sup_scrollbar.set, height=8)
        sup_listbox.pack(side="left", fill="both", expand=True)
        sup_scrollbar.config(command=sup_listbox.yview)
        
        def refresh_suppliers():
            suppliers = list_suppliers()
            sup_listbox.delete(0, tk.END)
            for sup in suppliers:
                sup_listbox.insert(tk.END, f"{sup['id']} | {sup['name']} | {sup.get('contact', '') or 'No contact'}")
        
        def add_supplier():
            name = simpledialog.askstring("Add Supplier", "Supplier Name:", parent=self)
            if not name:
                return
            contact = simpledialog.askstring("Add Supplier", "Contact:", parent=self) or ""
            email = simpledialog.askstring("Add Supplier", "Email:", parent=self) or ""
            address = simpledialog.askstring("Add Supplier", "Address:", parent=self) or ""
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("INSERT INTO suppliers (name, contact, email, address) VALUES (?, ?, ?, ?)", 
                          (name, contact, email, address))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Supplier added")
                refresh_suppliers()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add supplier: {str(e)}")
        
        def delete_supplier():
            sel = sup_listbox.curselection()
            if not sel:
                return
            text = sup_listbox.get(sel[0])
            sup_id = int(text.split("|")[0].strip())
            
            if messagebox.askyesno("Confirm", "Delete this supplier?"):
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM suppliers WHERE id=?", (sup_id,))
                    conn.commit()
                    conn.close()
                    refresh_suppliers()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete: {str(e)}")
        
        sup_btn_frame = ttk.Frame(sup_frame)
        sup_btn_frame.pack(fill="x", pady=5)
        ttk.Button(sup_btn_frame, text="➕ Add", command=add_supplier).pack(side="left", padx=5)
        ttk.Button(sup_btn_frame, text="🗑️ Delete", command=delete_supplier).pack(side="left", padx=5)
        
        refresh_suppliers()

    def create_reports_tab(self, parent):
        # Header
        header = ttk.Frame(parent, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Sales & Inventory Reports", 
                 font=("Arial", 16, "bold"), foreground="#0078D7").pack(anchor="w")
        
        # Sales report section
        sales_frame = ttk.LabelFrame(parent, text="Sales Report", padding=15)
        sales_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        report_text = scrolledtext.ScrolledText(sales_frame, height=15, wrap=tk.WORD, font=("Courier", 10))
        report_text.pack(fill="both", expand=True)
        
        def generate_sales_report():
            report_text.delete("1.0", tk.END)
            
            # Overall statistics
            report = get_sales_report()
            
            output = ["="*60, "SALES REPORT", "="*60, ""]
            output.append(f"Total Completed Orders: {report['total_orders'] or 0}")
            output.append(f"Total Revenue: ${report['total_revenue'] or 0:.2f}")
            output.append(f"Average Order Value: ${report['avg_order_value'] or 0:.2f}")
            output.append("\n" + "="*60)
            output.append("TOP SELLING ITEMS")
            output.append("="*60 + "\n")
            
            top_items = get_top_selling_items(10)
            if top_items:
                output.append(f"{'Item':<30} {'Units Sold':<15} {'Revenue':<15}")
                output.append("-"*60)
                for item in top_items:
                    output.append(f"{item['name'][:30]:<30} {item['total_sold']:<15} ${item['total_revenue']:<14.2f}")
            else:
                output.append("No sales data available")
            
            output.append("\n" + "="*60)
            output.append("INVENTORY STATUS")
            output.append("="*60 + "\n")
            
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""SELECT COUNT(*) as total, SUM(quantity * unit_price) as total_value 
                          FROM items""")
            inv_data = cur.fetchone()
            cur.execute("""SELECT COUNT(*) FROM items WHERE min_quantity > 0 AND quantity <= min_quantity""")
            low_stock = cur.fetchone()[0]
            conn.close()
            
            output.append(f"Total Items: {inv_data['total']}")
            output.append(f"Total Inventory Value: ${inv_data['total_value'] or 0:.2f}")
            output.append(f"Low Stock Items: {low_stock}")
            
            report_text.insert("1.0", "\n".join(output))
        
        # Buttons
        btn_frame = ttk.Frame(parent, padding=10)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="📊 Generate Report", command=generate_sales_report, 
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📥 Export Report", 
                  command=lambda: self.export_text_report(report_text)).pack(side="left", padx=5)
        
        # Generate initial report
        generate_sales_report()

    def export_text_report(self, text_widget):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Report"
            )
            if not file_path:
                return
            
            content = text_widget.get("1.0", tk.END)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            messagebox.showinfo("Success", f"Report exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def create_user(self):
        uname = simpledialog.askstring("New User", "Enter username:", parent=self)
        if not uname:
            return
        pwd = simpledialog.askstring("New User", "Enter password:", parent=self, show="*")
        if not pwd:
            return
        
        role = simpledialog.askstring("New User", "Enter role (admin/clerk/user):", parent=self)
        if role not in ("admin", "clerk", "user"):
            messagebox.showerror("Error", "Invalid role")
            return
        
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                       (uname, hash_password(pwd), role))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"User '{uname}' created with role '{role}'")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create user: {str(e)}")

    def show_profile(self):
        user = self.current_user
        win = tk.Toplevel(self)
        win.title("User Profile")
        win.geometry("500x500")
        
        header = ttk.Frame(win, padding=15)
        header.pack(fill="x")
        ttk.Label(header, text=f"Profile - {user['username']}", 
                 font=("Arial", 16, "bold"), foreground="#0078D7").pack(anchor="w")
        ttk.Label(header, text=f"Role: {user['role']}", 
                 font=("Arial", 11), foreground="#666").pack(anchor="w")
        
        form_frame = ttk.Frame(win, padding=15)
        form_frame.pack(fill="both", expand=True)
        
        ttk.Label(form_frame, text="Name:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", pady=5)
        name_var = tk.StringVar(value=user.get("name", ""))
        ttk.Entry(form_frame, textvariable=name_var, width=35).grid(row=0, column=1, pady=5)
        
        ttk.Label(form_frame, text="Phone:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="e", pady=5)
        phone_var = tk.StringVar(value=user.get("phone", ""))
        ttk.Entry(form_frame, textvariable=phone_var, width=35).grid(row=1, column=1, pady=5)
        
        ttk.Label(form_frame, text="Email:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="e", pady=5)
        email_var = tk.StringVar(value=user.get("email", ""))
        ttk.Entry(form_frame, textvariable=email_var, width=35).grid(row=2, column=1, pady=5)
        
        def save_profile():
            email = email_var.get().strip()
            if email and not validate_email(email):
                messagebox.showerror("Error", "Invalid email format")
                return
            
            try:
                update_user_field(user["id"], "name", name_var.get())
                update_user_field(user["id"], "phone", phone_var.get())
                update_user_field(user["id"], "email", email)
                messagebox.showinfo("Success", "Profile updated successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update profile: {str(e)}")
        
        ttk.Button(form_frame, text="💾 Save Profile", command=save_profile, 
                  style="Success.TButton").grid(row=3, column=0, columnspan=2, pady=15)
        
        def change_password():
            new_pwd = simpledialog.askstring("Change Password", "Enter new password:", parent=win, show="*")
            if not new_pwd:
                return
            confirm_pwd = simpledialog.askstring("Change Password", "Confirm new password:", parent=win, show="*")
            if new_pwd != confirm_pwd:
                messagebox.showerror("Error", "Passwords do not match")
                return
            
            try:
                update_user_field(user["id"], "password_hash", hash_password(new_pwd))
                messagebox.showinfo("Success", "Password changed successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to change password: {str(e)}")
        
        ttk.Button(form_frame, text="🔒 Change Password", command=change_password).grid(row=4, column=0, columnspan=2, pady=5)

        if user["role"] == "admin":
            ttk.Separator(form_frame, orient='horizontal').grid(row=5, column=0, columnspan=2, sticky="ew", pady=15)
            ttk.Label(form_frame, text="User Management", font=("Arial", 12, "bold")).grid(row=6, column=0, columnspan=2, pady=5)
            
            users = list_users()
            user_list = tk.Listbox(form_frame, height=6, width=60)
            user_list.grid(row=7, column=0, columnspan=2, pady=5)
            
            for u in users:
                user_list.insert(tk.END, f"{u['id']} | {u['username']} | {u['role']} | {u.get('email','N/A')}")
            
            def change_role():
                sel = user_list.curselection()
                if not sel:
                    return
                line = user_list.get(sel[0])
                uid = int(line.split("|")[0].strip())
                new_role = simpledialog.askstring("Change Role", "Enter new role (admin/clerk/user):", parent=win)
                if new_role in ("admin", "clerk", "user"):
                    try:
                        update_user_field(uid, "role", new_role)
                        messagebox.showinfo("Success", "User role updated")
                        win.destroy()
                        self.show_profile()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to update role: {str(e)}")
            
            ttk.Button(form_frame, text="✏️ Change User Role", command=change_role).grid(row=8, column=0, columnspan=2, pady=5)

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.current_user = None
            self.create_login_screen()


def main():
    init_db()
    app = InventoryApp()
    app.mainloop()


if __name__ == "__main__":
    main()

    def update_order_status(self):
        sel = self.orders_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Order", "Please select an order first")
            return
        
        text = self.orders_listbox.get(sel[0])
        order_number = text.split("|")[0].strip().split()[-1]
        
        win = tk.Toplevel(self)
        win.title("Update Order Status")
        win.geometry("350x200")
        
        ttk.Label(win, text=f"Order: {order_number}", font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Label(win, text="Select new status:").pack(pady=5)
        
        status_var = tk.StringVar(value="Pending")
        for status in ["Pending", "Processing", "Completed", "Cancelled"]:
            ttk.Radiobutton(win, text=status, variable=status_var, value=status).pack(anchor="w", padx=50)
        
        def save_status():
            new_status = status_var.get()
            try:
                conn = get_conn()
                cur = conn.cursor()
                
                if new_status == "Completed":
                    cur.execute("UPDATE orders SET status=?, completed_at=? WHERE order_number=?", 
                              (new_status, now_str(), order_number))
                else:
                    cur.execute("UPDATE orders SET status=? WHERE order_number=?", 
                              (new_status, order_number))
                
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Order status updated")
                win.destroy()
                self.refresh_orders_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update status: {str(e)}")
        
        ttk.Button(win, text="Save", command=save_status, style="Success.TButton").pack(pady=15)

    def create_customers_tab(self, parent):
        # Top buttons
        btn_frame = ttk.Frame(parent, padding=8)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="➕ Add Customer", command=self.add_customer, 
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Refresh", command=lambda: self.refresh_customers_list()).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📥 Export", command=self.export_customers).pack(side="left", padx=5)
        
        # Search
        search_frame = ttk.Frame(parent, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="🔍 Search:").pack(side="left", padx=5)
        self.customer_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.customer_search_var, width=30)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_customers_list())
        
        # Customers list
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.customers_listbox = tk.Listbox(list_frame, bg="white", fg="black",
                                           selectbackground="#0078D7", selectforeground="white",
                                           font=("Arial", 9), yscrollcommand=scrollbar.set)
        self.customers_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.customers_listbox.yview)
        
        self.customers_listbox.bind("<Double-Button-1>", lambda e: self.edit_customer())
        
        # Action buttons
        action_frame = ttk.Frame(parent, padding=8)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="✏️ Edit", command=self.edit_customer).pack(side="left", padx=5)
        ttk.Button(action_frame, text="🗑️ Delete", command=self.delete_customer, 
                  style="Danger.TButton").pack(side="left", padx=5)
        ttk.Button(action_frame, text="📋 View History", command=self.view_customer_history).pack(side="left", padx=5)
        
        self.refresh_customers_list()

    def refresh_customers_list(self):
        query = self.customer_search_var.get() if hasattr(self, 'customer_search_var') else ""
        customers = search_customer(query) if query else search_customer("%")
        
        self.customers_listbox.delete(0, tk.END)
        for c in customers:
            orders = c.get('total_orders', 0)
            spent = c.get('total_spent', 0)
            self.customers_listbox.insert(tk.END,
                f"{c['id']} | {c['name']} | {c['phone'] or 'N/A'} | {c['email'] or 'N/A'} | Orders: {orders} | Spent: ${spent:.2f}")

    def export_customers(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export Customers"
            )
            if not file_path:
                return
            
            customers = search_customer("%")
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Name', 'Phone', 'Email', 'Address', 'Total Orders', 'Total Spent', 'Created'])
                for c in customers:
                    writer.writerow([
                        c['id'], c['name'], c.get('phone', ''), c.get('email', ''),
                        c.get('address', ''), c.get('total_orders', 0), c.get('total_spent', 0),
                        c.get('created_at', '')
                    ])
            messagebox.showinfo("Success", f"Customers exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def view_customer_history(self):
        sel = self.customers_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Customer", "Please select a customer first")
            return
        
        text = self.customers_listbox.get(sel[0])
        cid = int(text.split("|")[0].strip())
        customer = get_customer(cid)
        
        if not customer:
            return
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""SELECT * FROM orders WHERE customer_id=? ORDER BY created_at DESC""", (cid,))
        orders = cur.fetchall()
        conn.close()
        
        win = tk.Toplevel(self)
        win.title(f"Order History - {customer['name']}")
        win.geometry("800x500")
        
        info_frame = ttk.Frame(win, padding=10)
        info_frame.pack(fill="x")
        ttk.Label(info_frame, text=f"Customer: {customer['name']}", 
                 font=("Arial", 14, "bold")).pack(anchor="w")
        ttk.Label(info_frame, text=f"Total Orders: {customer.get('total_orders', 0)} | Total Spent: ${customer.get('total_spent', 0):.2f}", 
                 font=("Arial", 10)).pack(anchor="w")
        
        columns = ('Order #', 'Date', 'Total', 'Status')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        for order in orders:
            tree.insert('', 'end', values=(
                order['order_number'], order['created_at'], 
                f"${order['total_amount']:.2f}", order['status']
            ))
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

        def delete_item():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select Item", "Please select an item first")
                return
            text = listbox.get(sel[0])
            sku = text.split("|")[0].strip().split()[-1]
            item = get_item_by_sku_or_id(sku)
            if not item:
                return
            
            if not messagebox.askyesno("Confirm Delete", 
                f"Are you sure you want to delete:\n\n{item['sku']} - {item['name']}\n\nThis action cannot be undone!"):
                return
            
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("DELETE FROM items WHERE id=?", (item['id'],))
                cur.execute("DELETE FROM transactions WHERE item_id=?", (item['id'],))
                conn.commit()
                conn.close()
                messagebox.showinfo("Deleted", "Item deleted successfully")
                refresh_list()
                details.delete("1.0", tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete item: {str(e)}")

        def export_inventory():
            try:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    title="Export Inventory"
                )
                if not file_path:
                    return
                
                items = list_items()
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['SKU', 'Name', 'Category', 'Supplier', 'Unit Price', 'Quantity', 'Min Quantity', 'Total Value', 'Notes'])
                    for item in items:
                        writer.writerow([
                            item['sku'], item['name'], item.get('category', ''), item.get('supplier', ''),
                            item['unit_price'], item['quantity'], item['min_quantity'],
                            item['unit_price'] * item['quantity'], item['notes'] or ''
                        ])
                messagebox.showinfo("Success", f"Inventory exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def create_order_window(self):
        win = tk.Toplevel(self)
        win.title("Create New Order")
        win.geometry("950x750")
        
        # Customer section
        customer_frame = ttk.LabelFrame(win, text="Customer Information", padding=10)
        customer_frame.pack(fill="x", padx=10, pady=10)
        
        search_frame = ttk.Frame(customer_frame)
        search_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=5)
        
        ttk.Label(search_frame, text="Search Customer:").pack(side="left", padx=5)
        customer_search_var = tk.StringVar()
        customer_search = ttk.Entry(search_frame, textvariable=customer_search_var, width=30)
        customer_search.pack(side="left", padx=5)
        
        customer_list = tk.Listbox(customer_frame, height=3, width=60, font=("Arial", 9))
        customer_list.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        
        selected_customer = {"id": None}
        
        def search_customers(event=None):
            query = customer_search_var.get()
            if len(query) < 2:
                return
            customers = search_customer(query)
            customer_list.delete(0, tk.END)
            for c in customers:
                customer_list.insert(tk.END, f"{c['id']} | {c['name']} | {c['phone'] or 'N/A'} | {c['email'] or 'N/A'}")
        
        def select_customer(event=None):
            sel = customer_list.curselection()
            if not sel:
                return
            text = customer_list.get(sel[0])
            cid = int(text.split("|")[0].strip())
            customer = get_customer(cid)
            if customer:
                selected_customer["id"] = customer["id"]
                name_var.set(customer["name"])
                phone_var.set(customer["phone"] or "")
                email_var.set(customer["email"] or "")
                address_var.set(customer["address"] or "")
        
        customer_search.bind("<KeyRelease>", search_customers)
        customer_list.bind("<<ListboxSelect>>", select_customer)
        
        ttk.Button(search_frame, text="➕ New Customer", 
                  command=lambda: self.create_new_customer_inline(selected_customer, name_var, phone_var, email_var, address_var)).pack(side="left", padx=5)
        
        # Customer details
        details_frame = ttk.Frame(customer_frame)
        details_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Label(details_frame, text="Name:*").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=name_var, width=35).grid(row=0, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Phone:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        phone_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=phone_var, width=35).grid(row=1, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Email:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        email_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=email_var, width=35).grid(row=2, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Address:").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        address_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=address_var, width=50).grid(row=3, column=1, columnspan=2, sticky="ew", pady=3)
        
        # Items section
        items_frame = ttk.LabelFrame(win, text="Order Items", padding=10)
        items_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Item search
        search_frame = ttk.Frame(items_frame)
        search_frame.pack(fill="x", pady=5)
        
        ttk.Label(search_frame, text="Item ID/SKU:").pack(side="left", padx=5)
        item_search_var = tk.StringVar()
        item_search = ttk.Entry(search_frame, textvariable=item_search_var, width=20)
        item_search.pack(side="left", padx=5)
        
        ttk.Label(search_frame, text="Quantity:").pack(side="left", padx=5)
        quantity_var = tk.StringVar(value="1")
        quantity_entry = ttk.Entry(search_frame, textvariable=quantity_var, width=10)
        quantity_entry.pack(side="left", padx=5)
        
        order_items = []
        
        def add_item_to_order():
            item_key = item_search_var.get().strip()
            if not item_key:
                messagebox.showwarning("Warning", "Enter item ID or SKU")
                return
            
            item = get_item_by_sku_or_id(item_key)
            if not item:
                messagebox.showerror("Error", "Item not found")
                return
            
            try:
                qty = int(quantity_var.get())
                if qty <= 0:
                    raise ValueError()
            except:
                messagebox.showerror("Error", "Invalid quantity")
                return
            
            if item['quantity'] < qty:
                if not messagebox.askyesno("Warning", f"Only {item['quantity']} units available. Continue anyway?"):
                    return
            
            subtotal = item['unit_price'] * qty
            order_items.append({
                'item_id': item['id'],
                'sku': item['sku'],
                'name': item['name'],
                'quantity': qty,
                'unit_price': item['unit_price'],
                'subtotal': subtotal
            })
            
            refresh_order_items()
            item_search_var.set("")
            quantity_var.set("1")
        
        ttk.Button(search_frame, text="➕ Add Item", command=add_item_to_order, 
                  style="Success.TButton").pack(side="left", padx=5)
        
        # Order items tree
        columns = ('SKU', 'Name', 'Qty', 'Unit Price', 'Subtotal')
        tree_frame = ttk.Frame(items_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)
        
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")
        
        items_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=items_tree.yview)
        
        for col in columns:
            items_tree.heading(col, text=col)
            items_tree.column(col, width=100)
        items_tree.pack(fill="both", expand=True)
        
        total_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(items_frame, textvariable=total_var, font=("Arial", 14, "bold"), foreground="#0078D7").pack(pady=5)
        
        def refresh_order_items():
            for item in items_tree.get_children():
                items_tree.delete(item)
            
            total = 0
            for item in order_items:
                items_tree.insert('', 'end', values=(
                    item['sku'], item['name'], item['quantity'], 
                    f"${item['unit_price']:.2f}", f"${item['subtotal']:.2f}"
                ))
                total += item['subtotal']
            total_var.set(f"Total: ${total:.2f}")
        
        def remove_selected_item():
            selected = items_tree.selection()
            if not selected:
                return
            index = items_tree.index(selected[0])
            order_items.pop(index)
            refresh_order_items()
        
        ttk.Button(items_frame, text="🗑️ Remove Selected", command=remove_selected_item, 
                  style="Danger.TButton").pack(pady=5)
        
        # Notes
        notes_frame = ttk.Frame(win, padding=10)
        notes_frame.pack(fill="x")
        ttk.Label(notes_frame, text="Order Notes:").pack(anchor="w")
        notes_text = tk.Text(notes_frame, height=3)
        notes_text.pack(fill="x")
        
        # Submit button
        def submit_order():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Customer name is required")
                return
            
            if not order_items:
                messagebox.showerror("Error", "Add at least one item")
                return
            
            # Validate email if provided
            if email_var.get() and not validate_email(email_var.get()):
                messagebox.showerror("Error", "Invalid email format")
                return
            
            conn = get_conn()
            cur = conn.cursor()
            
            try:
                # Create or update customer
                if selected_customer["id"]:
                    cur.execute("""UPDATE customers SET name=?, phone=?, email=?, address=? WHERE id=?""",
                               (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), selected_customer["id"]))
                    customer_id = selected_customer["id"]
                else:
                    cur.execute("""INSERT INTO customers (name, phone, email, address, created_at, total_orders, total_spent) 
                                  VALUES (?, ?, ?, ?, ?, 0, 0)""",
                               (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), now_str()))
                    customer_id = cur.lastrowid
                
                # Calculate total
                total = sum(item['subtotal'] for item in order_items)
                
                # Create order
                order_number = generate_order_number()
                cur.execute("""INSERT INTO orders (order_number, customer_id, total_amount, status, created_at, user_id, notes)
                              VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (order_number, customer_id, total, 'Pending', now_str(), self.current_user['id'], 
                            notes_text.get("1.0", tk.END).strip()))
                order_id = cur.lastrowid
                
                # Add order items and update inventory
                for item in order_items:
                    cur.execute("""INSERT INTO order_items (order_id, item_id, quantity, unit_price, subtotal)
                                  VALUES (?, ?, ?, ?, ?)""",
                               (order_id, item['item_id'], item['quantity'], item['unit_price'], item['subtotal']))
                    
                    # Update inventory
                    cur.execute("UPDATE items SET quantity = quantity - ?, last_updated=? WHERE id = ?",
                               (item['quantity'], now_str(), item['item_id']))
                    
                    # Record transaction
                    cur.execute("""INSERT INTO transactions (item_id, change, type, note, timestamp, user_id)
                                  VALUES (?, ?, ?, ?, ?, ?)""",
                               (item['item_id'], -item['quantity'], 'order', f'Order {order_number}', now_str(), self.current_user['id']))
                
                # Update customer stats
                cur.execute("""UPDATE customers SET total_orders = total_orders + 1, total_spent = total_spent + ? 
                              WHERE id = ?""", (total, customer_id))
                
                conn.commit()
                messagebox.showinfo("Success", f"Order {order_number} created successfully!\nTotal: ${total:.2f}")
                win.destroy()
                self.refresh_orders_list()
                
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error", f"Failed to create order: {str(e)}")
            finally:
                conn.close()
        
        btn_frame = ttk.Frame(win, padding=10)
        btn_frame.pack()
        ttk.Button(btn_frame, text="✅ Create Order", command=submit_order, 
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)

        role = self.current_user['role']
        if role == "admin":
            ttk.Button(action_frame, text="➕ Add Item", command=add_item, 
                      style="Success.TButton").pack(side="left", padx=4)
            ttk.Button(action_frame, text="🗑️ Delete Item", command=delete_item, 
                      style="Danger.TButton").pack(side="left", padx=4)
        
        ttk.Button(action_frame, text="📊 Adjust Stock", command=adjust_stock).pack(side="left", padx=4)
        ttk.Button(action_frame, text="⚠️ Low Stock", command=self.show_low_stock_detailed).pack(side="left", padx=4)
        ttk.Button(action_frame, text="📥 Export CSV", command=export_inventory).pack(side="left", padx=4)
        ttk.Button(action_frame, text="🔄 Refresh", command=refresh_list).pack(side="left", padx=4)

    def create_orders_tab(self, parent):
        # Top buttons
        btn_frame = ttk.Frame(parent, padding=8)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="➕ Create New Order", command=self.create_order_window,
                  style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Refresh", command=lambda: self.refresh_orders_list()).pack(side="left", padx=5)
        
        # Filter frame
        filter_frame = ttk.Frame(parent, padding=8)
        filter_frame.pack(fill="x")
        ttk.Label(filter_frame, text="Filter by Status:").pack(side="left", padx=5)
        
        self.order_status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.order_status_var, 
                                    values=["All", "Pending", "Processing", "Completed", "Cancelled"],
                                    state="readonly", width=15)
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_orders_list())
        
        # Orders listbox
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.orders_listbox = tk.Listbox(list_frame, bg="white", fg="black", 
                                         selectbackground="#0078D7", selectforeground="white",
                                         font=("Arial", 9), yscrollcommand=scrollbar.set)
        self.orders_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.orders_listbox.yview)
        
        self.orders_listbox.bind("<Double-Button-1>", lambda e: self.view_order_details())
        
        # Action buttons
        action_frame = ttk.Frame(parent, padding=8)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="👁️ View Details", command=self.view_order_details).pack(side="left", padx=5)
        ttk.Button(action_frame, text="✏️ Update Status", command=self.update_order_status).pack(side="left", padx=5)
        ttk.Button(action_frame, text="📥 Export Orders", command=self.export_orders).pack(side="left", padx=5)
        
        self.refresh_orders_list()

    def refresh_orders_list(self):
        status = self.order_status_var.get()
        status_filter = None if status == "All" else status
        orders = list_orders(status_filter)
        
        self.orders_listbox.delete(0, tk.END)
        for order in orders:
            status_emoji = {"Pending": "⏳", "Processing": "🔄", "Completed": "✅", "Cancelled": "❌"}.get(order['status'], "")
            self.orders_listbox.insert(tk.END, 
                f"{status_emoji} {order['order_number']} | {order['customer_name']} | ${order['total_amount']:.2f} | {order['status']} | {order['created_at']}")

    def export_orders(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export Orders"
            )
            if not file_path:
                return
            
            status = self.order_status_var.get()
            status_filter = None if status == "All" else status
            orders = list_orders(status_filter, limit=10000)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Order Number', 'Customer', 'Phone', 'Total', 'Status', 'Created', 'User'])
                for order in orders:
                    writer.writerow([
                        order['order_number'], order['customer_name'], order.get('customer_phone', ''),
                        order['total_amount'], order['status'], order['created_at'], order.get('username', '')
                    ])
            messagebox.showinfo("Success", f"Orders exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")