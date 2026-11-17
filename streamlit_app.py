
import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import qrcode
from io import BytesIO
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="FarmChain",
    page_icon="🌱",
    layout="wide"
)

# ---------------- DATABASE ----------------
DB = "farmchain.db"

def connect():
    return sqlite3.connect(DB)

def initialize():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                farmer TEXT,
                location TEXT,
                category TEXT,
                harvest_date TEXT,
                notes TEXT,
                quality TEXT,
                timestamp TEXT,
                previous_hash TEXT,
                block_hash TEXT
            )
        """)

initialize()

def make_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()

# ---------------- DESIGN ----------------
st.markdown("""
<style>
.stApp {
    background-color: #f5f8f2;
}
h1, h2, h3 {
    color: #205c37;
}
[data-testid="stSidebar"] {
    background-color: #e4efdf;
}
div.stButton > button {
    background-color: #246b45;
    color: white;
    border-radius: 8px;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.title("🌱 FarmChain")
st.sidebar.caption("Agricultural Supply Chain Management")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Register Product",
        "Product Tracking",
        "Blockchain Verification",
        "Analytics"
    ]
)

st.sidebar.divider()
st.sidebar.caption("Powered by Python & Streamlit")

# ---------------- DASHBOARD ----------------
if page == "Dashboard":

    st.title("🌱 FarmChain Dashboard")
    st.write("Transparent and secure agricultural supply chain management.")

    with connect() as con:
        total = pd.read_sql_query(
            "SELECT COUNT(*) AS count FROM products", con
        ).iloc[0]["count"]

        farmers = pd.read_sql_query(
            "SELECT COUNT(DISTINCT farmer) AS count FROM products", con
        ).iloc[0]["count"]

        categories = pd.read_sql_query(
            "SELECT COUNT(DISTINCT category) AS count FROM products", con
        ).iloc[0]["count"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Products", total)
    c2.metric("Registered Farmers", farmers)
    c3.metric("Product Categories", categories)

    st.subheader("About FarmChain")
    st.write("""
    FarmChain helps maintain agricultural product records,
    track harvested products and demonstrate blockchain-inspired
    tamper-evident record verification.
    """)

    st.info("Register a product to start building your supply-chain ledger.")

# ---------------- REGISTER PRODUCT ----------------
elif page == "Register Product":

    st.title("🧑‍🌾 Register Agricultural Product")

    with st.form("product_form"):

        name = st.text_input("Product Name")
        farmer = st.text_input("Farmer Name")
        location = st.text_input("Farm Location")

        category = st.selectbox(
            "Category",
            ["Vegetables", "Fruits", "Grains", "Spices", "Other"]
        )

        harvest_date = st.date_input("Harvest Date")
        quality = st.selectbox(
            "Quality Grade",
            ["A", "B", "C"]
        )

        notes = st.text_area("Additional Notes")

        submitted = st.form_submit_button("Register Product")

        if submitted:

            if not name.strip() or not farmer.strip() or not location.strip():
                st.error("Please complete all required fields.")

            else:
                timestamp = datetime.now().isoformat()

                with connect() as con:

                    previous = con.execute(
                        "SELECT block_hash FROM products ORDER BY id DESC LIMIT 1"
                    ).fetchone()

                    previous_hash = previous[0] if previous else "GENESIS"

                    product_id = con.execute("""
                        INSERT INTO products
                        (name, farmer, location, category, harvest_date,
                         notes, quality, timestamp, previous_hash, block_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        name, farmer, location, category,
                        str(harvest_date), notes, quality,
                        timestamp, previous_hash, ""
                    )).lastrowid

                    block_data = (
                        f"{product_id}|{name}|{farmer}|{location}|"
                        f"{category}|{harvest_date}|{quality}|"
                        f"{timestamp}|{previous_hash}"
                    )

                    block_hash = make_hash(block_data)

                    con.execute(
                        "UPDATE products SET block_hash=? WHERE id=?",
                        (block_hash, product_id)
                    )

                st.success(f"Product #{product_id} registered successfully!")
                st.code(block_hash, language="text")

# ---------------- PRODUCT TRACKING ----------------
elif page == "Product Tracking":

    st.title("📦 Product Tracking")

    with connect() as con:
        products = pd.read_sql_query(
            "SELECT * FROM products ORDER BY id DESC", con
        )

    if products.empty:
        st.warning("No products registered yet.")

    else:
        product_id = st.selectbox(
            "Select Product ID",
            products["id"].tolist()
        )

        product = products[products["id"] == product_id].iloc[0]

        st.subheader(product["name"])

        c1, c2 = st.columns(2)

        with c1:
            st.write("**Farmer:**", product["farmer"])
            st.write("**Location:**", product["location"])
            st.write("**Category:**", product["category"])

        with c2:
            st.write("**Harvest Date:**", product["harvest_date"])
            st.write("**Quality:**", product["quality"])
            st.write("**Registered:**", product["timestamp"])

        st.subheader("Product QR Code")

        qr = qrcode.make(
            f"FarmChain Product ID: {product_id}\n"
            f"Product: {product['name']}\n"
            f"Farmer: {product['farmer']}"
        )

        image = BytesIO()
        qr.save(image, format="PNG")

        st.image(image.getvalue(), width=200)

        st.download_button(
            "Download QR Code",
            data=image.getvalue(),
            file_name=f"FarmChain_Product_{product_id}.png",
            mime="image/png"
        )

# ---------------- BLOCKCHAIN VERIFICATION ----------------
elif page == "Blockchain Verification":

    st.title("🔗 Blockchain Verification")

    with connect() as con:
        products = pd.read_sql_query(
            "SELECT * FROM products ORDER BY id ASC", con
        )

    if products.empty:
        st.warning("No records available for verification.")

    else:
        valid = True
        previous_hash = "GENESIS"

        for _, row in products.iterrows():

            block_data = (
                f"{row['id']}|{row['name']}|{row['farmer']}|"
                f"{row['location']}|{row['category']}|"
                f"{row['harvest_date']}|{row['quality']}|"
                f"{row['timestamp']}|{previous_hash}"
            )

            calculated_hash = make_hash(block_data)

            if row["previous_hash"] != previous_hash:
                valid = False

            if row["block_hash"] != calculated_hash:
                valid = False

            previous_hash = row["block_hash"]

        if valid:
            st.success("All product records passed hash-chain verification.")
        else:
            st.error("Verification failed! A record may have been modified.")

        for _, row in products.iterrows():
            with st.expander(f"Block #{row['id']} - {row['name']}"):
                st.write("Previous Hash")
                st.code(row["previous_hash"])
                st.write("Block Hash")
                st.code(row["block_hash"])

# ---------------- ANALYTICS ----------------
elif page == "Analytics":

    st.title("📊 FarmChain Analytics")

    with connect() as con:
        products = pd.read_sql_query(
            "SELECT * FROM products", con
        )

    if products.empty:
        st.warning("Register products to view analytics.")

    else:
        st.subheader("Products by Category")
        st.bar_chart(products["category"].value_counts())

        st.subheader("Products by Quality")
        st.bar_chart(products["quality"].value_counts())

        st.subheader("Registered Products")
        st.dataframe(
            products.drop(columns=["notes"]),
            use_container_width=True
        )

st.divider()
st.caption("FarmChain | Agricultural Supply Chain Management")
