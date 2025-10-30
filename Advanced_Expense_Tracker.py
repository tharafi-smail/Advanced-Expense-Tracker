import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import csv
import matplotlib.pyplot as plt
from pymongo import MongoClient
from bson.objectid import ObjectId

CATEGORIES = [
    "Food", "Transport", "Housing", "Bills", "Clothing",
    "Health", "Education", "Entertainment", "Travel", "Other"
]

class ExpenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Personal Expense Manager")
        self.client = MongoClient("mongodb://localhost:27017")
        self.db = self.client["expense_manager"]
        self.col = self.db["expenses"]

        self.current_records = []  # cache of currently shown records (dicts)

        self.build_ui()
        self.load_records()

    def build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")

        # add farme
        add_frame = ttk.LabelFrame(frm, text="Add Expense", padding=8)
        add_frame.grid(row=0, column=0, sticky="ew")

        ttk.Label(add_frame, text="Description:").grid(row=0, column=0, sticky="w")
        self.desc_entry = ttk.Entry(add_frame)
        self.desc_entry.grid(row=0, column=1, columnspan=3, sticky="w", pady=2)

        ttk.Label(add_frame, text="Amount:").grid(row=0, column=2, sticky="w", padx=10)
        self.amount_entry = ttk.Entry(add_frame)
        self.amount_entry.grid(row=0, column=3, sticky="w", pady=10)

        ttk.Label(add_frame, text="Category:").grid(row=1, column=0, sticky="w")
        self.category_cb = ttk.Combobox(add_frame, width=17, values=CATEGORIES, state="readonly")
        self.category_cb.set(CATEGORIES[0])
        self.category_cb.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(add_frame, text="Date:").grid(row=1, column=2, sticky="w", padx=10)
        self.date_entry = ttk.Entry(add_frame, width=20)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=1, column=3, sticky="w", pady=2)

        add_btn = ttk.Button(add_frame, text="Add Expense", command=self.add_expense)
        add_btn.grid(row=1, column=4, sticky="e", padx=10)

        # search frame
        search_frame = ttk.Frame(frm, padding=(0,8))
        search_frame.grid(row=1, column=0, sticky="ew")

        ttk.Label(search_frame, text="From Date:").grid(row=0, column=0, sticky="w", padx=10)
        self.from_date_entry = ttk.Entry(search_frame)
        self.from_date_entry.grid(row=0, column=1, sticky="w")

        ttk.Label(search_frame, text="To Date:").grid(row=0, column=2, sticky="w", padx=10)
        self.to_date_entry = ttk.Entry(search_frame)
        self.to_date_entry.grid(row=0, column=3, sticky="w")

        search_btn = ttk.Button(search_frame, text="Search by date", command=self.search_by_date_range)
        search_btn.grid(row=0, column=4, padx=10)

        view_all_btn = ttk.Button(search_frame, text="View All", command=lambda: self.load_records())
        view_all_btn.grid(row=0, column=5, padx=10)

        delete_btn = ttk.Button(search_frame, text="Delete Selected", command=self.delete_selected)
        delete_btn.grid(row=0, column=6, padx=10)

        # view frame
        view_frame = ttk.Frame(frm)
        view_frame.grid(row=2, column=0, sticky="nsew")
        self.root.rowconfigure(2, weight=1)
        frm.rowconfigure(2, weight=1)

        cols = ("_id", "description", "amount", "category", "date")
        self.tree = ttk.Treeview(view_frame, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("description", text="Description")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("category", text="Category")
        self.tree.heading("date", text="Date")
        self.tree.column("_id", width=0, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bottom frame (export, graph, total)
        bottom_frame = ttk.Frame(frm, padding=(0,6))
        bottom_frame.grid(row=3, column=0, sticky="ew")

        export_btn = ttk.Button(bottom_frame, text="Export data", command=self.export_data)
        export_btn.pack(side="left", padx=5)

        graph_date_btn = ttk.Button(bottom_frame, text="Graph by Date", command=self.graph_by_date)
        graph_date_btn.pack(side="left", padx=5)

        graph_cat_btn = ttk.Button(bottom_frame, text="Graph by Category", command=self.graph_by_category)
        graph_cat_btn.pack(side="left", padx=5)

        self.total_var = tk.StringVar(value="Total: 0.00")
        ttk.Label(bottom_frame, textvariable=self.total_var, font=(None, 12, 'bold')).pack(side="right", padx=10)

    def add_expense(self):
        desc = self.desc_entry.get().strip()
        amount_s = self.amount_entry.get().strip()
        category = self.category_cb.get().strip()
        date_s = self.date_entry.get().strip()

        if not desc:
            messagebox.showwarning("Validation", "Description is required")
            return
        try:
            amount = float(amount_s)
        except Exception:
            messagebox.showwarning("Validation", "Amount must be a number")
            return
        try:
            d = datetime.strptime(date_s, "%Y-%m-%d")
            date_iso = d.strftime("%Y-%m-%d")
        except Exception:
            messagebox.showwarning("Validation", "Date must be in YYYY-MM-DD format")
            return

        doc = {
            "description": desc,
            "amount": amount,
            "category": category,
            "date": date_iso
        }
        res = self.col.insert_one(doc)

        self.desc_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.category_cb.set(CATEGORIES[0])

        messagebox.showinfo("Saved", f"Expense added")
        self.load_records()

    def load_records(self, query=None):
        if query is None:
            cursor = self.col.find().sort("date", 1)
        else:
            cursor = self.col.find(query).sort("date", 1)

        self.current_records = list(cursor)
        for i in self.tree.get_children():
            self.tree.delete(i)
        for rec in self.current_records:
            rid = str(rec.get("_id"))
            self.tree.insert("", tk.END, values=(rid, rec.get("description"), f"{rec.get('amount'):.2f}", rec.get("category"), rec.get("date")))
        self.update_total()

    def search_by_date_range(self):
        from_s = self.from_date_entry.get().strip()
        to_s = self.to_date_entry.get().strip()

        if not from_s or not to_s:
            messagebox.showinfo("Search", "Please enter both From and To dates (YYYY-MM-DD)")
            return

        try:
            from_d = datetime.strptime(from_s, "%Y-%m-%d")
            to_d = datetime.strptime(to_s, "%Y-%m-%d")
        except Exception:
            messagebox.showwarning("Validation", "Dates must be in YYYY-MM-DD format")
            return

        if from_d > to_d:
            messagebox.showwarning("Validation", "From date cannot be after To date")
            return

        query = {"date": {"$gte": from_d.strftime("%Y-%m-%d"), "$lte": to_d.strftime("%Y-%m-%d")}}
        self.load_records(query=query)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "No items selected")
            return
        confirm = messagebox.askyesno("Confirm", f"Delete {len(sel)} selected record(s)?")
        if not confirm:
            return
        for iid in sel:
            vals = self.tree.item(iid, "values")
            rid = vals[0]
            try:
                self.col.delete_one({"_id": ObjectId(rid)})
            except Exception as e:
                print("Failed delete", e)
        self.load_records()

    def export_data(self):
        if not self.current_records:
            messagebox.showinfo("Export", "No records to export")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")])
        if not fpath:
            return
        try:
            with open(fpath, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Description", "Amount", "Category", "Date"])
                for r in self.current_records:
                    writer.writerow([r.get("description"), f"{r.get('amount'):.2f}", r.get("category"), r.get("date")])
            messagebox.showinfo("Export", f"Exported {len(self.current_records)} rows to {fpath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def graph_by_date(self):
        if not self.current_records:
            messagebox.showinfo("Graph", "No records to graph")
            return
        agg = {}
        for r in self.current_records:
            d = r.get("date")
            agg[d] = agg.get(d, 0.0) + float(r.get("amount", 0))
        dates = sorted(agg.keys())
        amounts = [agg[d] for d in dates]

        plt.figure(figsize=(8,4))
        plt.plot(dates, amounts)
        plt.xlabel('Date')
        plt.ylabel('Total Amount')
        plt.title('Expenses by Date')
        plt.tight_layout()
        plt.show()

    def graph_by_category(self):
        if not self.current_records:
            messagebox.showinfo("Graph", "No records to graph")
            return
        agg = {}
        for r in self.current_records:
            c = r.get("category") or "Other"
            agg[c] = agg.get(c, 0.0) + float(r.get("amount", 0))
        cats = list(agg.keys())
        amounts = [agg[c] for c in cats]

        plt.figure(figsize=(8,4))
        plt.bar(cats, amounts)
        plt.xlabel('Category')
        plt.ylabel('Total Amount')
        plt.title('Expenses by Category')
        plt.tight_layout()
        plt.show()

    def update_total(self):
        total = 0.0
        for r in self.current_records:
            try:
                total += float(r.get('amount', 0))
            except Exception:
                pass
        self.total_var.set(f"Total: {total:.2f}")

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('840x460')
    app = ExpenseApp(root)
    root.mainloop()
