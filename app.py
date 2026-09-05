import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Zarządzanie Wydatkami", page_icon="💰", layout="centered")
st.title("💰 Budżet Domowy")

DB_HOST = os.getenv("DB_HOST")

@st.cache_resource
def get_db_engine():
    if DB_HOST:
        DB_USER = os.getenv("POSTGRES_USER", "pi_user")
        DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "TwojeBezpieczneHaslo123!")
        DB_NAME = os.getenv("POSTGRES_DB", "finanse_db")
        db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
    else:
        db_url = "sqlite:///finanse.db"
        
    return create_engine(db_url)

try:
    engine = get_db_engine()
    
    with engine.begin() as conn:
        if DB_HOST:
            # PostgreSQL
            sql_create_table = """
                CREATE TABLE IF NOT EXISTS wydatki (
                    id SERIAL PRIMARY KEY,
                    kategoria VARCHAR(50),
                    kwota NUMERIC(10, 2),
                    data DATE DEFAULT CURRENT_DATE
                );
            """
        else:
            # SQLite
            sql_create_table = """
                CREATE TABLE IF NOT EXISTS wydatki (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kategoria VARCHAR(50),
                    kwota NUMERIC(10, 2),
                    data DATE DEFAULT CURRENT_DATE
                );
            """
        conn.execute(text(sql_create_table))

    # information about database
    db_type = "PostgreSQL (Docker)" if DB_HOST else "SQLite (Lokalnie)"
    st.caption(f"Połączono z bazą: **{db_type}**")

    # add expense
    st.subheader("Wprowadź nowy wydatek")
    with st.form("form_wydatek", clear_on_submit=True):
        kategoria = st.selectbox("Kategoria", ["Jedzenie", "Rachunki", "Rozrywka", "Transport", "Inne"])
        kwota = st.number_input("Kwota (PLN)", min_value=0.00, step=0.01, format="%.2f")
        submitted = st.form_submit_button("Dodaj wydatek")
        
        if submitted:
            df_new = pd.DataFrame([{"kategoria": kategoria, "kwota": kwota}])
            df_new.to_sql("wydatki", engine, if_exists="append", index=False)
            st.success(f"Dodano wydatek: {kwota:.2f} zł ({kategoria})")

    st.divider()

    # last inputs
    st.subheader("Ostatnie wpisy")
    
    with engine.connect() as conn:
        df_wydatki = pd.read_sql_query(text("SELECT * FROM wydatki ORDER BY id DESC;"), conn)

    if not df_wydatki.empty:
        # last 10 inputs
        st.dataframe(df_wydatki.head(10), use_container_width=True)
        
        total_sum = df_wydatki["kwota"].sum()
        st.metric(label="Łączna suma wydatków w bazie", value=f"{total_sum:.2f} PLN")
    else:
        st.info("Baza danych jest jeszcze pusta. Dodaj swój pierwszy wydatek!")

except Exception as e:
    st.error(f"Błąd połączenia lub operacji na bazie danych: {e}")