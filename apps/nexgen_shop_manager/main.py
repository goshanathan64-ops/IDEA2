import os, sqlite3
from datetime import datetime, date
from kivy.app import App
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

def db_path():
    if platform == "android":
        return os.path.join(App.get_running_app().user_data_dir, "shop_manager.sqlite3")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop_manager.sqlite3")

class DB:
    def __init__(self):
        self.conn=sqlite3.connect(db_path())
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,cost REAL NOT NULL CHECK(cost>=0),price REAL NOT NULL CHECK(price>=0),quantity INTEGER NOT NULL CHECK(quantity>=0),low_stock INTEGER NOT NULL DEFAULT 5);
        CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY,name TEXT NOT NULL,phone TEXT DEFAULT '',notes TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY,description TEXT NOT NULL,amount REAL NOT NULL CHECK(amount>0),created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL,product_name TEXT NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>0),unit_price REAL NOT NULL,unit_cost REAL NOT NULL,total REAL NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(product_id) REFERENCES products(id));
        """)
        self.conn.commit()
    def rows(self,q,a=()): return self.conn.execute(q,a).fetchall()
    def close(self): self.conn.close()

class ShopScreen(Screen):
    def __init__(self,app,**kw):
        super().__init__(**kw); self.app_ref=app
        self.box=BoxLayout(orientation="vertical",padding=dp(12),spacing=dp(8)); self.add_widget(self.box)
    def reset(self,title,subtitle=""):
        self.box.clear_widgets()
        self.box.add_widget(Label(text=title,bold=True,font_size="22sp",size_hint_y=None,height=dp(42)))
        if subtitle: self.box.add_widget(Label(text=subtitle,size_hint_y=None,height=dp(42)))
        self.form=BoxLayout(orientation="vertical",spacing=dp(7),size_hint_y=None)
        self.form.bind(minimum_height=self.form.setter("height"))
        scroll=ScrollView(); scroll.add_widget(self.form); self.box.add_widget(scroll); self.fields={}
    def field(self,key,hint,filt=None):
        w=TextInput(hint_text=hint,multiline=False,size_hint_y=None,height=dp(48),input_filter=filt)
        self.fields[key]=w; self.form.add_widget(w)
    def pick(self,key,hint,values):
        w=Spinner(text=hint,values=values,size_hint_y=None,height=dp(48))
        self.fields[key]=w; self.form.add_widget(w)
    def action(self,label,fn):
        self.form.add_widget(Button(text=label,size_hint_y=None,height=dp(48),on_release=lambda *_:fn()))
    def listing(self,text):
        self.form.add_widget(Label(text=text,size_hint_y=None,height=max(dp(150),dp(23)*(text.count("\n")+2)),halign="left",valign="top"))

class NexGenShopManager(App):
    title="NexGen Shop Manager"
    def build(self):
        self.db=DB(); self.sm=ScreenManager()
        for n in ("dashboard","products","sales","customers","expenses","reports"): self.sm.add_widget(ShopScreen(self,name=n))
        self.show("dashboard"); return self.sm
    def alert(self,title,msg):
        b=BoxLayout(orientation="vertical",padding=dp(12)); b.add_widget(Label(text=str(msg)))
        x=Button(text="OK",size_hint_y=None,height=dp(44)); b.add_widget(x)
        p=Popup(title=title,content=b,size_hint=(.88,.4)); x.bind(on_release=p.dismiss); p.open()
    def nav(self,s):
        for label,target in [("Dashboard","dashboard"),("Products / Stock","products"),("Record Sale","sales"),("Customers","customers"),("Expenses","expenses"),("Reports","reports")]:
            s.action(label,lambda t=target:self.show(t))
    def show(self,n):
        self.sm.current=n; s=self.sm.get_screen(n)
        getattr(self,n)(s)
    def dashboard(self,s):
        today=date.today().isoformat()
        rev,gross=self.db.rows("SELECT COALESCE(SUM(total),0),COALESCE(SUM((unit_price-unit_cost)*quantity),0) FROM sales WHERE substr(created_at,1,10)=?",(today,))[0]
        exp=self.db.rows("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE substr(created_at,1,10)=?",(today,))[0][0]
        units,value=self.db.rows("SELECT COALESCE(SUM(quantity),0),COALESCE(SUM(quantity*cost),0) FROM products")[0]
        low=self.db.rows("SELECT name,quantity,low_stock FROM products WHERE quantity<=low_stock ORDER BY quantity")
        cash=lambda x:"USD "+format(x,".2f")
        s.reset("NexGen Shop Manager","Offline-first shop records")
        s.listing("TODAY "+today+"\nSales: "+cash(rev)+"\nGross profit: "+cash(gross)+"\nExpenses: "+cash(exp)+"\nEstimated net: "+cash(gross-exp)+"\nStock units: "+str(units)+"\nStock cost value: "+cash(value)+"\n\nLOW STOCK\n"+("\n".join("{} — {} left (alert {})".format(*r) for r in low) if low else "No low-stock products."))
        self.nav(s)
    def products(self,s):
        s.reset("Products & Stock","Add a product or update an existing product by name.")
        for k,h,f in [("name","Product name",None),("cost","Unit cost (USD)","float"),("price","Selling price (USD)","float"),("qty","Quantity in stock","int"),("low","Low-stock alert (default 5)","int")]: s.field(k,h,f)
        def save():
            try:
                n=s.fields["name"].text.strip(); c=float(s.fields["cost"].text or 0); p=float(s.fields["price"].text or 0); q=int(s.fields["qty"].text or 0); l=int(s.fields["low"].text or 5)
                if not n or min(c,p,q,l)<0: raise ValueError("Enter a name and non-negative values.")
                with self.db.conn: self.db.conn.execute("INSERT INTO products(name,cost,price,quantity,low_stock) VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET cost=excluded.cost,price=excluded.price,quantity=excluded.quantity,low_stock=excluded.low_stock",(n,c,p,q,l))
                self.show("products"); self.alert("Saved",n+" saved.")
            except (ValueError,sqlite3.Error) as e: self.alert("Check product",e)
        s.action("Save Product",save)
        rows=self.db.rows("SELECT name,cost,price,quantity,low_stock FROM products ORDER BY name")
        s.listing("PRODUCTS\n"+("\n".join("{} | cost {:.2f} | price {:.2f} | qty {} | alert {}".format(*r) for r in rows) if rows else "No products yet."))
        self.nav(s)
    def sales(self,s):
        rows=self.db.rows("SELECT id,name,quantity FROM products ORDER BY name")
        s.reset("Record a Sale","Choose a product and quantity; stock is deducted after validation.")
        s.pick("product","Choose product",["{} — {} (stock {})".format(*r) for r in rows]); s.field("qty","Quantity sold","int")
        def save():
            try:
                choice=s.fields["product"].text; pid=int(choice.split(" — ",1)[0]) if " — " in choice else 0; qty=int(s.fields["qty"].text or 0)
                if qty<=0: raise ValueError("Quantity must be at least 1.")
                with self.db.conn:
                    row=self.db.conn.execute("SELECT name,price,cost,quantity FROM products WHERE id=?",(pid,)).fetchone()
                    if not row: raise ValueError("Choose a valid product.")
                    n,p,c,available=row
                    if qty>available: raise ValueError("Only {} units remain.".format(available))
                    self.db.conn.execute("INSERT INTO sales(product_id,product_name,quantity,unit_price,unit_cost,total,created_at) VALUES(?,?,?,?,?,?,?)",(pid,n,qty,p,c,p*qty,datetime.now().isoformat(timespec="seconds")))
                    self.db.conn.execute("UPDATE products SET quantity=quantity-? WHERE id=?",(qty,pid))
                self.show("sales"); self.alert("Sale recorded","{} x {} — USD {:.2f}".format(qty,n,qty*p))
            except (ValueError,sqlite3.Error) as e: self.alert("Sale not recorded",e)
        s.action("Record Sale",save)
        recent=self.db.rows("SELECT created_at,product_name,quantity,total FROM sales ORDER BY id DESC LIMIT 20")
        s.listing("RECENT SALES\n"+("\n".join("{} | {} x {} | {:.2f}".format(d[:16],n,q,t) for d,n,q,t in recent) if recent else "No sales recorded."))
        self.nav(s)
    def customers(self,s):
        s.reset("Customers","Save customer names and contact details.")
        s.field("name","Customer name"); s.field("phone","Phone number"); s.field("notes","Notes")
        def save():
            n=s.fields["name"].text.strip()
            if not n: self.alert("Missing name","Enter a customer name."); return
            with self.db.conn: self.db.conn.execute("INSERT INTO customers(name,phone,notes) VALUES(?,?,?)",(n,s.fields["phone"].text.strip(),s.fields["notes"].text.strip()))
            self.show("customers"); self.alert("Saved","Customer record saved.")
        s.action("Save Customer",save)
        rows=self.db.rows("SELECT name,phone,notes FROM customers ORDER BY id DESC LIMIT 50")
        s.listing("CUSTOMERS\n"+("\n".join("{} | {} | {}".format(*r) for r in rows) if rows else "No customers saved."))
        self.nav(s)
    def expenses(self,s):
        s.reset("Expenses","Record rent, transport, electricity and other shop costs.")
        s.field("desc","Expense description"); s.field("amount","Amount (USD)","float")
        def save():
            try:
                d=s.fields["desc"].text.strip(); a=float(s.fields["amount"].text or 0)
                if not d or a<=0: raise ValueError("Enter a description and amount above zero.")
                with self.db.conn: self.db.conn.execute("INSERT INTO expenses(description,amount,created_at) VALUES(?,?,?)",(d,a,datetime.now().isoformat(timespec="seconds")))
                self.show("expenses"); self.alert("Saved","Expense recorded.")
            except (ValueError,sqlite3.Error) as e: self.alert("Check expense",e)
        s.action("Save Expense",save)
        rows=self.db.rows("SELECT description,amount,created_at FROM expenses ORDER BY id DESC LIMIT 30")
        s.listing("RECENT EXPENSES\n"+("\n".join("{} | {:.2f} | {}".format(d,a,t[:16]) for d,a,t in rows) if rows else "No expenses recorded."))
        self.nav(s)
    def reports(self,s):
        rev,gross,count=self.db.rows("SELECT COALESCE(SUM(total),0),COALESCE(SUM((unit_price-unit_cost)*quantity),0),COUNT(*) FROM sales")[0]
        exp=self.db.rows("SELECT COALESCE(SUM(amount),0) FROM expenses")[0][0]
        value,units=self.db.rows("SELECT COALESCE(SUM(quantity*cost),0),COALESCE(SUM(quantity),0) FROM products")[0]
        cash=lambda x:"USD "+format(x,".2f")
        s.reset("Business Reports","All-time totals stored on this device.")
        s.listing("SALES REVENUE: "+cash(rev)+"\nGROSS PROFIT: "+cash(gross)+"\nEXPENSES: "+cash(exp)+"\nESTIMATED NET: "+cash(gross-exp)+"\nSTOCK COST VALUE: "+cash(value)+"\nSTOCK UNITS: "+str(units)+"\nTRANSACTIONS: "+str(count))
        self.nav(s)
    def on_stop(self):
        if hasattr(self,"db"): self.db.close()

if __name__=="__main__": NexGenShopManager().run()
