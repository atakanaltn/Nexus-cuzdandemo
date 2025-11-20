import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(
    page_title="ONYX V13",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TASARIM (GLASSMORPHISM & DARK) ---
st.markdown("""
    <style>
        /* Arka Plan */
        .stApp { 
            background-color: #09090b; 
            background-image: radial-gradient(circle at 50% 0%, #1f1f2e 0%, #09090b 80%);
        }
        /* Kartlar */
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 15px; border-radius: 12px;
        }
        /* Tablar */
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; white-space: pre-wrap; background-color: rgba(255,255,255,0.05);
            border-radius: 5px; color: #fff;
        }
        .stTabs [aria-selected="true"] { background-color: #D4AF37; color: #000; }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
        
        /* Butonlar */
        div.stButton > button {
            background: #111; color: #D4AF37; border: 1px solid #444; width: 100%;
        }
        div.stButton > button:hover { border-color: #D4AF37; color: #FFF; }
    </style>
""", unsafe_allow_html=True)

# --- 3. VERİTABANI ---
DB_FILE = "onyx_v13.db"

def run_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if fetch: return c.fetchall()
        conn.commit()
        return True

def init_db():
    queries = [
        '''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, join_date TEXT)''',
        '''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, type TEXT, category TEXT, amount REAL, description TEXT)''',
        '''CREATE TABLE IF NOT EXISTS cat_limits (username TEXT, category TEXT, limit_amount REAL, PRIMARY KEY (username, category))'''
    ]
    for q in queries: run_query(q)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- KATEGORİLER ---
# Giderler (Detaylı ve Limitlerde Kullanılacak)
GIDER_KATEGORILERI = [
    "Abonelik - İnternet/Dijital", 
    "Gıda - Market", "Gıda - Restoran", 
    "Konut - Kira", "Konut - Aidat", "Fatura - Elektrik/Su/Gaz", "Fatura - Telefon",
    "Ulaşım - Yakıt", "Ulaşım - Toplu Taşıma/Taksi",
    "Kişisel - Giyim", "Kişisel - Bakım", "Sağlık", 
    "Eğlence", "Eğitim", "Borç Ödemesi", "Diğer Gider"
]
# Gelirler (Basit)
GELIR_KATEGORILERI = ["Maaş", "Ek Gelir", "Yatırım", "Borç Alacağı", "Diğer Gelir"]

# --- YARDIMCI FONKSİYONLAR ---
def get_user_data(username):
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM transactions WHERE username = ?", conn, params=(username,))
        conn.close()
        if not df.empty: df["date"] = pd.to_datetime(df["date"])
        return df
    except: return pd.DataFrame()

def sonraki_odeme_bul(baslangic_tarihi):
    bugun = datetime.now().date()
    # Timestamp ise date'e çevir, string ise parse et
    if isinstance(baslangic_tarihi, str):
        odeme_tarihi = datetime.strptime(baslangic_tarihi, "%Y-%m-%d").date()
    else:
        odeme_tarihi = baslangic_tarihi.date()
        
    while odeme_tarihi < bugun:
        odeme_tarihi += relativedelta(months=1)
    return odeme_tarihi

# --- BAŞLANGIÇ ---
init_db()
if 'logged_in' not in st.session_state: st.session_state.update({'logged_in': False, 'username': ''})

# ==========================================
# 1. GİRİŞ EKRANI
# ==========================================
if not st.session_state['logged_in']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color:#D4AF37;'>ONYX PRO</h1>", unsafe_allow_html=True)
        tab_l, tab_s = st.tabs(["Giriş Yap", "Kayıt Ol"])
        with tab_l:
            with st.form("login"):
                u = st.text_input("Kullanıcı Adı")
                p = st.text_input("Şifre", type="password")
                if st.form_submit_button("Giriş"):
                    if u=="admin" and p=="12345":
                        st.session_state.update({'logged_in':True, 'username':'admin'})
                        st.rerun()
                    elif run_query('SELECT * FROM users WHERE username=? AND password=?', (u, make_hashes(p)), fetch=True):
                        st.session_state.update({'logged_in':True, 'username':u})
                        st.rerun()
                    else: st.error("Hatalı bilgi.")
        with tab_s:
            with st.form("signup"):
                nu = st.text_input("Kullanıcı Adı")
                np = st.text_input("Şifre", type="password")
                if st.form_submit_button("Kayıt Ol"):
                    if run_query('INSERT INTO users VALUES (?,?,?)', (nu, make_hashes(np), datetime.now().strftime("%Y-%m-%d"))):
                        st.success("Başarılı! Giriş yapın.")
                    else: st.warning("Kullanıcı adı dolu.")

# ==========================================
# 2. ADMIN
# ==========================================
elif st.session_state['username'] == "admin":
    st.sidebar.title("👑 ADMIN")
    if st.sidebar.button("Çıkış"): 
        st.session_state['logged_in']=False
        st.rerun()
    st.title("Yönetici Paneli")
    conn = sqlite3.connect(DB_FILE)
    users = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    st.dataframe(users)

# ==========================================
# 3. KULLANICI PANELİ
# ==========================================
else:
    user = st.session_state['username']
    df = get_user_data(user)
    
    with st.sidebar:
        st.title(f"👤 {user.upper()}")
        st.markdown("---")
        menu = st.radio("MENÜ", [
            "📊 Dashboard", 
            "📝 İşlem Yönetimi", 
            "📉 Analiz & Limitler", 
            "🔄 Abonelik Takibi", 
            "🗂️ Geçmiş Raporlar"
        ])
        st.markdown("---")
        if st.button("Çıkış"):
            st.session_state['logged_in']=False
            st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Finansal Özet")
        if df.empty:
            st.info("Hoşgeldiniz! İşlem Yönetimi menüsünden ilk kaydınızı girin.")
        else:
            now = datetime.now()
            # Sadece Bu Ay
            df_mo = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]
            
            # Hesaplamalar
            total_kasa = df[df['type']=='Gelir']['amount'].sum() - df[df['type']=='Gider']['amount'].sum()
            mo_inc = df_mo[df_mo['type']=='Gelir']['amount'].sum()
            mo_exp = df_mo[df_mo['type']=='Gider']['amount'].sum()
            mo_net = mo_inc - mo_exp
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💎 TOPLAM KASA", f"{total_kasa:,.2f} ₺")
            c2.metric("📥 Bu Ay Gelir", f"{mo_inc:,.0f} ₺")
            c3.metric("📤 Bu Ay Gider", f"{mo_exp:,.0f} ₺")
            c4.metric("Net Durum", f"{mo_net:,.0f} ₺", delta_color="normal" if mo_net>=0 else "inverse")
            
            st.divider()
            
            col_g1, col_g2 = st.columns([2,1])
            with col_g1:
                if not df_mo.empty:
                    st.subheader("Nakit Akışı")
                    fig = px.area(df_mo, x="date", y="amount", color="type", 
                                  color_discrete_map={"Gelir": "#00FFA3", "Gider": "#FF4B4B"}, template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)
            with col_g2:
                 if not df_mo[df_mo['type']=='Gider'].empty:
                    st.subheader("Harcama Dağılımı")
                    fig2 = px.pie(df_mo[df_mo['type']=='Gider'], values='amount', names='category', hole=0.5, template="plotly_dark")
                    st.plotly_chart(fig2, use_container_width=True)

    # --- İŞLEM YÖNETİMİ (AYRILMIŞ SEKMELER - BUG FREE) ---
    elif menu == "📝 İşlem Yönetimi":
        st.title("İşlem Merkezi")
        
        # BUG ÖNLEMEK İÇİN SEKMELER AYRILDI
        tab_gider, tab_gelir, tab_liste = st.tabs(["🔴 Gider Ekle", "🟢 Gelir Ekle", "📋 Kayıt Defteri (Düzenle/Sil)"])
        
        # 1. GİDER EKLEME TABI
        with tab_gider:
            st.subheader("Harcama Girişi")
            with st.form("gider_form", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([1, 1, 1.5, 2])
                d_date = c1.date_input("Tarih", datetime.now())
                d_amt = c2.number_input("Tutar (TL)", min_value=0.0, step=50.0)
                # SADECE GİDER KATEGORİLERİ
                d_cat = c3.selectbox("Kategori", GIDER_KATEGORILERI)
                d_desc = c4.text_input("Açıklama (Örn: Migros, Kira)")
                
                if st.form_submit_button("Gideri Kaydet 🔴"):
                    run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', 
                              (user, d_date, "Gider", d_cat, d_amt, d_desc))
                    st.success("Gider başarıyla işlendi.")
                    st.rerun()

        # 2. GELİR EKLEME TABI
        with tab_gelir:
            st.subheader("Para Girişi")
            with st.form("gelir_form", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([1, 1, 1.5, 2])
                g_date = c1.date_input("Tarih", datetime.now(), key="g_date")
                g_amt = c2.number_input("Tutar (TL)", min_value=0.0, step=50.0, key="g_amt")
                # SADECE GELİR KATEGORİLERİ
                g_cat = c3.selectbox("Kategori", GELIR_KATEGORILERI, key="g_cat")
                g_desc = c4.text_input("Açıklama (Örn: Maaş, Prim)", key="g_desc")
                
                if st.form_submit_button("Geliri Kaydet 🟢"):
                    run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', 
                              (user, g_date, "Gelir", g_cat, g_amt, g_desc))
                    st.success("Gelir başarıyla işlendi.")
                    st.rerun()

        # 3. DÜZENLEME TABI (DATA EDITOR)
        with tab_liste:
            st.subheader("Tüm Kayıtlar")
            if not df.empty:
                # Düzenlenebilir tablo (Kategori sütununu serbest bıraktık karışmaması için)
                df_edit = df[['id', 'date', 'type', 'category', 'amount', 'description']].sort_values('date', ascending=False)
                
                changes = st.data_editor(
                    df_edit,
                    column_config={
                        "id": None,
                        "date": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                        "type": st.column_config.TextColumn("Tür", disabled=True), # Türü değiştirmeyi kapattık bug olmasın diye
                        "category": st.column_config.SelectboxColumn("Kategori", options=GIDER_KATEGORILERI + GELIR_KATEGORILERI),
                        "amount": st.column_config.NumberColumn("Tutar", format="%.2f ₺"),
                        "description": st.column_config.TextColumn("Açıklama"),
                    },
                    num_rows="dynamic",
                    use_container_width=True,
                    key="main_editor"
                )
                
                # Değişiklikleri Veritabanına Yaz
                if st.session_state.get("main_editor"):
                     state = st.session_state["main_editor"]
                     # Düzenleme
                     for idx, row in state.get("edited_rows", {}).items():
                         rid = df_edit.iloc[idx]['id']
                         for k, v in row.items():
                             if k == 'date': v = pd.to_datetime(v).strftime('%Y-%m-%d')
                             run_query(f"UPDATE transactions SET {k}=? WHERE id=?", (v, rid))
                     # Silme
                     for idx in state.get("deleted_rows", []):
                         rid = df_edit.iloc[idx]['id']
                         run_query("DELETE FROM transactions WHERE id=?", (rid,))
                     
                     if state["edited_rows"] or state["deleted_rows"]:
                         st.toast("Güncellendi!", icon="🔄")

    # --- LİMİTLER (SADECE GİDER) ---
    elif menu == "📉 Analiz & Limitler":
        st.title("Bütçe Limitleri")
        
        with st.expander("⚙️ Limit Belirle", expanded=True):
            with st.form("lim_form"):
                c1, c2 = st.columns(2)
                # Sadece Gider Kategorileri
                l_cat = c1.selectbox("Kategori Seç", GIDER_KATEGORILERI)
                l_val = c2.number_input("Aylık Limit (TL)", step=500.0)
                if st.form_submit_button("Limiti Kaydet"):
                    run_query('INSERT OR REPLACE INTO cat_limits VALUES (?,?,?)', (user, l_cat, l_val))
                    st.success("Limit ayarlandı.")
                    st.rerun()

        st.divider()
        
        # Limit Analizi
        st.subheader("Bu Ayın Durumu")
        res = run_query('SELECT category, limit_amount FROM cat_limits WHERE username=?', (user,), fetch=True)
        limits = {r[0]:r[1] for r in res}
        
        now = datetime.now()
        df_gider = df[(df['date'].dt.month == now.month) & (df['type']=='Gider')]
        
        if limits:
            for cat, lim in limits.items():
                spent = df_gider[df_gider['category']==cat]['amount'].sum()
                pct = (spent/lim)*100 if lim>0 else 0
                
                c_txt, c_bar = st.columns([1, 3])
                with c_txt:
                    st.write(f"**{cat}**")
                    st.caption(f"{spent:,.0f} / {lim:,.0f} TL")
                with c_bar:
                    color = "red" if pct > 100 else "orange" if pct > 80 else "green"
                    st.markdown(f"""<div style="width:100%; background:#333; height:10px; border-radius:5px;">
                                    <div style="width:{min(pct,100)}%; background:{color}; height:100%; border-radius:5px;"></div></div>""", unsafe_allow_html=True)
                    if pct>100: st.caption("⚠️ LİMİT AŞILDI!")
        else:
            st.info("Henüz limit belirlemediniz.")

    # --- ABONELİKLER (GERİ GELDİ) ---
    elif menu == "🔄 Abonelik Takibi":
        st.title("Abonelik Yönetimi")
        st.info("Kategorisi 'Abonelik - İnternet/Dijital' olan harcamalar burada listelenir.")
        
        df_subs = df[df['category'] == "Abonelik - İnternet/Dijital"].copy()
        
        if not df_subs.empty:
            subs_data = []
            for _, row in df_subs.iterrows():
                next_date = sonraki_odeme_bul(row['date'])
                days_left = (next_date - datetime.now().date()).days
                status = "✅ Ödendi" if days_left > 20 else "⏳ Yaklaşıyor"
                if days_left < 3: status = "🚨 Çok Yakın"
                
                subs_data.append({
                    "Hizmet": row['description'] if row['description'] else "İsimsiz",
                    "Tutar": f"{row['amount']} ₺",
                    "Sonraki Ödeme": next_date.strftime("%d.%m.%Y"),
                    "Kalan Gün": f"{days_left} Gün",
                    "Durum": status
                })
            st.dataframe(pd.DataFrame(subs_data), use_container_width=True)
            
            total_sub = df_subs['amount'].sum()
            st.metric("Aylık Sabit Gider", f"{total_sub:,.2f} ₺")
        else:
            st.warning("Abonelik bulunamadı. Gider eklerken 'Abonelik - İnternet/Dijital' seçin.")

    # --- GEÇMİŞ RAPORLAR (GERİ GELDİ) ---
    elif menu == "🗂️ Geçmiş Raporlar":
        st.title("Geçmiş Dönem Arşivi")
        
        if not df.empty:
            df['Period'] = df['date'].dt.strftime('%Y-%m')
            periods = sorted(df['Period'].unique(), reverse=True)
            
            selected_p = st.selectbox("Dönem Seçin", periods)
            
            df_p = df[df['Period'] == selected_p]
            inc = df_p[df_p['type']=='Gelir']['amount'].sum()
            exp = df_p[df_p['type']=='Gider']['amount'].sum()
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Gelir", f"{inc:,.2f} ₺")
            k2.metric("Gider", f"{exp:,.2f} ₺")
            k3.metric("Net", f"{inc-exp:,.2f} ₺")
            
            st.dataframe(df_p.sort_values('date'), use_container_width=True)
        else:
            st.info("Veri yok.")