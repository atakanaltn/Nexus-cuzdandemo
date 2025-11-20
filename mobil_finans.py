import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import hashlib
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(
    page_title="OmnyxWallet V25.1",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TASARIM (SOFT OBSIDIAN DARK) ---
st.markdown("""
    <style>
        /* Ana Arka Plan */
        .stApp { 
            background-color: #0E0E12; 
            background-image: radial-gradient(circle at 50% 0%, #1F1F26 0%, #0E0E12 90%);
            color: #E0E0E0;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { 
            background-color: #09090B; 
            border-right: 1px solid #27272A; 
        }
        
        /* Premium Kartlar */
        div[data-testid="stMetric"] {
            background: rgba(30, 30, 35, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 15px;
            border-radius: 16px;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        div[data-testid="stMetricLabel"] { color: #A1A1AA !important; font-size: 0.85rem !important; }
        div[data-testid="stMetricValue"] { color: #EDEDED !important; }
        
        /* Tablolar */
        div[data-testid="stDataFrame"] { 
            background-color: rgba(20, 20, 25, 0.5); 
            border: 1px solid #333; 
            border-radius: 12px; 
        }
        
        /* Butonlar */
        div.stButton > button {
            width: 100%;
            background: linear-gradient(135deg, #18181B, #27272A);
            color: #D4AF37;
            border: 1px solid #3F3F46;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            border-color: #D4AF37; color: #FFF;
            background: linear-gradient(135deg, #D4AF37, #F59E0B);
            color: #000;
        }
        
        /* Inputlar */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input {
            background-color: #18181B !important; 
            color: #FAFAFA !important; 
            border: 1px solid #3F3F46 !important;
            border-radius: 8px;
        }
        
        h1, h2, h3, h4 { color: #D4AF37 !important; font-family: 'Segoe UI', sans-serif; font-weight: 400; }
        
        /* Tab Seçimi */
        .stTabs [aria-selected="true"] { background-color: #D4AF37; color: #000; border-radius: 5px;}
        .stTabs [data-baseweb="tab"] { color: #A1A1AA; }
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

# --- AI MANTIĞI ---
def generate_ai_advice(df, user_limits):
    advice, status = [], "neutral"
    if df.empty or not user_limits: return ["Veri bekleniyor..."], "neutral"
    now = datetime.now()
    df_mo = df[(df['date'].dt.month == now.month) & (df['type'] == 'Gider')]
    total_spent = df_mo['amount'].sum()
    total_limit = sum(user_limits.values())
    if total_limit > 0:
        pct = (total_spent / total_limit) * 100
        if pct > 100: advice.append(f"🚨 **Kritik:** Bütçeyi aştın! ({total_spent - total_limit:.0f} TL Fazla)"); status = "critical"
        elif pct > 80: advice.append(f"⚠️ **Uyarı:** Limitlerin %{pct:.0f}'ine ulaştın."); status = "warning"
        else: advice.append("✅ **İyi Gidiyorsun:** Bütçe kontrol altında."); status = "good"
    return advice, status

init_db()
if 'logged_in' not in st.session_state: st.session_state.update({'logged_in': False, 'username': ''})

# 1. GİRİŞ
if not st.session_state['logged_in']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""<h1 style='text-align: center; font-family: "SF Pro Display", sans-serif; font-weight: 900; letter-spacing: 2px; background: linear-gradient(to right, #D4AF37, #FFE680); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>OmnyxWallet</h1>""", unsafe_allow_html=True)
        tab_l, tab_s = st.tabs(["Giriş", "Kayıt"])
        with tab_l:
            with st.form("login"):
                u = st.text_input("Kullanıcı Adı")
                p = st.text_input("Şifre", type="password")
                if st.form_submit_button("Giriş"):
                    if u=="admin" and p=="12345": st.session_state.update({'logged_in':True, 'username':'admin'}); st.rerun()
                    elif run_query('SELECT * FROM users WHERE username=? AND password=?', (u, make_hashes(p)), fetch=True): st.session_state.update({'logged_in':True, 'username':u}); st.rerun()
                    else: st.error("Hatalı bilgi.")
        with tab_s:
            with st.form("signup"):
                nu = st.text_input("Kullanıcı Adı")
                np = st.text_input("Şifre", type="password")
                if st.form_submit_button("Kayıt"):
                    if run_query('INSERT INTO users VALUES (?,?,?)', (nu, make_hashes(np), datetime.now().strftime("%Y-%m-%d"))): st.success("Başarılı."); 
                    else: st.warning("Kullanıcı adı dolu.")

# 2. ADMIN
elif st.session_state['username'] == "admin":
    st.sidebar.title("👑 ADMIN PANEL")
    if st.sidebar.button("Çıkış"): st.session_state['logged_in']=False; st.rerun()
    
    st.title("Sistem Yönetimi")
    
    tab1, tab2 = st.tabs(["📈 Genel Bakış", "👥 Kullanıcı Yönetimi"])
    
    with tab1:
        users = get_all_users_df()
        st.metric("Toplam Kayıtlı Üye", len(users))
        st.dataframe(users, use_container_width=True)
        
    with tab2:
        users = get_all_users_df()
        targets = users[users['username']!='admin']['username'].tolist()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Kullanıcı Seç")
            target_user = st.selectbox("Üye:", targets)
            
        if target_user:
            st.divider()
            col_pass, col_del = st.columns(2)
            with col_pass:
                st.info("🔑 Şifre Sıfırlama")
                new_pass = st.text_input("Yeni Şifre")
                if st.button("Güncelle"):
                    admin_update_password(target_user, new_pass)
                    st.success("Şifre güncellendi.")
            with col_del:
                st.error("🚨 Hesabı Silme")
                if st.button("KULLANICIYI SİL", type="primary"):
                    admin_delete_user(target_user)
                    st.warning("Silindi."); st.rerun()

# 3. KULLANICI
else:
    user = st.session_state['username']
    df = get_user_data(user)
    
    with st.sidebar:
        st.markdown("""
        <div style="padding-bottom: 20px; border-bottom: 1px solid #27272A; margin-bottom: 20px; text-align: center;">
             <h1 style="margin: 0; font-family: 'SF Pro Display', sans-serif; font-weight: 900; font-size: 2.2rem; letter-spacing: 2px; background: linear-gradient(to right, #D4AF37, #FFE680); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">OmnyxWallet</h1>
             <span style="font-size: 0.7rem; color: #71717A; letter-spacing: 3px; text-transform: uppercase;">Premium Finance</span>
        </div>
        """, unsafe_allow_html=True)
        menu = st.radio("MENÜ", ["📊 Dashboard", "📝 İşlem Yönetimi", "📉 Limitler & AI", "🗂️ Raporlar"])
        st.markdown("---")
        if st.button("🔄 Verileri Yenile"): st.rerun()
        if st.button("Çıkış"): st.session_state['logged_in']=False; st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Finansal Özet")
        
        now = datetime.now()
        total_kasa, mo_inc, mo_exp, mo_net = 0.0, 0.0, 0.0, 0.0
        today_inc, today_exp, today_net = 0.0, 0.0, 0.0
        df_mo = pd.DataFrame()

        if not df.empty:
            total_inc = df[df['type']=='Gelir']['amount'].sum()
            total_exp = df[df['type']=='Gider']['amount'].sum()
            total_kasa = total_inc - total_exp
            df_mo = df[(df['date'].dt.month == now.month) & (df['date'].dt.year == now.year)]
            if not df_mo.empty:
                mo_inc = df_mo[df_mo['type']=='Gelir']['amount'].sum()
                mo_exp = df_mo[df_mo['type']=='Gider']['amount'].sum()
                mo_net = mo_inc - mo_exp
            df_today = df[df['date'].dt.date == now.date()]
            if not df_today.empty:
                today_inc = df_today[df_today['type']=='Gelir']['amount'].sum()
                today_exp = df_today[df_today['type']=='Gider']['amount'].sum()
                today_net = today_inc - today_exp

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💎 GENEL TOPLAM", f"{total_kasa:,.2f} ₺")
        c2.metric(f"📥 Gelir ({now.strftime('%B')})", f"{mo_inc:,.2f} ₺")
        c3.metric(f"📤 Gider ({now.strftime('%B')})", f"{mo_exp:,.2f} ₺")
        c4.metric("Aylık Net", f"{mo_net:,.2f} ₺", delta_color="normal" if mo_net>=0 else "inverse")
        
        st.divider()
        
        col_main, col_side = st.columns([1.2, 1.5])
        
        with col_main:
            st.subheader("📅 Bugünün Özeti")
            kt1, kt2, kt3 = st.columns(3)
            kt1.metric("Giriş", f"{today_inc:,.0f}", label_visibility="collapsed")
            kt2.metric("Çıkış", f"{today_exp:,.0f}", label_visibility="collapsed")
            kt3.metric("Net", f"{today_net:,.0f}", delta_color="normal" if today_net>=0 else "inverse", label_visibility="collapsed")
            
            st.caption(f"Giriş: {today_inc:,.0f}₺ | Çıkış: {today_exp:,.0f}₺ | Net: {today_net:,.0f}₺")
            
            if not df.empty:
                df_td = df[df['date'].dt.date == now.date()]
                if not df_td.empty:
                    for _, row in df_td.iterrows():
                        c = "#FF4B4B" if row['type']=="Gider" else "#00FFA3"
                        st.markdown(f"""
                        <div style="background: #131316; padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 3px solid {c}; display:flex; justify-content:space-between; align-items:center;">
                            <div><span style="font-size:13px; color:#E0E0E0;">{row['category']}</span><br><span style="font-size:10px; color:#71717A;">{row['description'][:20]}</span></div>
                            <span style="font-weight:bold; color:#FFF;">{row['amount']:,.0f} ₺</span>
                        </div>""", unsafe_allow_html=True)
                else: st.caption("Bugün henüz işlem yok.")
            else: st.caption("Veri yok.")
            
            st.write("")
            # MİNİMAL PASTA (SOL ALT)
            if not df_mo.empty and not df_mo[df_mo['type']=='Gider'].empty:
                st.subheader("Harcama Dağılımı")
                # FIX: Renk skalasını Gold yerine Oranges yaptık
                fig_pie = px.pie(df_mo[df_mo['type']=='Gider'], values='amount', names='category', 
                                 hole=0.6, template="plotly_dark", color_discrete_sequence=px.colors.sequential.Oranges)
                fig_pie.update_layout(showlegend=False, margin=dict(l=10,r=10,t=10,b=10), height=220, paper_bgcolor="rgba(0,0,0,0)")
                fig_pie.update_traces(textposition='inside', textinfo='percent')
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_side:
            st.subheader("🔄 Abonelikler")
            if not df.empty:
                df_subs = df[df['category'] == "Abonelik - İnternet/Dijital"].copy()
                if not df_subs.empty:
                    for _, row in df_subs.iterrows():
                        next_date = sonraki_odeme_bul(row['date'])
                        days_left = (next_date - datetime.now().date()).days
                        border_c = "#2ECC71"
                        if days_left < 3: border_c = "#EF4444"
                        elif days_left < 10: border_c = "#F59E0B"
                        st.markdown(f"""
                        <div style="background: rgba(30,30,35,0.4); border:1px solid #27272A; padding: 12px; border-radius: 10px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                            <div style="display:flex; align-items:center; gap:10px;">
                                <div style="width:10px; height:10px; border-radius:50%; background-color:{border_c};"></div>
                                <div>
                                    <div style="font-weight:600; color:#FAFAFA; font-size:14px;">{row['description'] or 'Servis'}</div>
                                    <div style="font-size:11px; color:#71717A;">{next_date.strftime('%d.%m.%Y')}</div>
                                </div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-weight:bold; color:#D4AF37;">{row['amount']:,.0f} ₺</div>
                                <div style="font-size:11px; color:#A1A1AA;">{days_left} gün kaldı</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else: st.info("Aktif abonelik yok.")
            else: st.info("Veri yok.")

            st.write("")
            st.subheader("Günlük Trend")
            if not df_mo.empty:
                daily_trend = df_mo.groupby(['date', 'type'])['amount'].sum().reset_index()
                fig_bar = px.bar(daily_trend, x="date", y="amount", color="type",
                              color_discrete_map={"Gelir": "#00FFA3", "Gider": "#FF4B4B"}, 
                              template="plotly_dark")
                fig_bar.update_layout(showlegend=True, margin=dict(l=0,r=0,t=0,b=0), height=250, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_bar, use_container_width=True)
            else: st.caption("Grafik verisi yok.")

    # --- İŞLEMLER ---
    elif menu == "📝 İşlem Yönetimi":
        st.title("İşlem Merkezi")
        st.subheader("🔴 Gider Ekle")
        with st.form("gider"):
            c1,c2,c3,c4 = st.columns([1,1,1.5,2])
            dd = c1.date_input("Tarih", datetime.now())
            da = c2.number_input("Tutar", min_value=0.0, step=50.0)
            dc = c3.selectbox("Kategori", GIDER_KATEGORILERI)
            de = c4.text_input("Açıklama")
            if st.form_submit_button("Gider Kaydet"): run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', (user, dd, "Gider", dc, da, de)); st.success("Kaydedildi"); st.rerun()
        st.markdown("---")
        st.subheader("🟢 Gelir Ekle")
        with st.form("gelir"):
            c1,c2,c3,c4 = st.columns([1,1,1.5,2])
            gd = c1.date_input("Tarih", datetime.now(), key="gd")
            ga = c2.number_input("Tutar", min_value=0.0, step=50.0, key="ga")
            gc = c3.selectbox("Kategori", GELIR_KATEGORILERI, key="gc")
            ge = c4.text_input("Açıklama", key="ge")
            if st.form_submit_button("Gelir Kaydet"): run_query('INSERT INTO transactions(username, date, type, category, amount, description) VALUES (?,?,?,?,?,?)', (user, gd, "Gelir", gc, ga, ge)); st.success("Kaydedildi"); st.rerun()
        st.markdown("---")
        st.subheader("📋 Kayıt Defteri")
        if not df.empty:
            df_edit = df[['id','date','type','category','amount','description']].sort_values('date', ascending=False)
            ch = st.data_editor(df_edit, column_config={"id":None, "date":st.column_config.DateColumn("Tarih", format="DD.MM.YYYY")}, num_rows="dynamic", use_container_width=True, key="edit")
            if st.session_state.get("edit"):
                s = st.session_state["edit"]
                if s["edited_rows"] or s["deleted_rows"]:
                    for i, r in s["edited_rows"].items():
                        rid = df_edit.iloc[i]['id']
                        for k,v in r.items():
                            if k=='date': v=pd.to_datetime(v).strftime('%Y-%m-%d')
                            run_query(f"UPDATE transactions SET {k}=? WHERE id=?", (v, rid))
                    for i in s["deleted_rows"]: rid = df_edit.iloc[i]['id']; run_query("DELETE FROM transactions WHERE id=?", (rid,))
                    st.toast("Güncellendi")

    # --- LİMİTLER ---
    elif menu == "📉 Limitler & AI":
        st.title("Bütçe Kontrol")
        with st.expander("⚙️ Limit Ekle/Güncelle", expanded=False):
            with st.form("lim"):
                c1, c2 = st.columns(2)
                lc = c1.selectbox("Kategori", GIDER_KATEGORILERI)
                lv = c2.number_input("Limit (TL)", step=500.0)
                if st.form_submit_button("Kaydet"): run_query('INSERT OR REPLACE INTO cat_limits VALUES (?,?,?)', (user, lc, lv)); st.success("Tamam"); st.rerun()
        res = run_query('SELECT category, limit_amount FROM cat_limits WHERE username=?', (user,), fetch=True)
        limits = {r[0]:r[1] for r in res}
        ai_adv, ai_st = generate_ai_advice(df, limits)
        ai_c = "#2ECC71" if ai_st == "good" else "#EF4444" if ai_st == "critical" else "#F59E0B"
        st.markdown(f"""<div style="background:#18181B; border-left:4px solid {ai_c}; padding:15px; border-radius:8px; margin:20px 0;"><h4 style="margin:0; color:#D4AF37;">Omnyx AI</h4><p style="margin:5px 0 0 0; font-size:14px; color:#A1A1AA;">{ai_adv[0]}</p></div>""", unsafe_allow_html=True)
        if limits:
            now = datetime.now()
            df_g = pd.DataFrame()
            if not df.empty: df_g = df[(df['date'].dt.month==now.month) & (df['type']=='Gider')]
            cols = st.columns(3)
            for idx, (cat, lim) in enumerate(limits.items()):
                spent = 0
                if not df_g.empty: spent = df_g[df_g['category']==cat]['amount'].sum()
                pct = (spent/lim)*100 if lim>0 else 0
                rem = lim - spent
                sc = "#2ECC71"
                if pct > 100: sc = "#EF4444"
                elif pct > 80: sc = "#F59E0B"
                with cols[idx%3]: st.markdown(f"""<div style="background: #18181B; border: 1px solid #27272A; padding: 15px; border-radius: 10px; margin-bottom: 15px;"><div style="font-size: 14px; color: #A1A1AA;">{cat}</div><div style="font-size: 20px; font-weight: bold; color: #FFF; margin: 5px 0;">{spent:,.0f} / {lim:,.0f} ₺</div><div style="width: 100%; background: #27272A; height: 4px; border-radius: 2px; margin-top: 10px;"><div style="width: {min(pct,100)}%; background: {sc}; height: 100%; border-radius: 2px;"></div></div><div style="text-align: right; font-size: 11px; color: {sc}; margin-top: 5px;">{'⚠️ Aşıldı' if pct>100 else f'Kalan: {rem:,.0f} ₺'}</div></div>""", unsafe_allow_html=True)
        else: st.info("Limit yok.")

    # --- RAPORLAR (GÜNCELLENDİ) ---
    elif menu == "🗂️ Raporlar":
        st.title("Dönem Analizi")
        if not df.empty:
            df['P'] = df['date'].dt.strftime('%Y-%m')
            sel = st.selectbox("Dönem Seçiniz", sorted(df['P'].unique(), reverse=True))
            
            df_p = df[df['P']==sel]
            inc = df_p[df_p['type']=='Gelir']['amount'].sum()
            exp = df_p[df_p['type']=='Gider']['amount'].sum()
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Dönem Geliri", f"{inc:,.0f} ₺")
            k2.metric("Dönem Gideri", f"{exp:,.0f} ₺")
            k3.metric("Net Değişim", f"{inc-exp:,.0f} ₺")
            
            # EN ÇOK HARCANAN KATEGORİ (YENİ)
            top_cat = "-"
            if not df_p[df_p['type']=='Gider'].empty:
                top_cat = df_p[df_p['type']=='Gider'].groupby('category')['amount'].sum().idxmax()
            k4.metric("En Çok Harcanan", top_cat)
            
            st.divider()
            
            c_trend, c_sun = st.columns([1.5, 1])
            
            with c_trend:
                st.subheader("Gelir vs Gider Trendi")
                # Çizgi Grafik (Line Chart)
                daily_stats = df_p.groupby(['date', 'type'])['amount'].sum().reset_index()
                if not daily_stats.empty:
                    fig_line = px.line(daily_stats, x='date', y='amount', color='type', 
                                       markers=True, 
                                       color_discrete_map={"Gelir": "#00FFA3", "Gider": "#FF4B4B"},
                                       template="plotly_dark")
                    fig_line.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350)
                    st.plotly_chart(fig_line, use_container_width=True)
                else: st.info("Trend verisi yok.")

            with c_sun:
                st.subheader("Harcama Detayı")
                if not df_p[df_p['type']=='Gider'].empty:
                    # FIX: Colors düzeltildi (Oranges)
                    fig_sun = px.sunburst(df_p[df_p['type']=='Gider'], path=['category', 'description'], values='amount',
                                          color_discrete_sequence=px.colors.sequential.Oranges)
                    fig_sun.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=350, paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_sun, use_container_width=True)
                else: st.info("Gider yok.")
                
            st.subheader("İşlem Dökümü")
            st.dataframe(df_p.sort_values('date'), use_container_width=True)
        else: st.info("Veri yok.")