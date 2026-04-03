# 🚀 HuuChien Acoustic PRO MAX (FREEMIUM VERSION)

import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf
import streamlit as st
import base64
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ================= BACKGROUND =================
def set_bg(image_file):
    with open(image_file, "rb") as f:
        data = base64.b64encode(f.read()).decode()

    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{data}");
        background-size: cover;
    }}
    .block-container {{
        background: rgba(0,0,0,0.75);
        border-radius:20px;
        padding:25px;
    }}
    </style>
    """, unsafe_allow_html=True)

# ================= SWEEP =================
def generate_log_sweep(sr=48000, duration=10):
    t = np.linspace(0, duration, int(sr*duration))
    k = duration / np.log(20000/20)
    return np.sin(2*np.pi * 20 * (np.exp(t/k) - 1))

# ================= IR =================
def compute_ir(recorded, sr):
    recorded = recorded / (np.max(np.abs(recorded)) + 1e-9)
    duration = len(recorded) / sr
    t = np.linspace(0, duration, len(recorded))
    k = duration / np.log(20000/20)
    sweep = np.sin(2*np.pi * 20 * (np.exp(t/k) - 1))
    inv = sweep[::-1] / (np.exp(t/k) + 1e-9)
    ir = np.convolve(recorded, inv, mode='full')
    peak = np.argmax(np.abs(ir))
    ir = ir[peak:peak + int(sr*2)]
    ir = ir / (np.max(np.abs(ir)) + 1e-9)
    return ir

# ================= RT60 =================
def compute_rt60(ir, sr):
    energy = np.cumsum(ir[::-1]**2)[::-1]
    energy /= np.max(energy)
    db = 10*np.log10(energy+1e-9)
    t = np.arange(len(db))/sr
    try:
        t1 = t[np.where(db<=-5)[0][0]]
        t2 = t[np.where(db<=-35)[0][0]]
        return round((t2-t1)*2,3)
    except:
        return 0

# ================= FREQUENCY =================
def frequency_response(ir, sr):
    fft = np.fft.rfft(ir)
    freqs = np.fft.rfftfreq(len(ir), 1/sr)
    mag = 20*np.log10(np.abs(fft)+1e-9)
    return freqs, mag

# ================= SPL =================
def compute_spl(data, calibration_db=94):
    rms = np.sqrt(np.mean(data**2))
    dbfs = 20 * np.log10(rms + 1e-9)
    return round(dbfs + calibration_db,2)

# ================= PDF =================
def export_pdf(rt, spl, wall, price):
    doc = SimpleDocTemplate("report.pdf")
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph("HuuChien Acoustic Report", styles['Title']))
    content.append(Spacer(1,10))
    content.append(Paragraph(f"SPL: {spl} dB", styles['Normal']))
    content.append(Paragraph(f"RT60: {rt}s", styles['Normal']))
    content.append(Paragraph(f"Tiêu âm tường: {wall} m2", styles['Normal']))
    content.append(Paragraph(f"Chi phí: {price:,} VND", styles['Normal']))

    doc.build(content)

# ================= UI =================
st.set_page_config(layout="wide")
set_bg("logo.png")

# ================= FREEMIUM CONTROL =================
if 'usage' not in st.session_state:
    st.session_state['usage'] = 0

MAX_FREE = 3

# ================= LICENSE KEY =================
VALID_KEYS = ["HC-001","HC-002","HC-003"]

if 'pro' not in st.session_state:
    st.session_state['pro'] = False

st.title("🎧 HuuChien dB Acoustic")

st.markdown("""
## 📌 Hướng dẫn sử dụng
1. Tải sweep
2. Phát bằng loa
3. Thu bằng điện thoại
4. Upload file
5. Xem kết quả
""")

# FREE LIMIT + KEY
if not st.session_state['pro']:
    if st.session_state['usage'] >= MAX_FREE:
        st.error("🚫 Bạn đã hết lượt miễn phí")

        key = st.text_input("🔑 Nhập key để mở PRO")

        if st.button("Kích hoạt PRO"):
            if key in VALID_KEYS:
                st.session_state['pro'] = True
                st.success("✅ Mở khóa thành công")
                st.rerun()
            else:
                st.error("❌ Key sai")

        st.markdown("👉 Liên hệ Zalo để mua key: 0933525247")
        st.stop()

# SWEEP
if st.button("⬇️ Tải Sweep chuẩn"):
    sweep = generate_log_sweep()
    sf.write("sweep.wav", sweep, 48000)
    st.download_button("Download", open("sweep.wav","rb"))

# UPLOAD
file = st.file_uploader("Upload file đo (.wav)")

if file:
    data, sr = sf.read(file)
    if len(data.shape)>1:
        data = data[:,0]

    st.session_state['usage'] += 1

    spl = compute_spl(data)
    st.success(f"SPL: {spl} dB")

    ir = compute_ir(data, sr)
    freqs, mag = frequency_response(ir, sr)

    if np.max(mag)-np.min(mag) < 15:
        st.error("Sai file đo")
        st.stop()

    fig = plt.figure()
    plt.plot(freqs, mag)
    plt.xscale('log')
    st.pyplot(fig)

    rt = compute_rt60(ir, sr)
    st.write(f"RT60: {rt}s")

    if rt > 0.6:
        st.error("Phòng dội → cần tiêu âm")
    else:
        st.success("Phòng ổn")

    area = st.number_input("Diện tích",10.0)
    wall = round(area*0.6,1)
    st.write(f"Tiêu âm tường: {wall} m²")

    price = int(wall*650000)
    st.write(f"Chi phí: {price:,} VND")

    # ================= BẢNG PRO =================
    st.markdown("## 📊 Bảng phân tích PRO")

    status = "Ổn"
    solution = "Không cần xử lý"

    if rt > 0.7:
        status = "🔴 Dội mạnh"
        solution = "Bass trap + tiêu âm dày"
    elif rt > 0.5:
        status = "🟡 Dội nhẹ"
        solution = "Tiêu âm tường + trần"
    else:
        status = "🟢 Chuẩn"
        solution = "OK"

    table_html = f"""
    <div style='background:rgba(255,255,255,0.08);padding:20px;border-radius:15px'>
    <table style='width:100%;color:white'>
        <tr>
            <th>SPL</th>
            <th>RT60</th>
            <th>Đánh giá</th>
            <th>Giải pháp</th>
        </tr>
        <tr>
            <td>{spl} dB</td>
            <td>{rt}s</td>
            <td>{status}</td>
            <td>{solution}</td>
        </tr>
    </table>
    </div>
    """

    st.markdown(table_html, unsafe_allow_html=True)

    if st.button("📄 Xuất PDF"):
        export_pdf(rt, spl, wall, price)
        with open("report.pdf", "rb") as f:
            st.download_button("⬇️ Tải PDF", f, file_name="HuuChien_Report.pdf")

# ================= RUN EXE FIX =================
# Fix lỗi PyInstaller + Streamlit
try:
    import streamlit.web.cli as stcli
    import sys

    if __name__ == "__main__":
        sys.argv = ["streamlit", "run", sys.argv[0], "--global.developmentMode=false"]
        sys.exit(stcli.main())
except Exception as e:
    print("Run bằng CMD: python -m streamlit run app.py")
