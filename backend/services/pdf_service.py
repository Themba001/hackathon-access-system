import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from .qr_service import qr_png_bytes


PAGE_W, PAGE_H = A4


# Creates a clean ticket PDF: Name Surname, Student Number, QR code


def make_ticket_pdf(full_name: str, student_number: str, code_value: str, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)


    # Generate QR PNG in-memory
    png = qr_png_bytes(code_value)
    qr_img = ImageReader(io.BytesIO(png))


    c = canvas.Canvas(out_path, pagesize=A4)


    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(25*mm, (PAGE_H-30*mm), "NWU Internal Hackathon – Ticket")


    # Body text
    c.setFont("Helvetica", 13)
    c.drawString(25*mm, (PAGE_H-50*mm), f"Name Surname: {full_name}")
    c.drawString(25*mm, (PAGE_H-60*mm), f"Student Number: {student_number}")


    # QR Code
    qr_size = 60*mm
    c.drawImage(qr_img, 25*mm, (PAGE_H-140*mm), width=qr_size, height=qr_size, mask='auto')


    # Footer note
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(25*mm, 20*mm, "Present this ticket at bus boarding, registration, and meal collection.")


    c.showPage()
    c.save()