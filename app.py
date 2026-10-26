import re
import time

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Asisten Toko", page_icon="🛍️")

MODEL = "gemini-flash-lite-latest"  # change here if you want another model
MAX_BULK = 10  # max products per bulk run (protects the free quota)

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

PLATFORMS = {
    "Shopee": "keyword-rich title of about 80-100 characters; clear description with short lines; light emoji use",
    "Tokopedia": "clean, clear title of about 60-70 characters; detailed, trustworthy description with specs",
    "TikTok Shop": "short punchy title; description opens with a hook; trendy, energetic wording",
    "Instagram": "caption style: strong first line, short paragraphs, a call to action, emoji welcome",
}

TONES = {
    "Santai & ramah": "casual and friendly, like a helpful seller chatting with a customer",
    "Formal & profesional": "polite, formal and professional",
    "Lucu & seru": "playful and fun, light humor, still clear about the product",
    "Premium & elegan": "elegant, refined, premium feel without exaggeration",
}

SECTIONS = {
    "JUDUL": "Judul",
    "DESKRIPSI": "Deskripsi",
    "POIN": "Poin keunggulan",
    "HASHTAG": "Hashtag",
    "CAPTION": "Caption Instagram/TikTok",
}


def build_prompt(name, features, price, language, platform, tone, has_photo):
    lines = [
        "You are an expert e-commerce copywriter for Indonesian online sellers.",
        f"Write in {language}.",
        f"Platform: {platform} ({PLATFORMS[platform]}).",
        f"Tone: {TONES[tone]}.",
        "Rules: be natural and persuasive, no exaggerated or false claims. "
        "Never invent specs, materials, sizes, or certifications that were not given "
        "or clearly visible. If something is unknown, leave it out.",
    ]
    if has_photo:
        lines.append(
            "A product photo is attached. Use only what you can clearly see in it, "
            "plus the details below."
        )
    lines += [
        f"Product name: {name or '(not given - infer from the photo)'}",
        f"Features: {features or '(not given - infer from the photo)'}",
        f"Price: {price or '(not given - do not mention a price)'}",
        "",
        "Return EXACTLY these 5 sections. Each header must be alone on its own line:",
        "### JUDUL",
        "(one title)",
        "### DESKRIPSI",
        "(persuasive description, 2 short paragraphs)",
        "### POIN",
        "(5 bullet points of key benefits, each starting with '- ')",
        "### HASHTAG",
        "(8 hashtags on one line)",
        "### CAPTION",
        "(one short Instagram/TikTok caption)",
    ]
    return "\n".join(lines)


def generate(prompt, image=None):
    contents = [prompt]
    if image is not None:
        data, mime = image
        contents = [types.Part.from_bytes(data=data, mime_type=mime), prompt]
    response = client.models.generate_content(model=MODEL, contents=contents)
    return response.text or ""


def parse_sections(text):
    parts = re.split(r"^###\s*([A-Z]+)\s*$", text, flags=re.MULTILINE)
    result = {}
    for i in range(1, len(parts), 2):
        result[parts[i].strip()] = parts[i + 1].strip()
    return result


def friendly_error(e):
    msg = str(e)
    if "429" in msg or "quota" in msg.lower() or "RESOURCE_EXHAUSTED" in msg:
        return "Kuota gratis habis. Tunggu beberapa menit (atau besok) lalu coba lagi."
    if "API key" in msg or "API_KEY" in msg:
        return "API key tidak valid. Cek lagi Secrets di Streamlit."
    if "404" in msg or "not found" in msg.lower():
        return "Nama model tidak ditemukan. Cek nilai MODEL di app.py."
    return f"Terjadi error: {msg}"


# ---------- Header & shared settings ----------
st.title("🛍️ Asisten Toko")
st.write("Buat judul & deskripsi produk otomatis untuk Shopee, Tokopedia, TikTok Shop, dan Instagram.")

c1, c2, c3 = st.columns(3)
platform = c1.selectbox("Platform", list(PLATFORMS.keys()))
tone = c2.selectbox("Gaya bahasa", list(TONES.keys()))
language = c3.radio("Bahasa", ["Indonesia", "English"], horizontal=True)

tab_single, tab_bulk = st.tabs(["📸 Satu produk", "📦 Banyak produk (Bulk)"])

# ---------- Single product ----------
with tab_single:
    photo = st.file_uploader(
        "Foto produk (opsional, tapi bikin hasil lebih akurat)",
        type=["png", "jpg", "jpeg", "webp"],
        key="photo",
    )
    if photo:
        st.image(photo, width=250)

    name = st.text_input("Nama produk", placeholder="Tas ransel laptop")
    features = st.text_area("Fitur utama", placeholder="Anti air, muat laptop 15 inci, ada port USB")
    price = st.text_input("Harga", placeholder="Rp 150.000")
    st.caption("Kalau kamu upload foto, nama dan fitur boleh dikosongkan.")

    if st.button("Buat Deskripsi", key="single_btn"):
        if not photo and not (name and features):
            st.warning("Upload foto, atau isi nama produk dan fitur dulu ya.")
        else:
            image = (photo.getvalue(), photo.type) if photo else None
            prompt = build_prompt(name, features, price, language, platform, tone, bool(photo))
            with st.spinner("Sedang menulis..."):
                try:
                    text = generate(prompt, image)
                    sections = parse_sections(text)
                    if not sections:
                        st.code(text, language=None, wrap_lines=True)
                    else:
                        for key, label in SECTIONS.items():
                            if key in sections:
                                st.markdown(f"**{label}**")
                                # st.code has a built-in copy button (top right of each box)
                                st.code(sections[key], language=None, wrap_lines=True)
                    st.caption("⚠️ Periksa dulu hasilnya sebelum dipakai. AI bisa salah menebak fitur produk.")
                except Exception as e:
                    st.error(friendly_error(e))

# ---------- Bulk mode ----------
with tab_bulk:
    st.write(
        f"Upload file CSV atau Excel dengan kolom **nama**, **fitur**, **harga**. "
        f"Maksimal {MAX_BULK} produk per proses (untuk menjaga kuota gratis)."
    )
    template = pd.DataFrame(
        {
            "nama": ["Tas ransel laptop", "Kaos polos katun"],
            "fitur": ["Anti air, muat laptop 15 inci, ada port USB", "Bahan katun combed 30s, adem, tersedia 5 warna"],
            "harga": ["Rp 150.000", "Rp 55.000"],
        }
    )
    st.download_button(
        "Download template CSV",
        template.to_csv(index=False).encode("utf-8-sig"),
        file_name="template_produk.csv",
        mime="text/csv",
    )

    upload = st.file_uploader("Upload file produk", type=["csv", "xlsx"], key="bulk_file")

    if upload:
        try:
            df = pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)
            df.columns = [str(c).strip().lower() for c in df.columns]
            df = df.fillna("").astype(str)
        except Exception as e:
            df = None
            st.error(f"File tidak bisa dibaca: {e}")

        if df is not None:
            if "nama" not in df.columns:
                st.error("File harus punya kolom 'nama'. Download template di atas sebagai contoh.")
            else:
                st.write(f"Ditemukan {len(df)} produk. Pratinjau:")
                st.dataframe(df.head(MAX_BULK), use_container_width=True)
                if len(df) > MAX_BULK:
                    st.info(f"Hanya {MAX_BULK} produk pertama yang akan diproses.")

                if st.button("Buat semua deskripsi", key="bulk_btn"):
                    records = df.head(MAX_BULK).to_dict("records")
                    results = []
                    bar = st.progress(0.0, text="Memulai...")
                    for i, rec in enumerate(records):
                        pname = rec.get("nama", "").strip()
                        bar.progress(i / len(records), text=f"Memproses {i + 1}/{len(records)}: {pname}")
                        row = {"Nama Produk": pname, "Judul": "", "Deskripsi": "", "Poin": "", "Hashtag": "", "Caption": "", "Status": "OK"}
                        if not pname:
                            row["Status"] = "Dilewati (nama kosong)"
                            results.append(row)
                            continue
                        try:
                            prompt = build_prompt(
                                pname, rec.get("fitur", ""), rec.get("harga", ""),
                                language, platform, tone, False,
                            )
                            sections = parse_sections(generate(prompt))
                            row["Judul"] = sections.get("JUDUL", "")
                            row["Deskripsi"] = sections.get("DESKRIPSI", "")
                            row["Poin"] = sections.get("POIN", "")
                            row["Hashtag"] = sections.get("HASHTAG", "")
                            row["Caption"] = sections.get("CAPTION", "")
                            if not sections:
                                row["Status"] = "Format tidak terbaca"
                        except Exception as e:
                            row["Status"] = friendly_error(e)
                        results.append(row)
                        time.sleep(1)
                    bar.progress(1.0, text="Selesai!")
                    st.session_state["bulk_results"] = pd.DataFrame(results)

    # Results live in session_state so they survive the download-button rerun
    if "bulk_results" in st.session_state:
        out = st.session_state["bulk_results"]
        st.success("Hasil siap. Periksa dulu sebelum dipakai.")
        st.dataframe(out, use_container_width=True)
        st.download_button(
            "Download hasil (CSV)",
            out.to_csv(index=False).encode("utf-8-sig"),
            file_name="hasil_deskripsi_produk.csv",
            mime="text/csv",
        )
