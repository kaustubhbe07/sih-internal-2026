"""
QR code and PDF certificate generation service.
"""

import io
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors


def generate_qr(payload: str) -> bytes:
    """
    Generate a PNG QR code from a payload string.
    Returns the raw PNG image bytes.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_certificate_pdf(credential, institution_name: str) -> bytes:
    """
    Generate a simple PDF certificate for a credential.
    Returns the raw PDF bytes.
    """
    buf = io.BytesIO()

    c = canvas.Canvas(buf, pagesize=landscape(letter))
    width, height = landscape(letter)

    # Draw a simple border
    c.setStrokeColor(colors.darkblue)
    c.setLineWidth(4)
    c.rect(20, 20, width - 40, height - 40)

    # Draw institution name as header
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2.0, height - 100, institution_name)

    # Draw Certificate of Achievement text
    c.setFont("Helvetica", 24)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2.0, height - 150, "Certificate of Achievement")

    # Draw student details
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2.0, height - 220, f"This is to certify that {credential.student_name}")
    c.drawCentredString(width / 2.0, height - 260, f"Roll No: {credential.roll_no}")
    c.drawCentredString(width / 2.0, height - 300, f"has successfully completed the degree of")

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2.0, height - 340, credential.degree)

    if credential.cgpa:
        c.setFont("Helvetica", 16)
        c.drawCentredString(width / 2.0, height - 380, f"with a CGPA of {credential.cgpa}")

    # Draw custom fields if any
    y_pos = height - 420
    if credential.custom_fields:
        c.setFont("Helvetica", 14)
        for key, value in credential.custom_fields.items():
            label = key.replace("_", " ").title()
            c.drawCentredString(width / 2.0, y_pos, f"{label}: {value}")
            y_pos -= 30

    # Draw issue date
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2.0, 60, f"Issued on: {credential.issue_date}")

    # Embed QR Code in the bottom right corner
    if credential.qr_payload:
        qr_bytes = generate_qr(credential.qr_payload)
        qr_image = ImageReader(io.BytesIO(qr_bytes))

        qr_size = 120
        qr_x = width - 40 - qr_size - 20
        qr_y = 40
        c.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)

        c.setFont("Helvetica", 8)
        c.drawString(qr_x, qr_y - 10, f"ID: {credential.id}")

    c.showPage()
    c.save()

    return buf.getvalue()
