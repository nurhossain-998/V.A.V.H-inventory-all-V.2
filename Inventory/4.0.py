#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext

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
    
    # Existing tables
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, role TEXT,
        name TEXT, phone TEXT, email TEXT)''')
    
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
    
    # New tables for order management
    cur.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT,
        created_at TEXT, notes TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, order_number TEXT UNIQUE, customer_id INTEGER, 
        total_amount REAL, status TEXT, created_at TEXT, user_id INTEGER,
        notes TEXT, FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY, order_id INTEGER, item_id INTEGER, 
        quantity INTEGER, unit_price REAL, subtotal REAL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(item_id) REFERENCES items(id))''')
    
    conn.commit()
    
    # Create default users if none exist
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("admin", hash_password("admin"), "admin"))
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                    ("clerk", hash_password("clerk"), "clerk"))
        conn.commit()
    
    conn.close()

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

def list_orders(status_filter=None):
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
                       ORDER BY o.created_at DESC LIMIT 100""")
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


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V.A.V.H Studio - Inventory & Order Management")
        self.geometry("1100x650")
        self.resizable(True, True)
        self.configure(bg="white")
        
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="white")
        self.style.configure("TLabel", background="white", foreground="black")
        self.style.configure("TButton", background="#0078D7", foreground="white", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#3399FF")])
        
        self.current_user = None
        self.create_login_screen()

    def create_login_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="V.A.V.H Studio", font=("Arial", 22, "bold"), 
                 foreground="#0078D7").grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        ttk.Label(frame, text="Username:").grid(row=1, column=0, sticky="e", pady=5)
        user_entry = ttk.Entry(frame, width=25)
        user_entry.grid(row=1, column=1, sticky="w", pady=5)
        
        ttk.Label(frame, text="Password:").grid(row=2, column=0, sticky="e", pady=5)
        pass_entry = ttk.Entry(frame, show="*", width=25)
        pass_entry.grid(row=2, column=1, sticky="w", pady=5)

        def do_login(event=None):
            username = user_entry.get().strip()
            password = pass_entry.get().strip()
            user = get_user(username)
            if not user or hash_password(password) != user["password_hash"]:
                messagebox.showerror("Login failed", "Incorrect username or password")
                return
            self.current_user = dict(user)
            self.create_main_ui()

        ttk.Button(frame, text="Login", command=do_login).grid(row=3, column=0, columnspan=2, pady=10)
        self.bind("<Return>", do_login)

    def create_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        
        # Top bar
        top = ttk.Frame(self)
        top.pack(fill="x", padx=5, pady=5)
        ttk.Label(top, text=f"Logged in: {self.current_user['username']} ({self.current_user['role']})", 
                 foreground="#0078D7").pack(side="left")

        ttk.Button(top, text="Profile", command=self.show_profile).pack(side="right", padx=5)
        ttk.Button(top, text="Logout", command=self.logout).pack(side="right", padx=5)
        if self.current_user["role"] == "admin":
            ttk.Button(top, text="Create User", command=self.create_user).pack(side="right", padx=5)

        # Notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Inventory tab
        inventory_frame = ttk.Frame(notebook)
        notebook.add(inventory_frame, text="Inventory")
        self.create_inventory_tab(inventory_frame)
        
        # Orders tab
        orders_frame = ttk.Frame(notebook)
        notebook.add(orders_frame, text="Orders")
        self.create_orders_tab(orders_frame)
        
        # Customers tab
        customers_frame = ttk.Frame(notebook)
        notebook.add(customers_frame, text="Customers")
        self.create_customers_tab(customers_frame)

    def create_inventory_tab(self, parent):
        pan = ttk.Panedwindow(parent, orient=tk.HORIZONTAL)
        pan.pack(fill="both", expand=True)
        
        left = ttk.Frame(pan, width=350)
        right = ttk.Frame(pan)
        pan.add(left, weight=1)
        pan.add(right, weight=3)

        search_frame = ttk.Frame(left, padding=8)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search SKU/Name:").pack(anchor="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(fill="x")
        
        listbox = tk.Listbox(left, bg="white", fg="black", selectbackground="#0078D7", selectforeground="white")
        listbox.pack(fill="both", expand=True, padx=8, pady=8)

        def refresh_list(event=None):
            q = search_var.get() or "%"
            items = list_items(q)
            listbox.delete(0, tk.END)
            for it in items:
                listbox.insert(tk.END, f"{it['id']} | {it['sku']} | {it['name']} | Qty: {it['quantity']}")

        search_entry.bind("<KeyRelease>", lambda e: refresh_list())
        refresh_list()

        details = tk.Text(right, height=15, bg="white", fg="black", insertbackground="black")
        details.pack(fill="x", padx=8, pady=8)

        action_frame = ttk.Frame(right)
        action_frame.pack(fill="x", padx=8, pady=8)

        def show_selected(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            text = listbox.get(sel[0])
            key = text.split("|")[0].strip()
            item = get_item_by_sku_or_id(key)
            if not item:
                details.delete("1.0", tk.END)
                details.insert(tk.END, "Item not found")
                return
            out = [
                f"ID: {item['id']}",
                f"SKU: {item['sku']}",
                f"Name: {item['name']}",
                f"Category ID: {item['category_id']}",
                f"Supplier ID: {item['supplier_id']}",
                f"Unit price: ${item['unit_price']:.2f}",
                f"Quantity: {item['quantity']}",
                f"Min quantity: {item['min_quantity']}",
                f"Notes: {item['notes']}"
            ]
            details.delete("1.0", tk.END)
            details.insert(tk.END, "\n".join(out))

        listbox.bind("<<ListboxSelect>>", show_selected)

        def adjust_stock():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select", "Select an item first")
                return
            text = listbox.get(sel[0])
            key = text.split("|")[0].strip()
            item = get_item_by_sku_or_id(key)
            if not item:
                return
            try:
                change = int(simpledialog.askstring("Change", "Quantity change (negative to decrease):", parent=self))
            except:
                messagebox.showerror("Invalid", "Invalid number")
                return
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            new_q = item['quantity'] + change
            if new_q < 0:
                messagebox.showerror("Error", "Resulting quantity would be negative")
                return
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("UPDATE items SET quantity=? WHERE id=?", (new_q, item['id']))
            cur.execute("INSERT INTO transactions (item_id,change,type,note,timestamp,user_id) VALUES (?,?,?,?,?,?)",
                        (item['id'], change, 'adjust', note, now_str(), self.current_user['id']))
            conn.commit()
            conn.close()
            messagebox.showinfo("Updated", f"New quantity: {new_q}")
            refresh_list()

        def add_item():
            sku = simpledialog.askstring("SKU", "SKU:", parent=self)
            if not sku:
                return
            name = simpledialog.askstring("Name", "Name:", parent=self)
            if not name:
                return
            try:
                unit_price = float(simpledialog.askstring("Unit price", "Unit price (0):", parent=self) or 0)
            except:
                unit_price = 0.0
            try:
                quantity = int(simpledialog.askstring("Quantity", "Initial quantity (0):", parent=self) or 0)
            except:
                quantity = 0
            min_q = int(simpledialog.askstring("Min quantity", "Min quantity (0):", parent=self) or 0)
            notes = simpledialog.askstring("Notes", "Notes (optional):", parent=self) or ""
            
            conn = get_conn()
            cur = conn.cursor()
            try:
                cur.execute("INSERT INTO items (sku,name,unit_price,quantity,min_quantity,notes) VALUES (?,?,?,?,?,?)",
                            (sku, name, unit_price, quantity, min_q, notes))
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

        def delete_item():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Select", "Select an item first")
                return
            text = listbox.get(sel[0])
            key = text.split("|")[0].strip()
            item = get_item_by_sku_or_id(key)
            if not item:
                return
            if messagebox.askyesno("Confirm", f"Delete {item['sku']} - {item['name']}?"):
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("DELETE FROM items WHERE id=?", (item['id'],))
                cur.execute("DELETE FROM transactions WHERE item_id=?", (item['id'],))
                conn.commit()
                conn.close()
                messagebox.showinfo("Deleted", "Item deleted.")
                refresh_list()

        def low_stock_report():
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT sku,name,quantity,min_quantity FROM items WHERE min_quantity>0 AND quantity<=min_quantity ORDER BY quantity ASC")
            rows = cur.fetchall()
            conn.close()
            if not rows:
                messagebox.showinfo("Low stock", "No low-stock items.")
                return
            out = "\n".join(f"{r['sku']} - {r['name']}: {r['quantity']} (min {r['min_quantity']})" for r in rows)
            messagebox.showinfo("Low stock", out)

        def view_history():
            conn = get_conn()
            cur = conn.cursor()
            cur.execute('''SELECT t.timestamp,u.username,i.sku,i.name,t.change,t.type,t.note 
                           FROM transactions t 
                           LEFT JOIN users u ON t.user_id=u.id 
                           LEFT JOIN items i ON t.item_id=i.id 
                           ORDER BY t.timestamp DESC LIMIT 200''')
            rows = cur.fetchall()
            conn.close()
            if not rows:
                messagebox.showinfo("History", "No transactions.")
                return
            out = "\n".join(f"[{r['timestamp']}] ({r['username']}) {r['sku']} {r['name']}: {r['change']} ({r['type']}) - {r['note']}" for r in rows)
            
            win = tk.Toplevel(self)
            win.title("Transaction History")
            win.geometry("800x500")
            text = scrolledtext.ScrolledText(win, wrap=tk.WORD)
            text.pack(fill="both", expand=True, padx=10, pady=10)
            text.insert("1.0", out)
            text.config(state="disabled")

        role = self.current_user['role']
        if role == "admin":
            ttk.Button(action_frame, text="Add Item", command=add_item).pack(side="left", padx=4)
            ttk.Button(action_frame, text="Delete Item", command=delete_item).pack(side="left", padx=4)
        
        ttk.Button(action_frame, text="Adjust Stock", command=adjust_stock).pack(side="left", padx=4)
        ttk.Button(action_frame, text="Low Stock Report", command=low_stock_report).pack(side="left", padx=4)
        ttk.Button(action_frame, text="View History", command=view_history).pack(side="left", padx=4)
        ttk.Button(right, text="Refresh List", command=refresh_list).pack(pady=4)

    def create_orders_tab(self, parent):
        # Top buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=8, pady=8)
        
        ttk.Button(btn_frame, text="Create New Order", command=self.create_order_window).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh Orders", command=lambda: self.refresh_orders_list()).pack(side="left", padx=5)
        
        # Filter frame
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill="x", padx=8, pady=5)
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
                                         yscrollcommand=scrollbar.set)
        self.orders_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.orders_listbox.yview)
        
        self.orders_listbox.bind("<Double-Button-1>", lambda e: self.view_order_details())
        
        # Action buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill="x", padx=8, pady=8)
        
        ttk.Button(action_frame, text="View Details", command=self.view_order_details).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Update Status", command=self.update_order_status).pack(side="left", padx=5)
        
        self.refresh_orders_list()

    def refresh_orders_list(self):
        status = self.order_status_var.get()
        status_filter = None if status == "All" else status
        orders = list_orders(status_filter)
        
        self.orders_listbox.delete(0, tk.END)
        for order in orders:
            self.orders_listbox.insert(tk.END, 
                f"{order['order_number']} | {order['customer_name']} | ${order['total_amount']:.2f} | {order['status']} | {order['created_at']}")

    def create_order_window(self):
        win = tk.Toplevel(self)
        win.title("Create New Order")
        win.geometry("900x700")
        
        # Customer section
        customer_frame = ttk.LabelFrame(win, text="Customer Information", padding=10)
        customer_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(customer_frame, text="Search Customer:").grid(row=0, column=0, sticky="w", pady=5)
        customer_search_var = tk.StringVar()
        customer_search = ttk.Entry(customer_frame, textvariable=customer_search_var, width=30)
        customer_search.grid(row=0, column=1, sticky="w", pady=5)
        
        customer_list = tk.Listbox(customer_frame, height=3, width=50)
        customer_list.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        
        selected_customer = {"id": None}
        
        def search_customers(event=None):
            query = customer_search_var.get()
            if len(query) < 2:
                return
            customers = search_customer(query)
            customer_list.delete(0, tk.END)
            for c in customers:
                customer_list.insert(tk.END, f"{c['id']} | {c['name']} | {c['phone']} | {c['email']}")
        
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
        
        ttk.Button(customer_frame, text="New Customer", 
                  command=lambda: self.create_new_customer_inline(selected_customer, name_var, phone_var, email_var, address_var)).grid(row=0, column=2, padx=5)
        
        # Customer details
        details_frame = ttk.Frame(customer_frame)
        details_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Label(details_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=name_var, width=30).grid(row=0, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Phone:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        phone_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=phone_var, width=30).grid(row=1, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Email:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        email_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=email_var, width=30).grid(row=2, column=1, sticky="w", pady=3)
        
        ttk.Label(details_frame, text="Address:").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        address_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=address_var, width=50).grid(row=3, column=1, columnspan=2, sticky="ew", pady=3)
        
        # Items section
        items_frame = ttk.LabelFrame(win, text="Order Items", padding=10)
        items_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Item search
        search_frame = ttk.Frame(items_frame)
        search_frame.pack(fill="x", pady=5)
        
        ttk.Label(search_frame, text="Search Item (ID/SKU):").pack(side="left", padx=5)
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
        
        ttk.Button(search_frame, text="Add Item", command=add_item_to_order).pack(side="left", padx=5)
        
        # Order items list
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
        ttk.Label(items_frame, textvariable=total_var, font=("Arial", 12, "bold"), foreground="#0078D7").pack(pady=5)
        
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
        
        ttk.Button(items_frame, text="Remove Selected", command=remove_selected_item).pack(pady=5)
        
        # Notes
        notes_frame = ttk.Frame(win)
        notes_frame.pack(fill="x", padx=10, pady=5)
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
            
            conn = get_conn()
            cur = conn.cursor()
            
            try:
                # Create or update customer
                if selected_customer["id"]:
                    cur.execute("""UPDATE customers SET name=?, phone=?, email=?, address=? WHERE id=?""",
                               (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), selected_customer["id"]))
                    customer_id = selected_customer["id"]
                else:
                    cur.execute("""INSERT INTO customers (name, phone, email, address, created_at) 
                                  VALUES (?, ?, ?, ?, ?)""",
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
                    cur.execute("UPDATE items SET quantity = quantity - ? WHERE id = ?",
                               (item['quantity'], item['item_id']))
                    
                    # Record transaction
                    cur.execute("""INSERT INTO transactions (item_id, change, type, note, timestamp, user_id)
                                  VALUES (?, ?, ?, ?, ?, ?)""",
                               (item['item_id'], -item['quantity'], 'order', f'Order {order_number}', now_str(), self.current_user['id']))
                
                conn.commit()
                messagebox.showinfo("Success", f"Order {order_number} created successfully!")
                win.destroy()
                self.refresh_orders_list()
                
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error", f"Failed to create order: {str(e)}")
            finally:
                conn.close()
        
        ttk.Button(win, text="Create Order", command=submit_order).pack(pady=10)

    def create_new_customer_inline(self, selected_customer, name_var, phone_var, email_var, address_var):
        name = simpledialog.askstring("New Customer", "Customer Name:", parent=self)
        if not name:
            return
        phone = simpledialog.askstring("New Customer", "Phone:", parent=self) or ""
        email = simpledialog.askstring("New Customer", "Email:", parent=self) or ""
        address = simpledialog.askstring("New Customer", "Address:", parent=self) or ""
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""INSERT INTO customers (name, phone, email, address, created_at) VALUES (?, ?, ?, ?, ?)""",
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

    def view_order_details(self):
        sel = self.orders_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select", "Select an order first")
            return
        
        text = self.orders_listbox.get(sel[0])
        order_number = text.split("|")[0].strip()
        
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
        win.geometry("700x600")
        
        # Order info
        info_frame = ttk.LabelFrame(win, text="Order Information", padding=10)
        info_frame.pack(fill="x", padx=10, pady=10)
        
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
        
        ttk.Label(info_frame, text=info_text, justify="left").pack(anchor="w")
        
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
            messagebox.showinfo("Select", "Select an order first")
            return
        
        text = self.orders_listbox.get(sel[0])
        order_number = text.split("|")[0].strip()
        
        new_status = simpledialog.askstring("Update Status", 
                                           "Enter new status (Pending/Processing/Completed/Cancelled):",
                                           parent=self)
        if not new_status or new_status not in ["Pending", "Processing", "Completed", "Cancelled"]:
            return
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status=? WHERE order_number=?", (new_status, order_number))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Success", "Order status updated")
        self.refresh_orders_list()

    def create_customers_tab(self, parent):
        # Top buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=8, pady=8)
        
        ttk.Button(btn_frame, text="Add New Customer", command=self.add_customer).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=lambda: self.refresh_customers_list()).pack(side="left", padx=5)
        
        # Search
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill="x", padx=8, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=5)
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
                                           yscrollcommand=scrollbar.set)
        self.customers_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.customers_listbox.yview)
        
        self.customers_listbox.bind("<Double-Button-1>", lambda e: self.edit_customer())
        
        # Action buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill="x", padx=8, pady=8)
        
        ttk.Button(action_frame, text="Edit Customer", command=self.edit_customer).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Delete Customer", command=self.delete_customer).pack(side="left", padx=5)
        
        self.refresh_customers_list()

    def refresh_customers_list(self):
        query = self.customer_search_var.get() if hasattr(self, 'customer_search_var') else ""
        customers = search_customer(query) if query else search_customer("%")
        
        self.customers_listbox.delete(0, tk.END)
        for c in customers:
            self.customers_listbox.insert(tk.END,
                f"{c['id']} | {c['name']} | {c['phone'] or 'N/A'} | {c['email'] or 'N/A'}")

    def add_customer(self):
        win = tk.Toplevel(self)
        win.title("Add Customer")
        win.geometry("400x300")
        
        ttk.Label(win, text="Name:").pack(pady=5)
        name_var = tk.StringVar()
        ttk.Entry(win, textvariable=name_var, width=40).pack(pady=5)
        
        ttk.Label(win, text="Phone:").pack(pady=5)
        phone_var = tk.StringVar()
        ttk.Entry(win, textvariable=phone_var, width=40).pack(pady=5)
        
        ttk.Label(win, text="Email:").pack(pady=5)
        email_var = tk.StringVar()
        ttk.Entry(win, textvariable=email_var, width=40).pack(pady=5)
        
        ttk.Label(win, text="Address:").pack(pady=5)
        address_var = tk.StringVar()
        ttk.Entry(win, textvariable=address_var, width=40).pack(pady=5)
        
        def save():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Name is required")
                return
            
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""INSERT INTO customers (name, phone, email, address, created_at)
                          VALUES (?, ?, ?, ?, ?)""",
                       (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), now_str()))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", "Customer added")
            win.destroy()
            self.refresh_customers_list()
        
        ttk.Button(win, text="Save", command=save).pack(pady=10)

    def edit_customer(self):
        sel = self.customers_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select", "Select a customer first")
            return
        
        text = self.customers_listbox.get(sel[0])
        cid = int(text.split("|")[0].strip())
        customer = get_customer(cid)
        
        if not customer:
            return
        
        win = tk.Toplevel(self)
        win.title("Edit Customer")
        win.geometry("400x300")
        
        ttk.Label(win, text="Name:").pack(pady=5)
        name_var = tk.StringVar(value=customer['name'])
        ttk.Entry(win, textvariable=name_var, width=40).pack(pady=5)
        
        ttk.Label(win, text="Phone:").pack(pady=5)
        phone_var = tk.StringVar(value=customer['phone'] or "")
        ttk.Entry(win, textvariable=phone_var, width=40).pack(pady=5)
        
        ttk.Label(win, text="Email:").pack(pady=5)
        email_var = tk.StringVar(value=customer['email'] or "")
        ttk.Entry(win, textvariable=email_var, width=40).pack(pady=5)
        
        ttk.Label(win, text="Address:").pack(pady=5)
        address_var = tk.StringVar(value=customer['address'] or "")
        ttk.Entry(win, textvariable=address_var, width=40).pack(pady=5)
        
        def save():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Name is required")
                return
            
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""UPDATE customers SET name=?, phone=?, email=?, address=? WHERE id=?""",
                       (name_var.get(), phone_var.get(), email_var.get(), address_var.get(), cid))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", "Customer updated")
            win.destroy()
            self.refresh_customers_list()
        
        ttk.Button(win, text="Save", command=save).pack(pady=10)

    def delete_customer(self):
        sel = self.customers_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select", "Select a customer first")
            return
        
        text = self.customers_listbox.get(sel[0])
        cid = int(text.split("|")[0].strip())
        
        if messagebox.askyesno("Confirm", "Delete this customer?"):
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM customers WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Deleted", "Customer deleted")
            self.refresh_customers_list()

    def create_user(self):
        uname = simpledialog.askstring("New User", "Enter username:", parent=self)
        if not uname:
            return
        pwd = simpledialog.askstring("New User", "Enter password:", parent=self, show="*")
        if not pwd:
            return
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                        (uname, hash_password(pwd), "user"))
            conn.commit()
            messagebox.showinfo("Success", f"User '{uname}' created.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists.")
        finally:
            conn.close()

    def show_profile(self):
        user = self.current_user
        win = tk.Toplevel(self)
        win.title("Profile")
        win.geometry("400x400")
        
        ttk.Label(win, text=f"Profile ({user['username']})", font=("Arial", 14, "bold")).pack(pady=10)
        
        name = tk.StringVar(value=user.get("name", ""))
        phone = tk.StringVar(value=user.get("phone", ""))
        email = tk.StringVar(value=user.get("email", ""))
        
        ttk.Label(win, text="Name:").pack()
        ttk.Entry(win, textvariable=name).pack()
        ttk.Label(win, text="Phone:").pack()
        ttk.Entry(win, textvariable=phone).pack()
        ttk.Label(win, text="Email:").pack()
        ttk.Entry(win, textvariable=email).pack()
        
        def save_profile():
            update_user_field(user["id"], "name", name.get())
            update_user_field(user["id"], "phone", phone.get())
            update_user_field(user["id"], "email", email.get())
            messagebox.showinfo("Saved", "Profile updated.")
        
        ttk.Button(win, text="Save Profile", command=save_profile).pack(pady=10)
        
        def change_password():
            new_pwd = simpledialog.askstring("Change Password", "Enter new password:", parent=win, show="*")
            if new_pwd:
                update_user_field(user["id"], "password_hash", hash_password(new_pwd))
                messagebox.showinfo("Password", "Password changed.")
        
        ttk.Button(win, text="Change Password", command=change_password).pack(pady=5)

        if user["role"] == "admin":
            ttk.Label(win, text="All Users", font=("Arial", 12, "bold")).pack(pady=5)
            users = list_users()
            box = tk.Listbox(win, height=8)
            for u in users:
                box.insert(tk.END, f"{u['id']} | {u['username']} | {u['role']} | {u.get('email','')}")
            box.pack(fill="both", expand=True)
            
            def change_role():
                sel = box.curselection()
                if not sel:
                    return
                line = box.get(sel[0])
                uid = int(line.split("|")[0].strip())
                new_role = simpledialog.askstring("Role", "Enter new role (admin/user/clerk):", parent=win)
                if new_role in ("admin", "user", "clerk"):
                    update_user_field(uid, "role", new_role)
                    messagebox.showinfo("Updated", "User role updated.")
                    win.destroy()
            
            ttk.Button(win, text="Change Access", command=change_role).pack(pady=5)

    def logout(self):
        self.current_user = None
        self.create_login_screen()


def main():
    init_db()
    app = InventoryApp()
    app.mainloop()


if __name__ == "__main__":
    main()