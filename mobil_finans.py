import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(
    page_title="ONYX V14.1",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TASARIM ---
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

# --- 3. VERİTABANI ---
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

GIDER_KATEGORILERI = ["Abonelik - İnternet/Dijital", "Gıda - Market", "Gıda - Restoran", "Konut - Kira", "Fatura", "Ulaşım", "Kişisel", "Sağlık", "Eğlence", "Eğitim", "Diğer"]
GELIR_KATEGORILERI = ["Maaş", "Ek Gelir", "Yatırım", "Diğer"]

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
    if isinstance(baslangic_tarihi, str): odeme_tarihi = datetime.strptime(baslangic_tarihi, "%Y-%m-%d").date()
    else: odeme_tarihi = baslangic_tarihi.date()
    while odeme_tarihi < bugun: odeme_tarihi += relativedelta(months=1)
    return odeme_tarihi

init_db()
if 'logged_in' not in st.session_state: st.session_state.update({'logged_in': False, 'username': ''})

# ==========================================
# GİRİŞ
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
# ADMIN
# ==========================================
elif st.session_state['username'] == "admin":
    st.sidebar.title("👑 ADMIN")
    if st.sidebar.button("Çıkış"): 
        st.session_state['logged_in']=False
        st.rerun()
    
    admin_menu = st.sidebar.radio("Yönetim", ["📈 Özet", "👥 Kullanıcılar", "👁️ Veri İncele"])
    
    if admin_menu == "📈 Özet":
        st.title("Sistem Özeti")
        users = get_all_users_df()
        st.metric("Toplam Üye", len(users))
        st.dataframe(users, use_container_width=True)
        
    elif admin_menu == "👥 Kullanıcılar":
        st.title("Kullanıcı İşlemleri")
        users = get_all_users_df()
        targets = users[users['username']!='admin']['username'].tolist()
        sel = st.selectbox("Kullanıcı", targets)
        if sel:
            c1, c2 = st.columns(2)
            with c1:
                np = st.text_input("Yeni Şifre")
                if st.button("Şifre Değiştir"):
                    admin_update_password(sel, np)
                    st.success("Değiştirildi")
            with c2:
                st.error("Dikkat!")
                if st.button("KULLANICIYI SİL"):
                    admin_delete_user(sel)
                    st.rerun()
                    
    elif admin_menu == "👁️ Veri İncele":
        st.title("Veri Denetimi")
        users = get_all_users_df()
        targets = users[users['username']!='admin']['username'].tolist()
        sel = st.selectbox("Kullanıcı", targets)
        if sel:
            d = get_user_data(sel)
            if not d.empty:
                inc = d[d['type']=='Gelir']['amount'].sum()
                exp = d[d['type']=='Gider']['amount'].sum()
                st.metric("Net Bakiye", f"{inc-exp:,.2f} ₺")
                st.dataframe(d)

# ==========================================
# KULLANICI
# ==========================================
else:
    user = st.session_state['username']
    df = get_user_data(user)
    
    with st.sidebar:
        st.title(f"👤 {user.upper()}")
        st.caption("Premium Üye")
        st.markdown("---")
        menu = st.radio("MENÜ", ["📊 Dashboard", "📝 İşlem Yönetimi", "📉 Limitler", "🔄 Abonelikler", "🗂️ Raporlar"])
        st.markdown("---")
        # YENİ EKLENEN BUTON
        if st.button("🔄 Verileri Yenile"):
            st.rerun()
        if st.button("Çıkış"):
            st.session_state['logged_in']=False
            st.rerun()

    if menu == "📊 Dashboard":
        st.title("Finansal Özet")
        
        now = datetime.now()
        total_kasa, mo_inc, mo_exp, mo_net = 0.0, 0.0, 0.0, 0.0
        df_mo = pd.DataFrame()

        if not df.empty:
            # Genel Toplam (Tarihten bağımsız)
            total_inc = df[df['type']=='Gelir']['amount'].sum()
            total_exp = df[df['type']=='Gider']['amount'].sum()
            total_kasa = total_inc - total_exp
            
            # Bu Ay Filtresi (Dashboard sorunu buradaydı, şimdi daha sağlam)
            df_mo = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]
            
            if not df_mo.empty:
                mo_inc = df_mo[df_mo['type']=='Gelir']['amount'].sum()
                mo_exp = df_mo[df_mo['type']=='Gider']['amount'].sum()
                mo_net = mo_inc - mo_exp

        # Kartlar
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💎 GENEL TOPLAM", f"{total_kasa:,.2f} ₺", help="Tüm zamanların toplam bakiyesi")
        c2.metric(f"📥 Gelir ({now.strftime('%B')})", f"{mo_inc:,.2f} ₺", help="Sadece bu ay")
        c3.metric(f"📤 Gider ({now.strftime('%B')})", f"{mo_exp:,.2f} ₺", help="Sadece bu ay")
        c4.metric("Aylık Net", f"{mo_net:,.2f} ₺", delta_color="normal" if mo_net>=0 else "inverse")
        
        st.divider()
        
        c_g1, c_g2 = st.columns([2,1])
        with c_g1:
            if not df_mo.empty:
                fig = px.area(df_mo, x="date", y="amount", color="type", color_discrete_map={"Gelir": "#00FFA3", "Gider": "#FF4B4B"}, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Bu ay grafik verisi yok. (Tarih seçiminizi kontrol edin)")
                
        with c_g2:
             if not df_mo.empty and not df_mo[df_mo['type']=='Gider'].empty:
                fig2 = px.pie(df_mo[df_mo['type']=='Gider'], values='amount', names='category', hole=0.5, template="plotly_dark")
                st.plotly_chart(fig2, use_container_width=True)

    elif menu == "📝 İşlem Yönetimi":
        st.title("İşlem Merkezi")
        tab_g, tab_gl, tab_l = st.tabs(["🔴 Gider Ekle", "🟢 Gelir Ekle", "📋 Kayıt Defteri"])
        
        with tab_g:
            with st.form("gider"):
                c1,c2,c3,c4 = st.columns([1,1,1.5,2])
                dd = c1.date_input("Tarih", datetime.now())
                da = c2.number_input("Tutar", min_value=0.0, step=50.0)
                dc = c3.selectbox("Kategori", GIDER_KATEGORILERI)
                de = c4.text_input("Açıklama")
                if st.form_submit_button("Kaydet"):
                    run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', (user, dd, "Gider", dc, da, de))
                    st.success("Tamam"); st.rerun()
        with tab_gl:
            with st.form("gelir"):
                c1,c2,c3,c4 = st.columns([1,1,1.5,2])
                gd = c1.date_input("Tarih", datetime.now(), key="gd")
                ga = c2.number_input("Tutar", min_value=0.0, step=50.0, key="ga")
                gc = c3.selectbox("Kategori", GELIR_KATEGORILERI, key="gc")
                ge = c4.text_input("Açıklama", key="ge")
                if st.form_submit_button("Kaydet"):
                    run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', (user, gd, "Gelir", gc, ga, ge))
                    st.success("Tamam"); st.rerun()
        with tab_l:
            if not df.empty:
                df_edit = df[['id','date','type','category','amount','description']].sort_values('date', ascending=False)
                ch = st.data_editor(df_edit, column_config={"id":None, "date":st.column_config.DateColumn("Tarih", format="DD.MM.YYYY")}, num_rows="dynamic", use_container_width=True, key="edit")
                if st.session_state.get("edit"):
                    s = st.session_state["edit"]
                    if s["edited_rows"] or s["deleted_rows"]:
                        # Basit update/delete mantığı (önceki kodlardaki gibi)
                        for i, r in s["edited_rows"].items():
                            rid = df_edit.iloc[i]['id']
                            for k,v in r.items():
                                if k=='date': v=pd.to_datetime(v).strftime('%Y-%m-%d')
                                run_query(f"UPDATE transactions SET {k}=? WHERE id=?", (v, rid))
                        for i in s["deleted_rows"]:
                            rid = df_edit.iloc[i]['id']
                            run_query("DELETE FROM transactions WHERE id=?", (rid,))
                        st.toast("Güncellendi")

    elif menu == "📉 Limitler":
        st.title("Limitler")
        with st.expander("Limit Ayarla"):
            with st.form("lim"):
                lc = st.selectbox("Kategori", GIDER_KATEGORILERI)
                lv = st.number_input("Limit", step=500.0)
                if st.form_submit_button("Kaydet"):
                    run_query('INSERT OR REPLACE INTO cat_limits VALUES (?,?,?)', (user, lc, lv))
                    st.success("OK"); st.rerun()
        st.divider()
        res = run_query('SELECT category, limit_amount FROM cat_limits WHERE username=?', (user,), fetch=True)
        lims = {r[0]:r[1] for r in res}
        now = datetime.now()
        df_g = df[(df['date'].dt.month==now.month) & (df['type']=='Gider')]
        if lims:
            for c, l in lims.items():
                s = df_g[df_g['category']==c]['amount'].sum()
                p = (s/l)*100 if l>0 else 0
                col = "red" if p>100 else "orange" if p>80 else "green"
                st.write(f"**{c}** ({s:,.0f}/{l:,.0f})")
                st.markdown(f"""<div style="width:100%; background:#333; height:8px; border-radius:4px;"><div style="width:{min(p,100)}%; background:{col}; height:100%; border-radius:4px;"></div></div>""", unsafe_allow_html=True)
        else: st.info("Limit yok.")

    elif menu == "🔄 Abonelikler":
        st.title("Abonelikler")
        df_sub = df[df['category']=="Abonelik - İnternet/Dijital"]
        if not df_sub.empty:
            d = []
            for _, r in df_sub.iterrows():
                nx = sonraki_odeme_bul(r['date'])
                rem = (nx - datetime.now().date()).days
                stt = "✅ Ödendi" if rem>20 else "⏳ Yaklaşıyor"
                d.append({"Hizmet":r['description'], "Tutar":f"{r['amount']} ₺", "Sonraki":nx.strftime("%d.%m.%Y"), "Durum":stt})
            st.dataframe(pd.DataFrame(d), use_container_width=True)
        else: st.warning("Yok.")

    elif menu == "🗂️ Raporlar":
        st.title("Arşiv")
        if not df.empty:
            df['P'] = df['date'].dt.strftime('%Y-%m')
            sel = st.selectbox("Dönem", sorted(df['P'].unique(), reverse=True))
            df_p = df[df['P']==sel]
            i = df_p[df_p['type']=='Gelir']['amount'].sum()
            e = df_p[df_p['type']=='Gider']['amount'].sum()
            st.metric("Net", f"{i-e:,.2f} ₺")
            st.dataframe(df_p)
        else: st.info("Veri yok.")