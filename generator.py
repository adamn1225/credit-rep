import pandas as pd
from jinja2 import Environment, FileSystemLoader
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from pathlib import Path
from datetime import date

def render_letter(row, template_dir="disputes/templates"):
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("dispute_letter.j2")

    return template.render(
        today_date=date.today().strftime("%B %d, %Y"),
        bureau=row["bureau"],
        creditor_name=row["creditor_name"],
        account_number=row["account_number"],
        reason=row["reason"],
        full_name="John Doe",
        address="123 Main St, Tampa, FL 33602",
        dob="01/01/1990",
        ssn_last4="1234"
    )

def generate_pdf(text, out_path):
    c = canvas.Canvas(out_path, pagesize=LETTER)
    text_obj = c.beginText(72, 720)
    for line in text.split("\n"):
        text_obj.textLine(line)
    c.drawText(text_obj)
    c.showPage()
    c.save()

def build_letters(csv_path="data/accounts.csv"):
    df = pd.read_csv(csv_path)
    output_files = []
    for _, row in df.iterrows():
        text = render_letter(row)
        bureau_dir = Path(f"disputes/generated/{row['bureau'].lower()}")
        bureau_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = bureau_dir / f"{row['account_number']}.pdf"
        generate_pdf(text, pdf_path)
        output_files.append((pdf_path, row))
    return output_files
