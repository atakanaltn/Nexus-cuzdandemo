import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(
    page_title="NEXUS Final",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

VERI_DOSYASI = "cuzdan_verisi.csv"

# --- 2. CSS TASARIM ---
st.markdown("""
    <style>
        .stApp { background-color: #0E1117; }
        div[data-testid="stMetric"] {
            background-color: #1E1E1E; border: 1px solid #333;
            padding: 15px; border-radius: 8px;
        }
        th { background-color: #262730 !important; color: #FFA500 !important; cursor: pointer; }
        div.stButton > button {
            width: 100%; background-color: #262730; color: white; border: 1px solid #555;
        }
        div.stButton > button:hover { border-color: #00FFA3; color: #00FFA3; }
    </style>
""", unsafe_allow_html=True)

# --- 3. KATEGORİ LİSTELERİ ---
GIDER_KATEGORILERI = [
    "Abonelik - İnternet/Dijital", 
    "Gıda - Market", "Gıda - Restoran", 
    "Konut - Kira", "Konut - Aidat", "Fatura - Elektrik/Su/Gaz",
    "Ulaşım - Yakıt", "Ulaşım - Toplu Taşıma",
    "Kişisel - Giyim", "Kişisel - Bakım", "Sağlık",
    "Eğlence", "Eğitim", "Borç Ödeme", "Diğer"
]
GELIR_KATEGORILERI = ["Maaş", "Prim", "Ek İş", "Yatırım", "Borç Alacak", "Diğer"]

# --- 4. VERİ YÖNETİMİ ---
def veri_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            df = pd.read_csv(VERI_DOSYASI)
            df["Tarih"] = pd.to_datetime(df["Tarih"])
            return df
        except:
            pass
    return pd.DataFrame({
        "Tarih": pd.Series(dtype='datetime64[ns]'),
        "Tür": pd.Series(dtype='str'),
        "Kategori": pd.Series(dtype='str'),
        "Tutar": pd.Series(dtype='float'),
        "Açıklama": pd.Series(dtype='str')
    })

def veri_kaydet(df):
    df.to_csv(VERI_DOSYASI, index=False)

def sonraki_odeme_bul(baslangic_tarihi):
    bugun = datetime.now().date()
    odeme_tarihi = baslangic_tarihi.date()
    while odeme_tarihi < bugun:
        odeme_tarihi += relativedelta(months=1)
    return odeme_tarihi

df = veri_yukle()

# --- YAN MENÜ (SIRALAMA GÜNCELLENDİ) ---
with st.sidebar:
    st.title("💎 NEXUS")
    st.caption("Final Sürüm")
    st.markdown("---")
    menu = st.radio("MENÜ", [
        "📊 Anlık Durum (Bu Ay)", 
        "📝 İşlem Yönetimi",  # 2. Sıraya alındı
        "🔄 Abonelik Takibi", 
        "🗂️ Geçmiş Ay Raporları"
    ])

# ========================================================
# SAYFA 1: ANLIK DURUM
# ========================================================
if menu == "📊 Anlık Durum (Bu Ay)":
    st.title("Finansal Kontrol Paneli")
    
    if df.empty:
        st.info("Veri girişi bekleniyor... Yan menüden 'İşlem Yönetimi'ne gidin.")
    else:
        simdi = datetime.now()
        tum_gelir = df[df["Tür"] == "Gelir"]["Tutar"].sum()
        tum_gider = df[df["Tür"] == "Gider"]["Tutar"].sum()
        genel_varlik = tum_gelir - tum_gider
        
        df_bu_ay = df[(df["Tarih"].dt.month == simdi.month) & (df["Tarih"].dt.year == simdi.year)]
        aylik_gelir = df_bu_ay[df_bu_ay["Tür"] == "Gelir"]["Tutar"].sum()
        aylik_gider = df_bu_ay[df_bu_ay["Tür"] == "Gider"]["Tutar"].sum()
        aylik_net = aylik_gelir - aylik_gider
        
        if aylik_net >= 0:
            renk, ikon = "normal", "📈 KAR"
        else:
            renk, ikon = "inverse", "📉 ZARAR"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💎 TOPLAM VARLIK", f"{genel_varlik:,.2f} ₺", delta="Tüm Birikim")
        c2.metric("📥 Bu Ay Gelir", f"{aylik_gelir:,.2f} ₺")
        c3.metric("📤 Bu Ay Gider", f"{aylik_gider:,.2f} ₺")
        c4.metric(f"Bu Ay Net ({ikon})", f"{aylik_net:,.2f} ₺", delta=f"{aylik_net:,.2f} ₺", delta_color=renk)
        
        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Günlük Akış")
            if not df_bu_ay.empty:
                fig = px.bar(df_bu_ay, x="Tarih", y="Tutar", color="Tür",
                             color_discrete_map={"Gelir": "#00FFA3", "Gider": "#FF4B4B"}, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Bu ay işlem yok.")
        with col2:
            st.subheader("Gider Dağılımı")
            if not df_bu_ay[df_bu_ay["Tür"]=="Gider"].empty:
                fig_pie = px.pie(df_bu_ay[df_bu_ay["Tür"]=="Gider"], values="Tutar", names="Kategori", hole=0.4, template="plotly_dark")
                st.plotly_chart(fig_pie, use_container_width=True)

# ========================================================
# SAYFA 2: İŞLEM YÖNETİMİ (MENÜDE 2. SIRADA)
# ========================================================
elif menu == "📝 İşlem Yönetimi":
    st.title("İşlem Ekle / Düzenle")
    
    with st.expander("➕ YENİ İŞLEM EKLE", expanded=True):
        with st.form("ekle"):
            c1, c2, c3, c4 = st.columns([1,1,1,2])
            tur = c1.selectbox("Tür", ["Gider", "Gelir"])
            tarih = c2.date_input("Tarih", datetime.now())
            tutar = c3.number_input("Tutar", min_value=0.0, step=50.0)
            kategori = c4.selectbox("Kategori", GIDER_KATEGORILERI if tur=="Gider" else GELIR_KATEGORILERI)
            aciklama = st.text_input("Açıklama (Örn: Netflix, Türk Telekom)")
            
            if st.form_submit_button("Kaydet ✅"):
                yeni = pd.DataFrame({"Tarih":[pd.to_datetime(tarih)], "Tür":[tur], "Kategori":[kategori], "Tutar":[tutar], "Açıklama":[aciklama]})
                df = pd.concat([df, yeni], ignore_index=True)
                veri_kaydet(df)
                st.success("Kaydedildi!")
                st.rerun()
    
    st.divider()
    
    st.subheader("Kayıt Defteri")
    st.caption("Sıralamak için başlıklara tıklayın. Düzenlemek için çift tıklayın.")
    
    if not df.empty:
        editor = st.data_editor(
            df.sort_values("Tarih", ascending=False),
            num_rows="dynamic",
            use_container_width=True,
            key="editor",
            column_config={
                "Tutar": st.column_config.NumberColumn(format="%.2f ₺"),
                "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY"),
                "Tür": st.column_config.SelectboxColumn(options=["Gelir", "Gider"], required=True),
                "Kategori": st.column_config.SelectboxColumn(options=GIDER_KATEGORILERI+GELIR_KATEGORILERI, required=True)
            }
        )
        if not df.equals(editor):
            veri_kaydet(editor)
            st.toast("Güncellendi!", icon="💾")

# ========================================================
# SAYFA 3: ABONELİK TAKİBİ
# ========================================================
elif menu == "🔄 Abonelik Takibi":
    st.title("🔄 Aylık Sabit Abonelikler")
    
    df_abonelik = df[df["Kategori"] == "Abonelik - İnternet/Dijital"].copy()
    
    if not df_abonelik.empty:
        abonelik_listesi = []
        for index, row in df_abonelik.iterrows():
            sonraki_tarih = sonraki_odeme_bul(row["Tarih"])
            kalan_gun = (sonraki_tarih - datetime.now().date()).days
            durum = "✅ Ödendi" if kalan_gun > 25 else "⏳ Yaklaşıyor" if kalan_gun > 5 else "🚨 Çok Yakın"
            
            abonelik_listesi.append({
                "Orijinal_Index": index,
                "Hizmet Adı (Düzenle)": row["Açıklama"] if row["Açıklama"] else "İsimsiz",
                "Tutar": row["Tutar"],
                "Sonraki Ödeme": sonraki_tarih,
                "Kalan Gün": f"{kalan_gun} Gün",
                "Durum": durum
            })
            
        df_tablo = pd.DataFrame(abonelik_listesi)
        
        k1, k2 = st.columns(2)
        k1.metric("Aktif Abonelik", len(df_tablo))
        k2.metric("Aylık Toplam", f"{df_tablo['Tutar'].sum():,.2f} ₺")
        
        st.divider()
        st.subheader("Yenileme Listesi")
        
        edited_abonelik = st.data_editor(
            df_tablo[["Hizmet Adı (Düzenle)", "Tutar", "Sonraki Ödeme", "Kalan Gün", "Durum"]],
            use_container_width=True,
            column_config={
                "Sonraki Ödeme": st.column_config.DateColumn(format="DD.MM.YYYY"),
                "Tutar": st.column_config.NumberColumn(format="%.2f ₺"),
                "Durum": st.column_config.TextColumn(disabled=True),
                "Kalan Gün": st.column_config.TextColumn(disabled=True),
                "Sonraki Ödeme": st.column_config.DateColumn(disabled=True),
            },
            hide_index=True
        )
        
        if len(edited_abonelik) == len(df_tablo):
            degisiklik_var = False
            for i, row in edited_abonelik.iterrows():
                orijinal_idx = df_tablo.iloc[i]["Orijinal_Index"]
                if df.at[orijinal_idx, "Açıklama"] != row["Hizmet Adı (Düzenle)"]:
                    df.at[orijinal_idx, "Açıklama"] = row["Hizmet Adı (Düzenle)"]
                    degisiklik_var = True
                if df.at[orijinal_idx, "Tutar"] != row["Tutar"]:
                    df.at[orijinal_idx, "Tutar"] = row["Tutar"]
                    degisiklik_var = True
            
            if degisiklik_var:
                veri_kaydet(df)
    else:
        st.warning("Abonelik bulunamadı. İşlem eklerken 'Abonelik - İnternet/Dijital' kategorisini seçin.")

# ========================================================
# SAYFA 4: GEÇMİŞ RAPORLAR
# ========================================================
elif menu == "🗂️ Geçmiş Ay Raporları":
    st.title("Geçmiş Dönem Analizi")
    
    if not df.empty:
        df["Ay_Yil_Str"] = df["Tarih"].dt.strftime('%Y-%m')
        mevcut_donemler = sorted(df["Ay_Yil_Str"].unique(), reverse=True)
        secilen_donem = st.selectbox("Dönem Seçin:", mevcut_donemler)
        
        df_gecmis = df[df["Ay_Yil_Str"] == secilen_donem]
        g_gelir = df_gecmis[df_gecmis["Tür"] == "Gelir"]["Tutar"].sum()
        g_gider = df_gecmis[df_gecmis["Tür"] == "Gider"]["Tutar"].sum()
        g_net = g_gelir - g_gider
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Gelir", f"{g_gelir:,.2f} ₺")
        k2.metric("Gider", f"{g_gider:,.2f} ₺")
        k3.metric("Kalan", f"{g_net:,.2f} ₺", delta_color="normal" if g_net>=0 else "inverse")
        
        st.subheader("İşlem Dökümü")
        st.dataframe(
            df_gecmis[["Tarih", "Tür", "Kategori", "Tutar", "Açıklama"]].sort_values("Tarih"), 
            use_container_width=True,
            column_config={
                "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY"),
                "Tutar": st.column_config.NumberColumn(format="%.2f ₺")
            }
        )
    else:
        st.warning("Veri yok.")