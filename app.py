import os
import pandas as pd
import streamlit as st
from datetime import date
from sqlalchemy import create_engine, text, Text, Table, Column, Integer, String, Numeric, Date, MetaData

st.set_page_config(page_title="money_money", page_icon="💰", layout="centered")
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
    
    st.sidebar.header("Ustawienia bazy")
    if st.sidebar.button("⚠️ Usuń i zresetuj bazę danych"):
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS transakcje;"))
            conn.execute(text("DROP TABLE IF EXISTS wydatki;"))
        st.cache_resource.clear()
        st.sidebar.success("Baza zresetowana! Odśwież stronę (F5).")
    
    
    metadata = MetaData()
    transakcje_table = Table(
        'transakcje', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('typ', String(20)),
        Column('osoba', String(2)),
        Column('kategoria', String(50)),
        Column('kwota', Numeric(10, 2)),
        Column('data', Date, default=date.today),
        Column('notatka', Text)
    )
    metadata.create_all(engine)

    db_type = "PostgreSQL (Docker)" if DB_HOST else "SQLite (Lokalnie)"
    st.caption(f"Połączono z bazą: **{db_type}**")

    st.subheader("Wprowadź nową transakcję")

    kto = st.radio("**Kto?**", ["K", "M"], horizontal=True)
    typ = st.radio("**Typ transakcji**", ["Wydatek", "Przychód"], horizontal=True)
    
    STAWKI_OSOB = {
        "K": 31.4,
        "M": 32.
    }
    
    domyslna_stawka = STAWKI_OSOB.get(kto, 30.0)
    
    if typ == "Wydatek":
        kategorie = ["🥑 Spożywcze", "☕️ Restauracje", "💄 Kosmetyki", "🏠 Mieszkanie", "👕 Ubrania", "🎥 Atrakcje", "🎁 Prezenty", "🚘 Paliwo", "🚍 Komunikacja", "💊 Lekarz", "🧴 Chemia gospodarcza", "❔ Inne"]
        tryb_przychodu = "Wpisz kwotę bezpośrednio"
    else:
        kategorie = ["💵 Wynagrodzenie", "🔝 Premia", "🎁 Prezent", "📈 Inwestycje", "❔ Inne"]
        tryb_przychodu = st.radio(
            "Sposób wprowadzania kwoty", 
            ["Wpisz kwotę bezpośrednio", "Oblicz z godzin pracy"], 
            horizontal=True
        )

    with st.form("form_transakcja", clear_on_submit=True):
        kategoria = st.selectbox("Kategoria", kategorie)

        
        
        if tryb_przychodu == "Oblicz z godzin pracy":
            col_g, col_s = st.columns(2)
            with col_g:
                godziny = st.number_input("Liczba godzin", min_value=0.5, max_value=24.0, value=8.0, step=0.5)
            with col_s:
                stawka = st.number_input("Stawka za godzinę (PLN)", min_value=0.0, value=domyslna_stawka, step=1.0)
            
            kwota = round(godziny * stawka, 2)
            st.info(f"Wyliczony zarobek: **{kwota:.2f} PLN** ({godziny}h × {stawka:.2f} zł/h)")
        else:
            kwota = st.number_input("Kwota (PLN)", min_value=0.0, step=0.0, format="%.2f")
            
        wybrana_data = st.date_input("Data transakcji", value=date.today())
        
        notatka = st.text_input("Notatka (opcjonalnie)", placeholder="np. Zakupy w Lidlu")
        
        submitted = st.form_submit_button("Zapisz")
        
        if submitted:
            df_new = pd.DataFrame([{
                "typ": typ,
                "osoba": kto,
                "kategoria": kategoria[2:], 
                "kwota": kwota, 
                "data": wybrana_data,
                "notatka": notatka
            }])
            df_new.to_sql("transakcje", engine, if_exists="append", index=False)
            st.balloons()
            st.success(f"Zapisano {typ.lower()}: {kwota:.2f} zł ({kategoria})")

    st.divider()

    st.subheader("Podsumowanie finansowe")
    with engine.connect() as conn:
        df_transakcje = pd.read_sql_query(text("SELECT * FROM transakcje ORDER BY id DESC;"), conn)

    if not df_transakcje.empty:

        przychody = df_transakcje[df_transakcje["typ"] == "Przychód"]["kwota"].sum()
        wydatki = df_transakcje[df_transakcje["typ"] == "Wydatek"]["kwota"].sum()
        bilans = przychody - wydatki

        col1, col2, col3 = st.columns(3)
        col1.metric("Przychody", f"{przychody:.2f} PLN")
        col2.metric("Wydatki", f"{wydatki:.2f} PLN")
        col3.metric("Bilans", f"{bilans:.2f} PLN", delta=f"{bilans:.2f} PLN")

        st.subheader("Ostatnie transakcje")
        st.dataframe(df_transakcje.head(10), use_container_width=True)
    else:
        st.info("Baza danych jest pusta. Dodaj pierwszą transakcję!")

except Exception as e:
    st.error(f"Błąd połączenia lub operacji na bazie danych: {e}")