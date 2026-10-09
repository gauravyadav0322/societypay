import sqlite3
from pathlib import Path
from datetime import date, datetime
import random
import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "societypay.db"
DEMO_SOCIETY = "Greenview Residency"

st.set_page_config(page_title="SocietyPay | Maintenance Portal", page_icon="🏢", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1450px;}
[data-testid="stMetric"] {background:#ffffff; border:1px solid #e5e7eb; padding:16px 18px; border-radius:14px;}
[data-testid="stSidebar"] {background:#f7f9fc;}
.demo-banner {background:#fff4d6;border:1px solid #f2d58a;color:#704c00;padding:10px 14px;border-radius:10px;margin-bottom:14px;font-size:14px;}
.hero {padding:20px 24px;border-radius:18px;background:linear-gradient(120deg,#12233f,#1c4b67);color:white;margin-bottom:18px;}
.hero h1 {color:white;margin:0;font-size:30px;}
.hero p {color:#dce8f5;margin:6px 0 0 0;}
.small-muted {color:#6b7280;font-size:13px;}
</style>
<div class="demo-banner"><b>DEMO ENVIRONMENT — NO REAL MONEY</b> · All residents, invoices, transactions and payment outcomes are simulated.</div>
""", unsafe_allow_html=True)


def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def q(sql, params=(), read=True):
    with conn() as c:
        cur = c.execute(sql, params)
        if read:
            rows = cur.fetchall()
            return pd.DataFrame([dict(r) for r in rows])
        c.commit()
        return cur.lastrowid


def init_db():
    q("""CREATE TABLE IF NOT EXISTS residents(
        id INTEGER PRIMARY KEY AUTOINCREMENT, flat_no TEXT UNIQUE NOT NULL,
        building TEXT NOT NULL, resident_name TEXT NOT NULL, phone TEXT,
        email TEXT, monthly_fee REAL NOT NULL, active INTEGER NOT NULL DEFAULT 1)""", read=False)
    q("""CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT UNIQUE NOT NULL,
        resident_id INTEGER NOT NULL, billing_month TEXT NOT NULL, amount REAL NOT NULL,
        previous_dues REAL NOT NULL DEFAULT 0, due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL,
        FOREIGN KEY(resident_id) REFERENCES residents(id))""", read=False)
    q("""CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, txn_id TEXT UNIQUE NOT NULL,
        invoice_id INTEGER NOT NULL, amount REAL NOT NULL, method TEXT NOT NULL,
        status TEXT NOT NULL, paid_at TEXT NOT NULL, note TEXT,
        FOREIGN KEY(invoice_id) REFERENCES invoices(id))""", read=False)
    q("""CREATE TABLE IF NOT EXISTS bank_transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, reference TEXT UNIQUE NOT NULL,
        txn_date TEXT NOT NULL, payer TEXT NOT NULL, amount REAL NOT NULL,
        matched_invoice TEXT, status TEXT NOT NULL DEFAULT 'Unmatched')""", read=False)
    count = q("SELECT COUNT(*) n FROM residents").iloc[0]["n"]
    if count == 0:
        random.seed(42)
        names = ["Aarav Sharma","Ananya Patil","Vihaan Deshmukh","Isha Kulkarni","Arjun Mehta","Saanvi Joshi","Reyansh Shah","Aditi Nair","Advait Rao","Myra Kapoor","Kabir Singh","Sara Khan","Ishaan Gupta","Diya Iyer","Rohan Verma","Kiara Jain","Atharv Pawar","Meera Sethi","Vivaan Das","Tara Menon"]
        residents = []
        for i in range(1, 201):
            building = chr(65 + ((i - 1) // 50))
            floor_flat = ((i - 1) % 50) + 1
            flat_no = f"{building}-{100 + floor_flat}"
            residents.append((flat_no, building, names[(i-1) % len(names)], f"98{random.randint(10000000,99999999)}", f"resident{i}@example.com", 3000 if i % 5 else 3500, 1))
        with conn() as c:
            c.executemany("INSERT INTO residents(flat_no,building,resident_name,phone,email,monthly_fee,active) VALUES(?,?,?,?,?,?,?)", residents)
            c.commit()
    month = date.today().strftime("%Y-%m")
    invoices_count = q("SELECT COUNT(*) n FROM invoices WHERE billing_month=?", (month,)).iloc[0]["n"]
    if invoices_count == 0:
        res = q("SELECT * FROM residents WHERE active=1 ORDER BY id")
        with conn() as c:
            for _, r in res.iterrows():
                invoice_no = f"INV-{month.replace('-', '')}-{int(r['id']):04d}"
                due = date.today().replace(day=min(10, 28)).isoformat()
                cur = c.execute("INSERT INTO invoices(invoice_no,resident_id,billing_month,amount,previous_dues,due_date,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (invoice_no, int(r['id']), month, float(r['monthly_fee']), 0, due, "Pending", datetime.now().isoformat(timespec="seconds")))
                invoice_id = cur.lastrowid
                if int(r['id']) <= 170:
                    txn = f"TEST_TXN_{month.replace('-', '')}_{int(r['id']):04d}"
                    c.execute("INSERT INTO payments(txn_id,invoice_id,amount,method,status,paid_at,note) VALUES(?,?,?,?,?,?,?)",
                        (txn, invoice_id, float(r['monthly_fee']), "UPI (simulated)", "Success", datetime.now().isoformat(timespec="seconds"), "Seeded demo payment"))
                    c.execute("UPDATE invoices SET status='Paid' WHERE id=?", (invoice_id,))
            c.commit()
    bank_count = q("SELECT COUNT(*) n FROM bank_transactions").iloc[0]["n"]
    if bank_count == 0:
        with conn() as c:
            for i in range(1, 7):
                c.execute("INSERT OR IGNORE INTO bank_transactions(reference,txn_date,payer,amount,matched_invoice,status) VALUES(?,?,?,?,?,?)",
                    (f"BANK-DEMO-{i:04d}", date.today().isoformat(), ["UPI R SHARMA","NEFT UNKNOWN","UPI A PATIL","IMPS FLAT B-124","UPI NO NAME","NEFT RESIDENT"][i-1], [3000,3500,3000,3500,3000,3000][i-1], None, "Unmatched"))
            c.commit()

init_db()


def money(x):
    return f"₹{float(x or 0):,.0f}"


def get_current_month():
    return date.today().strftime("%Y-%m")


def current_data():
    month = get_current_month()
    inv = q("SELECT i.*, r.flat_no, r.resident_name, r.building FROM invoices i JOIN residents r ON i.resident_id=r.id WHERE i.billing_month=?", (month,))
    total = float(inv["amount"].sum()) if not inv.empty else 0
    paid = float(inv.loc[inv.status == "Paid", "amount"].sum()) if not inv.empty else 0
    return inv, total, paid

st.sidebar.markdown("# 🏢 SocietyPay")
st.sidebar.caption("Maintenance automation")
page = st.sidebar.radio("NAVIGATION", ["Overview", "Residents & Flats", "Invoices & Payments", "Payment Simulator", "Reconciliation", "Reports & Exports"], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.markdown(f"**{DEMO_SOCIETY}**")
st.sidebar.caption("200 flats · Demo account")
if st.sidebar.button("Reset demo data", use_container_width=True, help="Deletes demo database and recreates sample records"):
    if DB_PATH.exists(): DB_PATH.unlink()
    init_db()
    st.rerun()
st.sidebar.caption("v1.0 · Portfolio prototype")

if page == "Overview":
    st.markdown(f'<div class="hero"><h1>Good morning 👋</h1><p>{DEMO_SOCIETY} · Maintenance collection overview for {date.today().strftime("%B %Y")}</p></div>', unsafe_allow_html=True)
    inv, total, paid = current_data()
    pending = total - paid
    paid_count = int((inv.status == "Paid").sum()) if not inv.empty else 0
    pending_count = int((inv.status != "Paid").sum()) if not inv.empty else 0
    rate = paid / total * 100 if total else 0
    a,b,c,d = st.columns(4)
    a.metric("Total billed", money(total), f"{len(inv)} invoices")
    b.metric("Collected", money(paid), f"{paid_count} flats paid")
    c.metric("Outstanding", money(pending), f"{pending_count} invoices")
    d.metric("Collection rate", f"{rate:.1f}%", "For current billing month")
    st.write("")
    left,right = st.columns([1.25,1])
    with left:
        st.subheader("Collection status")
        chart = pd.DataFrame({"Status":["Paid","Pending"],"Amount":[paid,pending]})
        fig = px.pie(chart, names="Status", values="Amount", hole=.62, color="Status", color_discrete_map={"Paid":"#1c9a78","Pending":"#e9a23b"})
        fig.update_layout(margin=dict(t=10,b=10,l=5,r=5), legend=dict(orientation="h",y=-0.05), height=300)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Quick actions")
        if st.button("🧾 Generate bills for next month", use_container_width=True):
            next_month = (date.today().replace(day=28) + pd.Timedelta(days=4)).replace(day=1)
            month = next_month.strftime("%Y-%m")
            existing = q("SELECT COUNT(*) n FROM invoices WHERE billing_month=?", (month,)).iloc[0]["n"]
            if existing:
                st.info(f"Bills already exist for {month}.")
            else:
                residents = q("SELECT * FROM residents WHERE active=1")
                with conn() as db:
                    for _, r in residents.iterrows():
                        invno = f"INV-{month.replace('-', '')}-{int(r['id']):04d}"
                        db.execute("INSERT INTO invoices(invoice_no,resident_id,billing_month,amount,previous_dues,due_date,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                   (invno,int(r['id']),month,float(r['monthly_fee']),0,f"{month}-10","Pending",datetime.now().isoformat(timespec="seconds")))
                    db.commit()
                st.success(f"Created {len(residents)} demo invoices for {month}.")
                st.rerun()
        if st.button("📥 Export current month CSV", use_container_width=True):
            st.session_state["overview_export"] = inv.to_csv(index=False).encode("utf-8")
        if "overview_export" in st.session_state:
            st.download_button("Download invoices.csv", st.session_state["overview_export"], "societypay_invoices.csv", "text/csv", use_container_width=True)
        st.info("Demo transactions are simulated. No real bank or UPI account is connected.")
    st.subheader("Recent invoices")
    st.dataframe(inv[["invoice_no","flat_no","resident_name","billing_month","amount","due_date","status"]].sort_values("invoice_no", ascending=False).head(10), use_container_width=True, hide_index=True)

elif page == "Residents & Flats":
    st.title("Residents & Flats")
    st.caption("Manage the sample resident directory. All records are fictional demo data.")
    with st.expander("＋ Add a resident", expanded=False):
        with st.form("add_resident"):
            x1,x2,x3 = st.columns(3)
            flat = x1.text_input("Flat number", placeholder="A-301")
            building = x2.selectbox("Building", list("ABCD"))
            fee = x3.number_input("Monthly fee (₹)", min_value=0, value=3000, step=100)
            x4,x5,x6 = st.columns(3)
            name = x4.text_input("Resident name")
            phone = x5.text_input("Phone (dummy)")
            email = x6.text_input("Email (dummy)")
            submitted = st.form_submit_button("Add resident", type="primary")
            if submitted:
                if not flat.strip() or not name.strip(): st.error("Flat number and resident name are required.")
                else:
                    try:
                        q("INSERT INTO residents(flat_no,building,resident_name,phone,email,monthly_fee,active) VALUES(?,?,?,?,?,?,1)",(flat.strip().upper(),building,name.strip(),phone,email,float(fee)),read=False)
                        st.success("Resident added."); st.rerun()
                    except sqlite3.IntegrityError: st.error("That flat number already exists.")
    residents = q("SELECT id,flat_no,building,resident_name,phone,email,monthly_fee,active FROM residents ORDER BY building,flat_no")
    search = st.text_input("Search by flat or resident", placeholder="e.g. A-101 or Aarav")
    if search:
        residents = residents[residents.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
    st.dataframe(residents, use_container_width=True, hide_index=True, column_config={"monthly_fee":st.column_config.NumberColumn("Monthly fee",format="₹%.0f"),"active":st.column_config.CheckboxColumn("Active")})
    st.download_button("Export residents CSV", residents.to_csv(index=False).encode("utf-8"), "societypay_residents.csv", "text/csv")

elif page == "Invoices & Payments":
    st.title("Invoices & Payments")
    inv = q("SELECT i.id,i.invoice_no,r.flat_no,r.resident_name,i.billing_month,i.amount,i.previous_dues,i.due_date,i.status FROM invoices i JOIN residents r ON i.resident_id=r.id ORDER BY i.billing_month DESC, r.flat_no")
    f1,f2 = st.columns([1,1])
    months = sorted(inv.billing_month.dropna().unique().tolist(), reverse=True)
    selected_month = f1.selectbox("Billing month", ["All months"] + months)
    status_filter = f2.selectbox("Payment status", ["All statuses","Paid","Pending","Failed","Partial"])
    filtered = inv.copy()
    if selected_month != "All months": filtered = filtered[filtered.billing_month == selected_month]
    if status_filter != "All statuses": filtered = filtered[filtered.status == status_filter]
    st.dataframe(filtered.drop(columns=["id"]), use_container_width=True, hide_index=True, column_config={"amount":st.column_config.NumberColumn("Amount",format="₹%.0f"),"previous_dues":st.column_config.NumberColumn("Previous dues",format="₹%.0f")})
    st.download_button("Export filtered invoices", filtered.to_csv(index=False).encode("utf-8"), "societypay_invoices.csv", "text/csv")
    st.subheader("Payment history")
    payments = q("SELECT p.txn_id,i.invoice_no,r.flat_no,r.resident_name,p.amount,p.method,p.status,p.paid_at,p.note FROM payments p JOIN invoices i ON p.invoice_id=i.id JOIN residents r ON i.resident_id=r.id ORDER BY p.id DESC LIMIT 100")
    if payments.empty: st.info("No payments yet. Use Payment Simulator to create test transactions.")
    else: st.dataframe(payments, use_container_width=True, hide_index=True)

elif page == "Payment Simulator":
    st.title("Payment Simulator")
    st.warning("This is a mock checkout. Clicking a payment outcome does not transfer money.")
    pending = q("SELECT i.id,i.invoice_no,r.flat_no,r.resident_name,i.billing_month,i.amount,i.status FROM invoices i JOIN residents r ON i.resident_id=r.id WHERE i.status!='Paid' ORDER BY i.billing_month DESC,r.flat_no")
    if pending.empty:
        st.success("No unpaid invoices in the current demo data. Generate next month's bills from Overview to test more payments.")
    else:
        options = {f"{r['flat_no']} · {r['resident_name']} · {r['billing_month']} · {money(r['amount'])} · {r['status']}": int(r['id']) for _,r in pending.iterrows()}
        chosen = st.selectbox("Choose an invoice", list(options.keys()))
        row = pending[pending.id == options[chosen]].iloc[0]
        col1,col2 = st.columns([1,1])
        with col1:
            st.markdown("### Invoice summary")
            st.metric("Amount due", money(row.amount))
            st.write(f"**Invoice:** {row.invoice_no}")
            st.write(f"**Resident:** {row.resident_name}")
            st.write(f"**Flat:** {row.flat_no}")
            st.write(f"**Billing period:** {row.billing_month}")
        with col2:
            st.markdown("### Simulated checkout")
            method = st.selectbox("Payment method", ["UPI (simulated)","Net banking (simulated)","Card (simulated)"])
            st.text_input("Gateway", value="SocietyPay Mock Gateway", disabled=True)
            b1,b2,b3 = st.columns(3)
            outcome = None
            if b1.button("✓ Success", type="primary", use_container_width=True): outcome = "Success"
            if b2.button("✕ Fail", use_container_width=True): outcome = "Failed"
            if b3.button("… Pending", use_container_width=True): outcome = "Pending"
            if outcome:
                txn = f"TEST_TXN_{datetime.now().strftime('%y%m%d%H%M%S')}_{random.randint(100,999)}"
                q("INSERT INTO payments(txn_id,invoice_id,amount,method,status,paid_at,note) VALUES(?,?,?,?,?,?,?)",(txn,int(row.id),float(row.amount),method,outcome,datetime.now().isoformat(timespec="seconds"),"Mock gateway transaction"),read=False)
                if outcome == "Success": q("UPDATE invoices SET status='Paid' WHERE id=?",(int(row.id),),read=False)
                elif outcome == "Failed": q("UPDATE invoices SET status='Failed' WHERE id=?",(int(row.id),),read=False)
                elif outcome == "Pending": q("UPDATE invoices SET status='Pending' WHERE id=?",(int(row.id),),read=False)
                st.session_state["last_payment"] = {"txn":txn,"invoice":row.invoice_no,"flat":row.flat_no,"amount":float(row.amount),"status":outcome,"method":method}
                st.rerun()
    if "last_payment" in st.session_state:
        p = st.session_state["last_payment"]
        st.divider(); st.subheader("Latest simulated transaction")
        st.success("Payment successful (simulated)." if p["status"]=="Success" else ("Payment pending confirmation (simulated)." if p["status"]=="Pending" else "Payment failed (simulated)."))
        st.write(f"Transaction: `{p['txn']}` · Invoice: `{p['invoice']}` · Amount: **{money(p['amount'])}** · Status: **{p['status']}**")
        if p["status"] == "Success":
            receipt = pd.DataFrame([{"Receipt":"RCPT-"+p['txn'][-8:],"Transaction ID":p['txn'],"Invoice":p['invoice'],"Flat":p['flat'],"Amount (INR)":p['amount'],"Method":p['method'],"Status":"SUCCESS — SIMULATED","Timestamp":datetime.now().isoformat(timespec="seconds")}])
            st.download_button("Download demo receipt CSV", receipt.to_csv(index=False).encode("utf-8"), f"receipt_{p['txn']}.csv", "text/csv")

elif page == "Reconciliation":
    st.title("Reconciliation Centre")
    st.caption("Match bank-style demo transactions to invoices. This page does not connect to a real bank.")
    bank = q("SELECT * FROM bank_transactions ORDER BY id DESC")
    a,b,c = st.columns(3)
    a.metric("Demo bank transactions", len(bank))
    b.metric("Matched", int((bank.status == "Matched").sum()) if not bank.empty else 0)
    c.metric("Needs review", int((bank.status != "Matched").sum()) if not bank.empty else 0)
    st.subheader("Unmatched transactions")
    unmatched = bank[bank.status != "Matched"]
    if unmatched.empty: st.success("All demo bank transactions are matched.")
    else:
        st.dataframe(unmatched, use_container_width=True, hide_index=True)
        with st.form("match_bank_txn"):
            tx_options = {f"{r['reference']} · {r['payer']} · {money(r['amount'])}": int(r['id']) for _,r in unmatched.iterrows()}
            chosen_tx = st.selectbox("Select transaction", list(tx_options.keys()))
            candidates = q("SELECT i.invoice_no,r.flat_no,r.resident_name,i.amount,i.status,i.id FROM invoices i JOIN residents r ON i.resident_id=r.id ORDER BY i.billing_month DESC,r.flat_no")
            inv_options = {f"{r['invoice_no']} · {r['flat_no']} · {r['resident_name']} · {money(r['amount'])} · {r['status']}": int(r['id']) for _,r in candidates.iterrows()}
            chosen_inv = st.selectbox("Match to invoice", list(inv_options.keys()))
            submitted = st.form_submit_button("Confirm match", type="primary")
            if submitted:
                txid = tx_options[chosen_tx]; invoice_id = inv_options[chosen_inv]
                invoice_no = candidates[candidates.id == invoice_id].iloc[0].invoice_no
                q("UPDATE bank_transactions SET matched_invoice=?,status='Matched' WHERE id=?",(invoice_no,txid),read=False)
                st.success(f"Matched transaction to {invoice_no}."); st.rerun()
    st.info("In a production implementation, bank statement imports and gateway settlement reports would be validated, deduplicated and reconciled with an audit trail.")

elif page == "Reports & Exports":
    st.title("Reports & Exports")
    inv = q("SELECT i.invoice_no,r.flat_no,r.building,r.resident_name,r.phone,i.billing_month,i.amount,i.previous_dues,i.due_date,i.status FROM invoices i JOIN residents r ON i.resident_id=r.id ORDER BY i.billing_month DESC,r.building,r.flat_no")
    pay = q("SELECT p.txn_id,i.invoice_no,r.flat_no,r.resident_name,p.amount,p.method,p.status,p.paid_at,p.note FROM payments p JOIN invoices i ON p.invoice_id=i.id JOIN residents r ON i.resident_id=r.id ORDER BY p.paid_at DESC")
    residents = q("SELECT flat_no,building,resident_name,phone,email,monthly_fee,active FROM residents ORDER BY building,flat_no")
    st.subheader("Download data")
    x,y,z = st.columns(3)
    x.download_button("📄 Invoices CSV", inv.to_csv(index=False).encode("utf-8"), "invoices_report.csv", "text/csv", use_container_width=True)
    y.download_button("💳 Payments CSV", pay.to_csv(index=False).encode("utf-8"), "payments_report.csv", "text/csv", use_container_width=True)
    z.download_button("👥 Residents CSV", residents.to_csv(index=False).encode("utf-8"), "residents_report.csv", "text/csv", use_container_width=True)
    st.subheader("Monthly collection trend")
    if inv.empty: st.info("No invoice data yet.")
    else:
        trend = inv.assign(paid_amount=inv.amount.where(inv.status == "Paid", 0)).groupby("billing_month", as_index=False).agg(billed=("amount","sum"), collected=("paid_amount","sum"))
        trend_long = trend.melt(id_vars="billing_month", var_name="metric", value_name="amount")
        fig = px.bar(trend_long, x="billing_month", y="amount", color="metric", barmode="group", labels={"billing_month":"Billing month","amount":"Amount (₹)","metric":"Metric"})
        fig.update_layout(height=350, margin=dict(t=20,b=20))
        st.plotly_chart(fig, use_container_width=True)
    st.caption("All downloadable records are fictional sample data. Do not use this prototype to store real resident information.")

st.divider()
st.caption("SocietyPay · Educational prototype · Mock payments only · Not production-ready for real financial transactions")
