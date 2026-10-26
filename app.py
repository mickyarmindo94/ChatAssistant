import streamlit as st
from google import genai

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.title("🛍️ Asisten Toko")
st.write("Buat judul & deskripsi produk otomatis untuk Shopee, Tokopedia, dan TikTok Shop.")

name = st.text_input("Nama produk", placeholder="Tas ransel laptop")
features = st.text_area("Fitur utama", placeholder="Anti air, muat laptop 15 inci, ada port USB")
price = st.text_input("Harga", placeholder="Rp 150.000")
language = st.radio("Bahasa", ["Indonesia", "English"], horizontal=True)

if st.button("Buat Deskripsi"):
    if not name or not features:
        st.warning("Isi nama produk dan fitur dulu ya.")
    else:
        prompt = f"""You are an expert e-commerce copywriter for Indonesian online sellers.
Write in {language}, in a natural, friendly tone. No exaggerated or false claims.

Product: {name}
Features: {features}
Price: {price}

Return:
1. A title (max 80 characters, with searchable keywords)
2. A persuasive description (2 short paragraphs)
3. 5 bullet points of key benefits
4. 8 hashtags
5. A short Instagram/TikTok caption
"""
        with st.spinner("Sedang menulis..."):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Terjadi error: {e}")
