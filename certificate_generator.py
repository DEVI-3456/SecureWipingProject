# certificate_generator.py
# FINAL – STABLE – PYINSTALLER SAFE – CRASH SAFE

import sys
import os
import json
import random
import datetime
import qrcode
from jinja2 import Template
from xhtml2pdf import pisa

# =================================================
# ASSETS RESOLUTION (ONEFILE + ONEDIR + NORMAL)
# =================================================

def get_assets_dir():
    # PyInstaller environment
    if getattr(sys, "frozen", False):

        # onefile mode (_MEIPASS)
        base = getattr(sys, "_MEIPASS", None)
        if base:
            assets = os.path.join(base, "assets")
            if os.path.isdir(assets):
                return assets

        # onedir mode (_internal/assets)
        exe_dir = os.path.dirname(sys.executable)
        internal_assets = os.path.join(exe_dir, "_internal", "assets")
        if os.path.isdir(internal_assets):
            return internal_assets

    # normal python run
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


ASSETS_DIR = get_assets_dir()

# certificates folder (safe location)
CERT_DIR = os.path.join(os.getcwd(), "certificates")
os.makedirs(CERT_DIR, exist_ok=True)

# =================================================
# HTML TEMPLATE
# =================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@page { size: A4 landscape; margin: 8mm; }
body { font-family: "Times New Roman"; font-size: 10px; }

.certificate {
    border: 5px solid #0d47a1;
    padding: 6px;
}
.inner {
    border: 2px solid #c9a44c;
    padding: 10px;
}
.header { text-align: center; }
.logo { width: 60px; height: 60px; }

h1 { color: #0d47a1; margin: 4px 0; }
h2 { margin: 0 0 6px 0; font-size: 13px; }

.intro { text-align: center; margin: 10px 0; }

table.main-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9px;
}
table.main-table th, table.main-table td {
    border: 1px solid #ccc;
    padding: 4px;
}
table.main-table th {
    background: #f2f2f2;
    width: 30%;
    text-align: left;
}

.bottom-table { width: 100%; margin-top: 25px; }
.sign-box { text-align: left; padding-left: 60px; }
.qr-box { text-align: right; padding-right: 60px; }

.signature-img { width: 220px; height: 80px; }
.qr-img { width: 100px; height: 100px; }

.footer {
    text-align: center;
    font-size: 8.5px;
    margin-top: 20px;
    color: #555;
}
</style>
</head>

<body>
<div class="certificate">
<div class="inner">

<div class="header">
{% if logo_path %}
<img src="{{ logo_path }}" class="logo">
{% endif %}
<h1>SECURE DATA ERASURE CERTIFICATE</h1>
<h2>Certificate of Compliance</h2>
</div>

<div class="intro">
This certificate confirms that the following file has been securely erased
in accordance with <b>{{ standardCompliance }}</b> using <b>{{ toolVersion }}</b>.
</div>

<table class="main-table">
<tr><th>Certificate ID</th><td>{{ certificateId }}</td></tr>
<tr><th>File Name</th><td>{{ fileName }}</td></tr>
<tr><th>File Path</th><td>{{ filePath }}</td></tr>
<tr><th>File Size</th><td>{{ fileSize }} bytes</td></tr>
<tr><th>Number of Passes</th><td>{{ passes }}</td></tr>
<tr><th>Original Hash</th><td>{{ originalHash }}</td></tr>
<tr><th>Final Hash</th><td>{{ finalHash }}</td></tr>
<tr><th>Status</th><td>{{ status }}</td></tr>
<tr><th>Date</th><td>{{ wipeDate }}</td></tr>
<tr><th>Compliance</th><td>{{ standardCompliance }}</td></tr>
</table>

<table class="bottom-table">
<tr>
<td class="sign-box">
{% if signature_path %}
<img src="{{ signature_path }}" class="signature-img"><br>
<b>Head of Security</b>
{% endif %}
</td>

<td class="qr-box">
{% if qr_path %}
<img src="{{ qr_path }}" class="qr-img"><br>
Scan to Verify Certificate
{% endif %}
</td>
</tr>
</table>

<div class="footer">
Digitally generated certificate — no physical signature required<br>
Authorized by SecureWiper Systems Pvt Ltd
</div>

</div>
</div>
</body>
</html>
"""

# =================================================
# LINK CALLBACK (SAFE FOR XHTML2PDF)
# =================================================

def link_callback(uri, rel):
    # only absolute paths are used
    if uri.startswith("http"):
        return uri
    return uri

# =================================================
# PDF GENERATION (NO CRASH)
# =================================================

def html_to_pdf(html, output_path):
    with open(output_path, "w+b") as f:
        pisa.CreatePDF(
            html,
            dest=f,
            link_callback=link_callback
        )

# =================================================
# QR GENERATION (SAFE)
# =================================================

def generate_qr(cert_id):
    try:
        qr = qrcode.make(f"https://securewiper.io/verify/{cert_id}")
        qr_path = os.path.join(CERT_DIR, f"{cert_id}_qr.png")
        qr.save(qr_path)
        return qr_path
    except Exception:
        return None

# =================================================
# MAIN CERTIFICATE FUNCTION (FULLY CRASH SAFE)
# =================================================

def generate_html_certificate(
    file_path, original_hash, final_hash, size, passes, success=True
):
    try:
        cert_id = f"SWC-{datetime.datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

        # asset paths
        logo_path = os.path.join(ASSETS_DIR, "logo.png")
        signature_path = os.path.join(ASSETS_DIR, "esignature.png")

        # graceful fallbacks
        if not os.path.isfile(logo_path):
            logo_path = None
        if not os.path.isfile(signature_path):
            signature_path = None

        qr_path = generate_qr(cert_id)
        if qr_path and not os.path.isfile(qr_path):
            qr_path = None

        data = {
            "certificateId": cert_id,
            "fileName": os.path.basename(file_path),
            "filePath": file_path,
            "fileSize": f"{size:,}",
            "passes": passes,
            "originalHash": original_hash,
            "finalHash": final_hash,
            "status": "SUCCESS" if success else "FAILED",
            "wipeDate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "toolVersion": "SecureWiper v2.0",
            "standardCompliance": "NIST SP 800-88 Rev. 1",
            "logo_path": logo_path.replace("\\", "/") if logo_path else None,
            "signature_path": signature_path.replace("\\", "/") if signature_path else None,
            "qr_path": qr_path.replace("\\", "/") if qr_path else None,
        }

        html = Template(HTML_TEMPLATE).render(**data)

        pdf_path = os.path.join(CERT_DIR, f"{cert_id}.pdf")
        html_to_pdf(html, pdf_path)

        with open(pdf_path.replace(".pdf", ".json"), "w", encoding="utf-8") as jf:
            json.dump(data, jf, indent=4)

        return pdf_path, None

    except Exception as e:
        # NEVER crash caller (important for QThread)
        return None, str(e)
