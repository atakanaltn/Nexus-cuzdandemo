import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(
    page_title="ONYX Pro",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (ONYX BLACK THEME) ---
st.markdown("""
    <style>
        .stApp { background-color: #050505; }
        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #1a1a1a, #000000);
            border: 1px solid #333;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.6);
        }
        h1, h2, h3 { color: #E0E0E0 !important; font-family: 'Helvetica Neue', sans-serif; }
        th { background-color: #111 !important; color: #D4AF37 !important; border-bottom: 1px solid #333; }
        section[data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #222; }
        div.stButton > button {
            width: 100%; background-color: #111; color: #D4AF37; border: 1px solid #444;
        }
        div.stButton > button:hover { border-color: #D4AF37; color: #FFF; }
    </style>
""", unsafe_allow_html=True)

# --- 3. VERİTABANI YÖNETİMİ (SQLITE) ---
DB_FILE = "onyx_database.db"

def init_db():
    """Veritabanı ve tabloları oluşturur"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Kullanıcılar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, join_date TEXT)''')
    # İşlemler Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, 
                  date TEXT, type TEXT, category TEXT, amount REAL, description TEXT)''')
    # Limit Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS limits 
                 (username TEXT PRIMARY KEY, monthly_limit REAL)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def add_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, join_date) VALUES (?,?,?)', 
                  (username, make_hashes(password), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False # Kullanıcı adı zaten var

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password = ?', (username, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data

# --- KULLANICI FONKSİYONLARI ---
def get_user_data(username):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM transactions WHERE username = ?", conn, params=(username,))
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

def add_transaction(username, date, type, category, amount, description):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)',
              (username, date, type, category, amount, description))
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def get_limit(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT monthly_limit FROM limits WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else 20000

def set_limit(username, limit):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO limits (username, monthly_limit) VALUES (?, ?)', (username, limit))
    conn.commit()
    conn.close()

# --- ADMIN FONKSİYONLARI ---
def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT username, join_date FROM users", conn)
    conn.close()
    return df

# --- BAŞLANGIÇ ---
init_db()

# Kategoriler
GIDER_KATEGORILERI = ["Abonelik - İnternet/Dijital", "Gıda - Market", "Gıda - Restoran", "Konut - Kira", "Fatura", "Ulaşım", "Kişisel", "Eğlence", "Diğer"]
GELIR_KATEGORILERI = ["Maaş", "Ek Gelir", "Yatırım", "Diğer"]

# --- SİSTEM AKIŞI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

# 1. GİRİŞ EKRANI (LOGIN / SIGNUP)
if not st.session_state['logged_in']:
    st.title("💎 ONYX Giriş")
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap"):
                # ADMIN GİRİŞİ
                if username == "admin" and password == "12345":
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = "admin"
                    st.rerun()
                # NORMAL GİRİŞ
                elif login_user(username, password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.success("Giriş Başarılı!")
                    st.rerun()
                else:
                    st.error("Hatalı Kullanıcı Adı veya Şifre")
    
    with tab2:
        with st.form("signup_form"):
            new_user = st.text_input("Yeni Kullanıcı Adı")
            new_pass = st.text_input("Yeni Şifre", type="password")
            if st.form_submit_button("Kayıt Ol"):
                if add_user(new_user, new_pass):
                    st.success("Hesap oluşturuldu! Giriş yap sekmesine gidin.")
                else:
                    st.warning("Bu kullanıcı adı zaten alınmış.")

# 2. YÖNETİCİ PANELİ (ADMIN)
elif st.session_state['username'] == "admin":
    st.sidebar.title("👑 ADMIN PANEL")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state['logged_in'] = False
        st.rerun()
    
    st.title("Yönetim Paneli")
    
    # İstatistikler
    users_df = get_all_users()
    total_users = len(users_df) - 1 # Admin hariç
    
    c1, c2 = st.columns(2)
    c1.metric("Toplam Üye", total_users)
    c2.metric("Sistem Saati", datetime.now().strftime("%H:%M"))
    
    st.subheader("Üye Listesi")
    st.dataframe(users_df)
    
    st.info("Yönetici olarak kullanıcı verilerine müdahale edemezsiniz (Gizlilik İlkesi). Sadece genel istatistikleri görebilirsiniz.")

# 3. KULLANICI ARAYÜZÜ (USER DASHBOARD)
else:
    curr_user = st.session_state['username']
    
    # Verileri Çek
    df = get_user_data(curr_user)
    limit = get_limit(curr_user)
    
    # YAN MENÜ
    with st.sidebar:
        st.title(f"👤 {curr_user.upper()}")
        st.caption("ONYX Pro Member")
        st.markdown("---")
        menu = st.radio("MENÜ", ["📊 Dashboard", "📝 İşlem Yönetimi", "📉 Limit & Analiz", "🔄 Abonelikler"])
        st.markdown("---")
        if st.button("Çıkış Yap"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- SAYFA: DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Finansal Özet")
        if df.empty:
            st.info("Hoşgeldiniz! İşlem Yönetimi menüsünden ilk kaydınızı oluşturun.")
        else:
            simdi = datetime.now()
            df_bu_ay = df[(df["date"].dt.month == simdi.month) & (df["date"].dt.year == simdi.year)]
            
            gelir = df_bu_ay[df_bu_ay["type"]=="Gelir"]["amount"].sum()
            gider = df_bu_ay[df_bu_ay["type"]=="Gider"]["amount"].sum()
            toplam_kasa = df[df["type"]=="Gelir"]["amount"].sum() - df[df["type"]=="Gider"]["amount"].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💎 TOPLAM KASA", f"{toplam_kasa:,.2f} ₺")
            c2.metric("📥 Bu Ay Gelir", f"{gelir:,.2f} ₺")
            c3.metric("📤 Bu Ay Gider", f"{gider:,.2f} ₺")
            c4.metric("Net Durum", f"{gelir-gider:,.2f} ₺", delta_color="normal" if (gelir-gider)>=0 else "inverse")
            
            st.markdown("---")
            if not df_bu_ay.empty:
                fig = px.area(df_bu_ay, x="date", y="amount", color="type", 
                              color_discrete_map={"Gelir": "#00FFA3", "Gider": "#FF4B4B"}, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

    # --- SAYFA: İŞLEM YÖNETİMİ ---
    elif menu == "📝 İşlem Yönetimi":
        st.title("İşlem Ekle")
        with st.form("add_tr"):
            c1, c2, c3 = st.columns(3)
            t_type = c1.selectbox("Tür", ["Gider", "Gelir"])
            t_date = c2.date_input("Tarih", datetime.now())
            t_amount = c3.number_input("Tutar", min_value=0.0)
            t_cat = st.selectbox("Kategori", GIDER_KATEGORILERI if t_type=="Gider" else GELIR_KATEGORILERI)
            t_desc = st.text_input("Açıklama")
            if st.form_submit_button("Kaydet"):
                add_transaction(curr_user, t_date, t_type, t_cat, t_amount, t_desc)
                st.success("Kaydedildi")
                st.rerun()
        
        st.divider()
        st.subheader("Geçmiş Kayıtlar")
        if not df.empty:
            # Basit Silme Arayüzü
            for index, row in df.sort_values("date", ascending=False).iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 3, 1])
                c1.write(row['date'].strftime('%d.%m.%Y'))
                c2.write(row['type'])
                c3.write(f"{row['amount']:,.2f} ₺")
                c4.write(row['description'])
                if c5.button("Sil", key=row['id']):
                    delete_transaction(row['id'])
                    st.rerun()

    # --- SAYFA: LİMİT ---
    elif menu == "📉 Limit & Analiz":
        st.title("Bütçe Limiti")
        curr_limit = get_limit(curr_user)
        
        new_limit = st.number_input("Aylık Limit (TL)", value=float(curr_limit))
        if st.button("Güncelle"):
            set_limit(curr_user, new_limit)
            st.success("Limit güncellendi!")
            st.rerun()
            
        st.divider()
        # Analiz
        simdi = datetime.now()
        bu_ay_gider = 0
        if not df.empty:
             bu_ay_gider = df[(df["date"].dt.month == simdi.month) & (df["type"]=="Gider")]["amount"].sum()
             
        yuzde = (bu_ay_gider / curr_limit) * 100 if curr_limit > 0 else 0
        st.write(f"Harcama: {bu_ay_gider:,.2f} / Limit: {curr_limit:,.2f}")
        st.progress(min(yuzde/100, 1.0))
        if yuzde >= 100: st.error("LİMİT AŞILDI!")

    # --- SAYFA: ABONELİKLER ---
    elif menu == "🔄 Abonelikler":
        st.title("Abonelik Takibi")
        st.info("'Abonelik - İnternet/Dijital' kategorisindeki harcamalar burada görünür.")
        
        if not df.empty:
            subs = df[df["category"] == "Abonelik - İnternet/Dijital"]
            if not subs.empty:
                for _, row in subs.iterrows():
                    st.write(f"**{row['description']}** - {row['amount']} TL (Son İşlem: {row['date'].strftime('%d.%m.%Y')})")
            else:
                st.warning("Abonelik kaydı yok.")