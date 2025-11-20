import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(
    page_title="ONYX V14 Admin",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TASARIM (ONYX DARK THEME) ---
st.markdown("""
    <style>
        .stApp { 
            background-color: #09090b; 
            background-image: radial-gradient(circle at 50% 0%, #1f1f2e 0%, #09090b 80%);
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 15px; border-radius: 12px;
        }
        section[data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #222; }
        div.stButton > button {
            background: #111; color: #D4AF37; border: 1px solid #444; width: 100%;
        }
        div.stButton > button:hover { border-color: #D4AF37; color: #FFF; }
        .stTabs [aria-selected="true"] { background-color: #D4AF37; color: #000; }
    </style>
""", unsafe_allow_html=True)

# --- 3. VERİTABANI YÖNETİMİ ---
DB_FILE = "onyx_v14.db"

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
GIDER_KATEGORILERI = [
    "Abonelik - İnternet/Dijital", "Gıda - Market", "Gıda - Restoran", 
    "Konut - Kira", "Konut - Aidat", "Fatura - Elektrik/Su/Gaz", "Fatura - Telefon",
    "Ulaşım - Yakıt", "Ulaşım - Toplu Taşıma", "Kişisel - Giyim", "Kişisel - Bakım", 
    "Sağlık", "Eğlence", "Eğitim", "Borç Ödemesi", "Diğer Gider"
]
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

def get_all_users_df():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT username, join_date FROM users", conn)
    conn.close()
    return df

def admin_update_password(username, new_password):
    return run_query("UPDATE users SET password = ? WHERE username = ?", (make_hashes(new_password), username))

def admin_delete_user(username):
    run_query("DELETE FROM users WHERE username = ?", (username,))
    run_query("DELETE FROM transactions WHERE username = ?", (username,))
    run_query("DELETE FROM cat_limits WHERE username = ?", (username,))
    return True

def sonraki_odeme_bul(baslangic_tarihi):
    bugun = datetime.now().date()
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
                        st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
                    else: st.warning("Bu kullanıcı adı zaten var.")

# ==========================================
# 2. YÖNETİCİ PANELİ (GELİŞMİŞ)
# ==========================================
elif st.session_state['username'] == "admin":
    st.sidebar.title("👑 ADMIN PANEL")
    st.sidebar.info("Tam Yetkili Erişim")
    if st.sidebar.button("Çıkış Yap"): 
        st.session_state['logged_in']=False
        st.rerun()
    
    # Admin Menüsü
    admin_menu = st.sidebar.radio("Yönetim", ["📈 Genel İstatistikler", "👥 Kullanıcı Yönetimi (Şifre/Sil)", "👁️ Veri Denetimi"])
    
    if admin_menu == "📈 Genel İstatistikler":
        st.title("Sistem Özeti")
        users_df = get_all_users_df()
        total_users = len(users_df)
        
        # Sistemdeki Toplam Para Hareketi
        conn = sqlite3.connect(DB_FILE)
        total_tx_vol = pd.read_sql_query("SELECT SUM(amount) FROM transactions", conn).iloc[0,0]
        conn.close()
        if total_tx_vol is None: total_tx_vol = 0
        
        c1, c2 = st.columns(2)
        c1.metric("Toplam Üye", total_users)
        c2.metric("Sistemdeki İşlem Hacmi", f"{total_tx_vol:,.2f} ₺")
        
        st.subheader("Kayıtlı Üyeler")
        st.dataframe(users_df, use_container_width=True)

    elif admin_menu == "👥 Kullanıcı Yönetimi (Şifre/Sil)":
        st.title("Kullanıcı İşlemleri")
        users_df = get_all_users_df()
        user_list = users_df[users_df['username'] != 'admin']['username'].tolist()
        
        target_user = st.selectbox("İşlem Yapılacak Kullanıcı:", user_list)
        
        if target_user:
            st.divider()
            c_pass, c_del = st.columns(2)
            
            # Şifre Sıfırlama
            with c_pass:
                st.subheader("🔒 Şifre Değiştir")
                st.info(f"**{target_user}** için yeni şifre belirle.")
                new_admin_pass = st.text_input("Yeni Şifre", key="new_pass")
                if st.button("Şifreyi Güncelle"):
                    if new_admin_pass:
                        admin_update_password(target_user, new_admin_pass)
                        st.success(f"{target_user} kullanıcısının şifresi değiştirildi.")
                    else:
                        st.warning("Şifre boş olamaz.")
            
            # Kullanıcı Silme
            with c_del:
                st.subheader("🚨 Kullanıcıyı Sil")
                st.error("Bu işlem geri alınamaz! Tüm verileri silinir.")
                if st.button("KULLANICIYI SİL"):
                    admin_delete_user(target_user)
                    st.success(f"{target_user} sistemden silindi.")
                    st.rerun()

    elif admin_menu == "👁️ Veri Denetimi":
        st.title("Kullanıcı Verilerini İncele")
        users_df = get_all_users_df()
        user_list = users_df[users_df['username'] != 'admin']['username'].tolist()
        target_user = st.selectbox("Kullanıcı Seç:", user_list)
        
        if target_user:
            df = get_user_data(target_user)
            if not df.empty:
                gelir = df[df['type']=='Gelir']['amount'].sum()
                gider = df[df['type']=='Gider']['amount'].sum()
                st.metric(f"{target_user} Net Varlık", f"{gelir-gider:,.2f} ₺")
                st.dataframe(df.sort_values('date', ascending=False), use_container_width=True)
            else:
                st.info("Bu kullanıcının verisi yok.")

# ==========================================
# 3. KULLANICI PANELİ (BUG FIXED DASHBOARD)
# ==========================================
else:
    user = st.session_state['username']
    df = get_user_data(user)
    
    with st.sidebar:
        st.title(f"👤 {user.upper()}")
        st.caption("Premium Üye")
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
        
        # BUG FIX: Eğer df boşsa veya o ay veri yoksa çökmemesi için kontroller
        now = datetime.now()
        
        total_kasa = 0.0
        mo_inc = 0.0
        mo_exp = 0.0
        mo_net = 0.0
        df_mo = pd.DataFrame() # Boş dataframe başlat

        if not df.empty:
            # Genel Toplam
            total_inc = df[df['type']=='Gelir']['amount'].sum()
            total_exp = df[df['type']=='Gider']['amount'].sum()
            total_kasa = total_inc - total_exp
            
            # Bu Ay
            df_mo = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]
            if not df_mo.empty:
                mo_inc = df_mo[df_mo['type']=='Gelir']['amount'].sum()
                mo_exp = df_mo[df_mo['type']=='Gider']['amount'].sum()
                mo_net = mo_inc - mo_exp

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💎 TOPLAM KASA", f"{total_kasa:,.2f} ₺")
        c2.metric("📥 Bu Ay Gelir", f"{mo_inc:,.2f} ₺")
        c3.metric("📤 Bu Ay Gider", f"{mo_exp:,.2f} ₺")
        c4.metric("Net Durum", f"{mo_net:,.2f} ₺", delta_color="normal" if mo_net>=0 else "inverse")
        
        st.divider()
        
        col_g1, col_g2 = st.columns([2,1])
        with col_g1:
            if not df_mo.empty:
                st.subheader("Nakit Akışı")
                fig = px.area(df_mo, x="date", y="amount", color="type", 
                              color_discrete_map={"Gelir": "#00FFA3", "Gider": "#FF4B4B"}, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Bu ay grafik için henüz veri yok.")
                
        with col_g2:
             if not df_mo.empty and not df_mo[df_mo['type']=='Gider'].empty:
                st.subheader("Harcama Dağılımı")
                fig2 = px.pie(df_mo[df_mo['type']=='Gider'], values='amount', names='category', hole=0.5, template="plotly_dark")
                st.plotly_chart(fig2, use_container_width=True)

    # --- İŞLEM YÖNETİMİ ---
    elif menu == "📝 İşlem Yönetimi":
        st.title("İşlem Merkezi")
        tab_gider, tab_gelir, tab_liste = st.tabs(["🔴 Gider Ekle", "🟢 Gelir Ekle", "📋 Kayıt Defteri"])
        
        with tab_gider:
            with st.form("gider_form", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([1, 1, 1.5, 2])
                d_date = c1.date_input("Tarih", datetime.now())
                d_amt = c2.number_input("Tutar", min_value=0.0, step=50.0)
                d_cat = c3.selectbox("Kategori", GIDER_KATEGORILERI)
                d_desc = c4.text_input("Açıklama")
                if st.form_submit_button("Gider Kaydet"):
                    run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', (user, d_date, "Gider", d_cat, d_amt, d_desc))
                    st.success("Kaydedildi")
                    st.rerun()

        with tab_gelir:
            with st.form("gelir_form", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([1, 1, 1.5, 2])
                g_date = c1.date_input("Tarih", datetime.now(), key="g_date")
                g_amt = c2.number_input("Tutar", min_value=0.0, step=50.0, key="g_amt")
                g_cat = c3.selectbox("Kategori", GELIR_KATEGORILERI, key="g_cat")
                g_desc = c4.text_input("Açıklama", key="g_desc")
                if st.form_submit_button("Gelir Kaydet"):
                    run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', (user, g_date, "Gelir", g_cat, g_amt, g_desc))
                    st.success("Kaydedildi")
                    st.rerun()

        with tab_liste:
            st.subheader("Tüm Kayıtlar")
            if not df.empty:
                df_edit = df[['id', 'date', 'type', 'category', 'amount', 'description']].sort_values('date', ascending=False)
                changes = st.data_editor(df_edit, column_config={"id":None, "type":st.column_config.TextColumn(disabled=True), "date": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY")}, num_rows="dynamic", use_container_width=True, key="main_editor")
                
                if st.session_state.get("main_editor"):
                     state = st.session_state["main_editor"]
                     for idx, row in state.get("edited_rows", {}).items():
                         rid = df_edit.iloc[idx]['id']
                         for k, v in row.items():
                             if k=='date': v=pd.to_datetime(v).strftime('%Y-%m-%d')
                             run_query(f"UPDATE transactions SET {k}=? WHERE id=?", (v, rid))
                     for idx in state.get("deleted_rows", []):
                         rid = df_edit.iloc[idx]['id']
                         run_query("DELETE FROM transactions WHERE id=?", (rid,))
                     if state["edited_rows"] or state["deleted_rows"]: st.toast("Güncellendi!");

    # --- LİMİTLER ---
    elif menu == "📉 Analiz & Limitler":
        st.title("Bütçe Limitleri")
        with st.expander("⚙️ Limit Belirle", expanded=True):
            with st.form("lim_form"):
                c1, c2 = st.columns(2)
                l_cat = c1.selectbox("Kategori", GIDER_KATEGORILERI)
                l_val = c2.number_input("Limit (TL)", step=500.0)
                if st.form_submit_button("Kaydet"):
                    run_query('INSERT OR REPLACE INTO cat_limits VALUES (?,?,?)', (user, l_cat, l_val))
                    st.success("Ayarlandı.")
                    st.rerun()
        st.divider()
        st.subheader("Bu Ayın Durumu")
        res = run_query('SELECT category, limit_amount FROM cat_limits WHERE username=?', (user,), fetch=True)
        limits = {r[0]:r[1] for r in res}
        now = datetime.now()
        df_gider = pd.DataFrame()
        if not df.empty: df_gider = df[(df['date'].dt.month == now.month) & (df['type']=='Gider')]
        
        if limits:
            for cat, lim in limits.items():
                spent = 0
                if not df_gider.empty: spent = df_gider[df_gider['category']==cat]['amount'].sum()
                pct = (spent/lim)*100 if lim>0 else 0
                c_txt, c_bar = st.columns([1, 3])
                with c_txt: st.write(f"**{cat}**"); st.caption(f"{spent:,.0f} / {lim:,.0f} TL")
                with c_bar:
                    color = "red" if pct > 100 else "orange" if pct > 80 else "green"
                    st.markdown(f"""<div style="width:100%; background:#333; height:10px; border-radius:5px;"><div style="width:{min(pct,100)}%; background:{color}; height:100%; border-radius:5px;"></div></div>""", unsafe_allow_html=True)
        else: st.info("Limit yok.")

    # --- ABONELİKLER ---
    elif menu == "🔄 Abonelik Takibi":
        st.title("Abonelik Yönetimi")
        df_subs = pd.DataFrame()
        if not df.empty: df_subs = df[df['category'] == "Abonelik - İnternet/Dijital"].copy()
        
        if not df_subs.empty:
            subs_data = []
            for _, row in df_subs.iterrows():
                next_date = sonraki_odeme_bul(row['date'])
                days_left = (next_date - datetime.now().date()).days
                status = "✅ Ödendi" if days_left > 20 else "⏳ Yaklaşıyor"
                subs_data.append({"Hizmet": row['description'], "Tutar": f"{row['amount']} ₺", "Sonraki Ödeme": next_date.strftime("%d.%m.%Y"), "Durum": status})
            st.dataframe(pd.DataFrame(subs_data), use_container_width=True)
        else: st.warning("Abonelik yok.")

    # --- RAPORLAR ---
    elif menu == "🗂️ Geçmiş Raporlar":
        st.title("Geçmiş Raporlar")
        if not df.empty:
            df['Period'] = df['date'].dt.strftime('%Y-%m')
            selected_p = st.selectbox("Dönem", sorted(df['Period'].unique(), reverse=True))
            df_p = df[df['Period'] == selected_p]
            inc = df_p[df_p['type']=='Gelir']['amount'].sum()
            exp = df_p[df_p['type']=='Gider']['amount'].sum()
            st.metric("Net", f"{inc-exp:,.2f} ₺")
            st.dataframe(df_p.sort_values('date'), use_container_width=True)
        else: st.info("Veri yok.")