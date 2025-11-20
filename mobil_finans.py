import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime

# --- 1. SİSTEM VE SAYFA AYARLARI ---
st.set_page_config(
    page_title="ONYX Hyper-Fluid",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. MODERN CSS (GLASSMORPHISM & NEON) ---
st.markdown("""
    <style>
        /* Ana Arka Plan (Derin Uzay Siyahı) */
        .stApp { 
            background-color: #09090b; 
            background-image: radial-gradient(circle at 50% 0%, #1f1f2e 0%, #09090b 70%);
        }
        
        /* Kartlar (Glassmorphism) */
        div[data-testid="stMetric"], div.css-1r6slb0 {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            border-color: #D4AF37;
        }
        
        /* Başlıklar ve Fontlar */
        h1, h2, h3 { color: #ffffff !important; font-family: 'Inter', sans-serif; font-weight: 600; letter-spacing: -0.5px; }
        p, div { color: #e0e0e0; font-family: 'Inter', sans-serif; }
        
        /* Tablo Tasarımı */
        div[data-testid="stDataFrame"] {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 12px;
            padding: 10px;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { 
            background-color: #050505; 
            border-right: 1px solid #222; 
        }
        
        /* Özel Butonlar */
        div.stButton > button {
            background: linear-gradient(45deg, #111, #222);
            color: #D4AF37;
            border: 1px solid #444;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background: linear-gradient(45deg, #D4AF37, #F1C40F);
            color: #000;
            border-color: #D4AF37;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. VERİTABANI (HATA KORUMALI) ---
DB_FILE = "onyx_v12.db"

def run_query(query, params=(), fetch=False):
    """Veritabanı işlemlerini güvenli hale getiren sarmalayıcı"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute(query, params)
            if fetch:
                return c.fetchall()
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Veritabanı Hatası: {e}")
        return False

def init_db():
    queries = [
        '''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, join_date TEXT)''',
        '''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, type TEXT, category TEXT, amount REAL, description TEXT)''',
        '''CREATE TABLE IF NOT EXISTS limits (username TEXT PRIMARY KEY, monthly_limit REAL)''',
        '''CREATE TABLE IF NOT EXISTS cat_limits (username TEXT, category TEXT, limit_amount REAL, PRIMARY KEY (username, category))'''
    ]
    for q in queries:
        run_query(q)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- KATEGORİLER ---
GIDER_KATEGORILERI = ["Abonelik - İnternet/Dijital", "Gıda - Market", "Gıda - Restoran", "Konut - Kira", "Fatura", "Ulaşım", "Kişisel", "Eğlence", "Eğitim", "Diğer"]
GELIR_KATEGORILERI = ["Maaş", "Ek Gelir", "Yatırım", "Diğer"]

# --- FONKSİYONLAR ---
def get_user_data(username):
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM transactions WHERE username = ?", conn, params=(username,))
        conn.close()
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except:
        return pd.DataFrame()

def get_greeting():
    hour = datetime.now().hour
    if hour < 12: return "Günaydın ☀️"
    elif hour < 18: return "İyi Günler 🌤️"
    else: return "İyi Akşamlar 🌙"

# --- BAŞLANGIÇ ---
init_db()

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'username': ''})

# ==========================================
# 1. GİRİŞ EKRANI (CENTERED & CLEAN)
# ==========================================
if not st.session_state['logged_in']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #D4AF37 !important;'>ONYX PRO</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Yeni Nesil Varlık Yönetimi</p>", unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["Giriş Yap", "Kayıt Ol"])
        
        with tab_login:
            with st.form("login_form"):
                user = st.text_input("Kullanıcı Adı")
                pw = st.text_input("Şifre", type="password")
                if st.form_submit_button("Giriş Yap", use_container_width=True):
                    if user == "admin" and pw == "12345":
                        st.session_state.update({'logged_in': True, 'username': 'admin'})
                        st.rerun()
                    else:
                        res = run_query('SELECT * FROM users WHERE username =? AND password = ?', (user, make_hashes(pw)), fetch=True)
                        if res:
                            st.session_state.update({'logged_in': True, 'username': user})
                            st.rerun()
                        else:
                            st.error("Hatalı bilgiler.")

        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Yeni Kullanıcı Adı")
                new_pw = st.text_input("Yeni Şifre", type="password")
                if st.form_submit_button("Hesap Oluştur", use_container_width=True):
                    success = run_query('INSERT INTO users(username, password, join_date) VALUES (?,?,?)', 
                                      (new_user, make_hashes(new_pw), datetime.now().strftime("%Y-%m-%d")))
                    if success:
                        st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
                    else:
                        st.warning("Kullanıcı adı alınmış.")

# ==========================================
# 2. ADMIN PANELİ
# ==========================================
elif st.session_state['username'] == "admin":
    st.sidebar.title("👑 ADMIN")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state['logged_in'] = False
        st.rerun()
    
    st.title("Sistem Paneli")
    conn = sqlite3.connect(DB_FILE)
    users = pd.read_sql_query("SELECT username, join_date FROM users", conn)
    conn.close()
    
    c1, c2 = st.columns(2)
    c1.metric("Toplam Kullanıcı", len(users))
    c2.metric("Aktif Veritabanı", "Onyx V12")
    
    st.subheader("Kullanıcı Listesi")
    st.dataframe(users, use_container_width=True)
    
    selected = st.selectbox("Kullanıcı İncele", users[users['username']!='admin']['username'].tolist())
    if selected:
        df = get_user_data(selected)
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("Veri yok.")

# ==========================================
# 3. KULLANICI ARAYÜZÜ (FLUID DESIGN)
# ==========================================
else:
    user = st.session_state['username']
    df = get_user_data(user)
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 👤 {user.upper()}")
        st.caption("Premium Üye")
        st.markdown("---")
        menu = st.radio("Navigasyon", ["📊 Dashboard", "💎 İşlemler (Canlı)", "📉 Limitler & Analiz"])
        st.markdown("---")
        if st.button("Güvenli Çıkış"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        # 1. HERO SECTION (Karşılama)
        greeting = get_greeting()
        st.markdown(f"## {greeting}, **{user}**")
        
        if df.empty:
            st.info("Henüz bir finansal hareketiniz yok. 'İşlemler' menüsünden ilk kaydınızı oluşturun.")
        else:
            # Hesaplamalar
            now = datetime.now()
            df_mo = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]
            
            total_assets = df[df['type']=='Gelir']['amount'].sum() - df[df['type']=='Gider']['amount'].sum()
            mo_inc = df_mo[df_mo['type']=='Gelir']['amount'].sum()
            mo_exp = df_mo[df_mo['type']=='Gider']['amount'].sum()
            mo_net = mo_inc - mo_exp
            
            # Hero Card
            hero_col, kpi_col = st.columns([1.5, 2.5])
            with hero_col:
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #D4AF37, #F1C40F); padding: 20px; border-radius: 15px; color: black; box-shadow: 0 10px 20px rgba(212, 175, 55, 0.3);">
                        <h4 style="margin:0; color:black !important;">Toplam Varlık</h4>
                        <h1 style="margin:0; font-size: 3rem; color:black !important;">₺{total_assets:,.2f}</h1>
                        <p style="margin:5px 0 0 0; opacity: 0.8;">Finansal Özgürlük Puanı: {'Yüksek' if total_assets > 10000 else 'Gelişiyor'}</p>
                    </div>
                    """, unsafe_allow_html=True
                )
            
            with kpi_col:
                k1, k2, k3 = st.columns(3)
                k1.metric("📥 Bu Ay Gelir", f"{mo_inc:,.0f} ₺")
                k2.metric("📤 Bu Ay Gider", f"{mo_exp:,.0f} ₺")
                k3.metric("📈 Bu Ay Net", f"{mo_net:,.0f} ₺", delta_color="normal" if mo_net >= 0 else "inverse")
            
            st.markdown("---")
            
            # Charts (Fluid Layout)
            c_chart1, c_chart2 = st.columns([2, 1])
            with c_chart1:
                st.subheader("Nakit Akışı")
                if not df_mo.empty:
                    fig = px.area(df_mo, x="date", y="amount", color="type", 
                                  color_discrete_map={"Gelir": "#00FFA3", "Gider": "#FF4B4B"}, 
                                  template="plotly_dark")
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0,r=0,t=0,b=0), height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption("Bu ay grafik verisi yok.")
            
            with c_chart2:
                st.subheader("Harcama Pasta")
                df_gider = df_mo[df_mo['type']=='Gider']
                if not df_gider.empty:
                    fig2 = px.pie(df_gider, values='amount', names='category', hole=0.6, template="plotly_dark", color_discrete_sequence=px.colors.sequential.RdBu)
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0,r=0,t=0,b=0), height=300, showlegend=False)
                    fig2.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.caption("Harcama yok.")

    # --- İŞLEMLER (CANLI EDİTÖR) ---
    elif menu == "💎 İşlemler (Canlı)":
        st.title("İşlem Yönetimi")
        
        # 1. Hızlı Ekleme Paneli (Üstte, temiz)
        with st.expander("➕ Yeni İşlem Ekle", expanded=True):
            with st.form("quick_add", clear_on_submit=True):
                c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1.5, 2])
                t_type = c1.selectbox("Tür", ["Gider", "Gelir"])
                t_date = c2.date_input("Tarih", datetime.now())
                t_amt = c3.number_input("Tutar", min_value=0.0, step=50.0)
                t_cat = c4.selectbox("Kategori", GIDER_KATEGORILERI if t_type == "Gider" else GELIR_KATEGORILERI)
                t_desc = c5.text_input("Açıklama")
                
                if st.form_submit_button("Kaydet 💾"):
                    run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', 
                              (user, t_date, t_type, t_cat, t_amt, t_desc))
                    st.success("İşlem eklendi.")
                    st.rerun()

        st.divider()
        
        # 2. Canlı Düzenlenebilir Tablo (Altın Özellik)
        st.subheader("📋 İşlem Geçmişi (Düzenlenebilir)")
        st.caption("Tablodaki verilere çift tıklayarak düzenleyebilir, satırı seçip silebilirsiniz.")
        
        if not df.empty:
            df_display = df[['id', 'date', 'type', 'category', 'amount', 'description']].sort_values('date', ascending=False)
            
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "id": None, # ID'yi gizle
                    "date": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                    "type": st.column_config.SelectboxColumn("Tür", options=["Gelir", "Gider"], required=True),
                    "category": st.column_config.SelectboxColumn("Kategori", options=GIDER_KATEGORILERI + GELIR_KATEGORILERI, required=True),
                    "amount": st.column_config.NumberColumn("Tutar (TL)", format="%.2f ₺"),
                    "description": st.column_config.TextColumn("Açıklama"),
                },
                num_rows="dynamic", # Silme ve ekleme aktif
                use_container_width=True,
                key="editor"
            )
            
            # Değişiklikleri Algıla ve Veritabanına Yaz (Gelişmiş Senkronizasyon)
            if st.session_state.get("editor"):
                changes = st.session_state["editor"]
                
                # A. Düzenlenenler
                for idx, updates in changes.get("edited_rows", {}).items():
                    row_id = df_display.iloc[idx]["id"]
                    for col, val in updates.items():
                        # Tarih düzeltmesi (datetime objesini string'e çevir)
                        if col == "date": val = pd.to_datetime(val).strftime("%Y-%m-%d")
                        run_query(f"UPDATE transactions SET {col} = ? WHERE id = ?", (val, row_id))
                
                # B. Silinenler
                for idx in changes.get("deleted_rows", []):
                    row_id = df_display.iloc[idx]["id"]
                    run_query("DELETE FROM transactions WHERE id = ?", (row_id,))
                
                # C. Eklenenler
                for row in changes.get("added_rows", []):
                    # Eklenen satırların boş olmamasını kontrol et
                    if row.get("amount") and row.get("type"):
                         d = row.get("date", datetime.now().strftime("%Y-%m-%d"))
                         run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)',
                                  (user, d, row.get("type"), row.get("category", "Diğer"), row.get("amount"), row.get("description", "")))

                # Eğer değişiklik varsa sayfayı yenile (ki tablo güncellensin)
                if changes["edited_rows"] or changes["deleted_rows"] or changes["added_rows"]:
                     st.toast("Veritabanı güncellendi!", icon="🔄")
                     # Manuel rerun gerekebilir, ancak data_editor bazen kendi halleder.
                     # st.rerun() 

    # --- LİMİTLER ---
    elif menu == "📉 Limitler & Analiz":
        st.title("Bütçe Kontrolü")
        
        # Limit Ayarları
        with st.expander("⚙️ Limit Ayarları"):
            res = run_query("SELECT category, limit_amount FROM cat_limits WHERE username = ?", (user,), fetch=True)
            user_limits = {row[0]: row[1] for row in res} if res else {}
            
            with st.form("limit_set"):
                c1, c2 = st.columns(2)
                l_cat = c1.selectbox("Kategori", GIDER_KATEGORILERI)
                l_val = c2.number_input("Limit (TL)", min_value=0.0, step=500.0)
                if st.form_submit_button("Limiti Kaydet"):
                    run_query('INSERT OR REPLACE INTO cat_limits (username, category, limit_amount) VALUES (?, ?, ?)', (user, l_cat, l_val))
                    st.success("Limit ayarlandı.")
                    st.rerun()
        
        st.divider()
        
        # Analiz Barları
        st.subheader("Bu Ayın Durumu")
        if not df.empty:
            now = datetime.now()
            df_gider = df[(df['date'].dt.month == now.month) & (df['type']=='Gider')]
            
            if not user_limits:
                st.info("Henüz limit belirlemediniz.")
            
            for cat, limit in user_limits.items():
                spent = df_gider[df_gider['category']==cat]['amount'].sum()
                pct = (spent / limit) * 100 if limit > 0 else 0
                
                st.write(f"**{cat}**")
                c_bar, c_txt = st.columns([4, 1])
                
                color = "green"
                if pct > 100: color = "red"
                elif pct > 80: color = "orange"
                
                # Özel HTML Progress Bar (Daha estetik)
                c_bar.markdown(f"""
                    <div style="width:100%; background-color: #333; border-radius: 10px; height: 20px;">
                        <div style="width: {min(pct, 100)}%; background-color: {color}; height: 100%; border-radius: 10px; transition: width 0.5s;"></div>
                    </div>
                """, unsafe_allow_html=True)
                c_txt.caption(f"{spent:,.0f} / {limit:,.0f} TL")
                if pct > 100: st.caption(f"⚠️ {spent-limit:,.0f} TL Aşıldı!")
                st.write("") # Boşluk
        else:
            st.warning("Veri yok.")