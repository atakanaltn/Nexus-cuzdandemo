import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(
    page_title="ONYX Pro V11",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TASARIM (ONYX THEME) ---
st.markdown("""
    <style>
        .stApp { background-color: #050505; }
        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #1a1a1a, #000000);
            border: 1px solid #333; padding: 15px; border-radius: 12px;
        }
        h1, h2, h3 { color: #E0E0E0 !important; font-family: 'Helvetica Neue', sans-serif; }
        th { background-color: #111 !important; color: #D4AF37 !important; border-bottom: 1px solid #333; }
        section[data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #222; }
        div.stButton > button {
            width: 100%; background-color: #111; color: #D4AF37; border: 1px solid #444;
        }
        div.stButton > button:hover { border-color: #D4AF37; color: #FFF; }
        
        /* Progress Bar Renkleri */
        .stProgress > div > div > div > div { background-color: #00FFA3; }
    </style>
""", unsafe_allow_html=True)

# --- 3. VERİTABANI VE KATEGORİLER ---
DB_FILE = "onyx_database.db"

# KATEGORİ LİSTELERİ
GIDER_KATEGORILERI = [
    "Abonelik - İnternet/Dijital", "Gıda - Market", "Gıda - Restoran", 
    "Konut - Kira", "Fatura - Elektrik/Su", "Fatura - Telefon/Net",
    "Ulaşım - Yakıt", "Ulaşım - Toplu Taşıma",
    "Kişisel - Giyim", "Kişisel - Bakım", "Sağlık", "Eğlence", "Eğitim", "Diğer"
]
# GELİR KATEGORİLERİ (SADELEŞTİRİLDİ)
GELIR_KATEGORILERI = ["Maaş / Düzenli", "Ek Gelir / Ticaret", "Yatırım", "Diğer"]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Kullanıcılar
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, join_date TEXT)''')
    # İşlemler
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, 
                  date TEXT, type TEXT, category TEXT, amount REAL, description TEXT)''')
    # Genel Limit
    c.execute('''CREATE TABLE IF NOT EXISTS limits 
                 (username TEXT PRIMARY KEY, monthly_limit REAL)''')
    # Kategori Bazlı Limitler (YENİ TABLO)
    c.execute('''CREATE TABLE IF NOT EXISTS cat_limits 
                 (username TEXT, category TEXT, limit_amount REAL, PRIMARY KEY (username, category))''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

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
        return False

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password = ?', (username, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data

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

# --- LİMİT FONKSİYONLARI ---
def get_global_limit(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT monthly_limit FROM limits WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else 20000

def set_global_limit(username, limit):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO limits (username, monthly_limit) VALUES (?, ?)', (username, limit))
    conn.commit()
    conn.close()

def set_cat_limit(username, category, limit):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO cat_limits (username, category, limit_amount) VALUES (?, ?, ?)', 
              (username, category, limit))
    conn.commit()
    conn.close()

def get_cat_limits_dict(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT category, limit_amount FROM cat_limits WHERE username = ?', (username,))
    data = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in data}

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT username, join_date FROM users", conn)
    conn.close()
    return df

# --- BAŞLANGIÇ ---
init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

# ==========================================
# 1. GİRİŞ EKRANI
# ==========================================
if not st.session_state['logged_in']:
    st.title("💎 ONYX Giriş")
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    with tab1:
        with st.form("login"):
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş"):
                if u == "admin" and p == "12345":
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = "admin"
                    st.rerun()
                elif login_user(u, p):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    st.success("Başarılı")
                    st.rerun()
                else:
                    st.error("Hatalı!")
    with tab2:
        with st.form("signup"):
            nu = st.text_input("Kullanıcı Adı")
            np = st.text_input("Şifre", type="password")
            if st.form_submit_button("Kayıt Ol"):
                if add_user(nu, np):
                    st.success("Kayıt başarılı! Giriş yapın.")
                else:
                    st.warning("Kullanıcı adı dolu.")

# ==========================================
# 2. YÖNETİCİ PANELİ
# ==========================================
elif st.session_state['username'] == "admin":
    st.sidebar.title("👑 ADMIN")
    if st.sidebar.button("Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()
    
    st.title("Yönetici Paneli")
    users_df = get_all_users()
    st.metric("Toplam Üye", len(users_df))
    
    user_list = users_df[users_df['username'] != 'admin']['username'].tolist()
    if user_list:
        target = st.selectbox("Kullanıcı İncele:", user_list)
        if target:
            df = get_user_data(target)
            if not df.empty:
                gelir = df[df['type']=='Gelir']['amount'].sum()
                gider = df[df['type']=='Gider']['amount'].sum()
                st.write(f"**{target}** - Net Varlık: {gelir-gider:,.2f} ₺")
                st.dataframe(df)
    else:
        st.warning("Üye yok.")

# ==========================================
# 3. KULLANICI ARAYÜZÜ
# ==========================================
else:
    curr_user = st.session_state['username']
    df = get_user_data(curr_user)
    
    with st.sidebar:
        st.title(f"👤 {curr_user}")
        st.markdown("---")
        menu = st.radio("MENÜ", ["📊 Dashboard", "📝 İşlem Ekle", "📉 Limit & Analiz", "🔄 Abonelikler"])
        st.markdown("---")
        if st.button("Çıkış"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Finansal Özet")
        if df.empty:
            st.info("Henüz veri yok.")
        else:
            simdi = datetime.now()
            df_ay = df[(df["date"].dt.month == simdi.month) & (df["date"].dt.year == simdi.year)]
            gelir = df_ay[df_ay["type"]=="Gelir"]["amount"].sum()
            gider = df_ay[df_ay["type"]=="Gider"]["amount"].sum()
            net = gelir - gider
            total_kasa = df[df["type"]=="Gelir"]["amount"].sum() - df[df["type"]=="Gider"]["amount"].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💎 TOPLAM KASA", f"{total_kasa:,.2f} ₺")
            c2.metric("📥 Bu Ay Gelir", f"{gelir:,.2f} ₺")
            c3.metric("📤 Bu Ay Gider", f"{gider:,.2f} ₺")
            c4.metric("Net", f"{net:,.2f} ₺", delta_color="normal" if net>=0 else "inverse")
            
            st.divider()
            
            # Pasta Grafik (Gider Dağılımı)
            c_graf1, c_graf2 = st.columns(2)
            with c_graf1:
                if not df_ay[df_ay["type"]=="Gider"].empty:
                    st.subheader("Harcama Dağılımı")
                    fig = px.pie(df_ay[df_ay["type"]=="Gider"], values="amount", names="category", hole=0.5, template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Bu ay gider yok.")
            with c_graf2:
                 if not df_ay.empty:
                    st.subheader("Günlük Akış")
                    fig2 = px.bar(df_ay, x="date", y="amount", color="type", color_discrete_map={"Gelir":"#00FFA3", "Gider":"#FF4B4B"}, template="plotly_dark")
                    st.plotly_chart(fig2, use_container_width=True)

    # --- İŞLEM EKLE ---
    elif menu == "📝 İşlem Ekle":
        st.title("İşlem Ekle")
        with st.form("add"):
            c1, c2, c3 = st.columns(3)
            typ = c1.selectbox("Tür", ["Gider", "Gelir"])
            dat = c2.date_input("Tarih", datetime.now())
            amt = c3.number_input("Tutar", min_value=0.0, step=50.0)
            # KATEGORİLER BURADA AYARLANDI
            cat = st.selectbox("Kategori", GIDER_KATEGORILERI if typ=="Gider" else GELIR_KATEGORILERI)
            desc = st.text_input("Açıklama")
            if st.form_submit_button("Kaydet"):
                add_transaction(curr_user, dat, typ, cat, amt, desc)
                st.success("Kaydedildi")
                st.rerun()
        
        st.subheader("Geçmiş")
        if not df.empty:
            st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)
            # Silme özelliği
            for idx, row in df.sort_values("date", ascending=False).head(5).iterrows():
                c_a, c_b = st.columns([4, 1])
                c_a.text(f"{row['date'].strftime('%d.%m')} | {row['category']} | {row['amount']} TL")
                if c_b.button("Sil", key=f"del_{row['id']}"):
                    delete_transaction(row['id'])
                    st.rerun()

    # --- LİMİT & ANALİZ (YENİ ALTYAPI) ---
    elif menu == "📉 Limit & Analiz":
        st.title("Bütçe Limitleri")
        
        # 1. Kategori Limit Ayarlama
        with st.expander("🛠️ Kategori Limiti Belirle/Güncelle", expanded=False):
            with st.form("cat_limit_form"):
                c_l1, c_l2 = st.columns(2)
                secilen_kat = c_l1.selectbox("Kategori Seç", GIDER_KATEGORILERI)
                secilen_limit = c_l2.number_input("Limit (TL)", min_value=0.0, step=500.0)
                if st.form_submit_button("Limiti Kaydet"):
                    set_cat_limit(curr_user, secilen_kat, secilen_limit)
                    st.success(f"{secilen_kat} için limit {secilen_limit} TL olarak ayarlandı.")
                    st.rerun()

        st.divider()
        
        # 2. Limit Analizi (Progress Bars)
        st.subheader("Bu Ayın Limit Durumu")
        
        simdi = datetime.now()
        if not df.empty:
            # Bu ayın giderlerini çek
            df_gider = df[(df["date"].dt.month == simdi.month) & 
                          (df["date"].dt.year == simdi.year) & 
                          (df["type"] == "Gider")]
            
            # Kullanıcının tüm limitlerini çek
            user_limits = get_cat_limits_dict(curr_user)
            
            if not user_limits:
                st.info("Henüz kategori bazlı limit belirlemediniz. Yukarıdaki panelden ekleyin.")
            
            # Her limit için bar oluştur
            for kat, limit in user_limits.items():
                # O kategorideki harcamayı bul
                harcanan = df_gider[df_gider["category"] == kat]["amount"].sum()
                
                if limit > 0:
                    yuzde = (harcanan / limit) * 100
                    bar_val = min(yuzde / 100, 1.0)
                    
                    col_bar1, col_bar2 = st.columns([3, 1])
                    with col_bar1:
                        st.write(f"**{kat}**")
                        # Renkli Bar Mantığı
                        if yuzde >= 100:
                            st.progress(bar_val)
                            st.error(f"⚠️ LİMİT AŞILDI! ({harcanan:,.0f} / {limit:,.0f} TL)")
                        elif yuzde >= 80:
                            st.progress(bar_val)
                            st.warning(f"Dikkat! ({harcanan:,.0f} / {limit:,.0f} TL)")
                        else:
                            st.progress(bar_val)
                            st.caption(f"Güvenli: {harcanan:,.0f} / {limit:,.0f} TL")
        else:
            st.info("Bu ay harcama verisi yok.")

    # --- ABONELİKLER ---
    elif menu == "🔄 Abonelikler":
        st.title("Abonelikler")
        if not df.empty:
            subs = df[df["category"] == "Abonelik - İnternet/Dijital"]
            st.dataframe(subs)
        else:
            st.warning("Yok.")