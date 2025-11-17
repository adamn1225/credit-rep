import pandas as pd
from jinja2 import Environment, FileSystemLoader
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from pathlib import Path
from datetime import date
import os
from ai_generator import generate_dispute_letter_ai

def render_letter(row, template_dir="disputes/templates", use_ai=True):
    """
    Generate letter content - uses AI if enabled, falls back to template
    """
    if use_ai and os.getenv("OPENAI_API_KEY"):
        # Use AI to generate letter
        account_info = {
            'bureau': row.get('bureau'),
            'creditor_name': row.get('creditor_name'),
            'account_number': row.get('account_number'),
            'reason': row.get('reason'),
            'account_type': row.get('account_type', ''),
            'balance': row.get('balance', ''),
            'notes': row.get('notes', '')
        }
        return generate_dispute_letter_ai(account_info)
    else:
        # Fallback to Jinja2 template
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
    """Generate PDF from text content with better formatting"""
    doc = SimpleDocTemplate(str(out_path), pagesize=LETTER,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Create styles
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=6
    )
    
    # Build document content
    story = []
    
    # Split text into paragraphs and add to story
    paragraphs = text.split('\n\n')
    for para in paragraphs:
        if para.strip():
            # Replace single newlines with <br/> for line breaks
            para_formatted = para.replace('\n', '<br/>')
            p = Paragraph(para_formatted, normal_style)
            story.append(p)
            story.append(Spacer(1, 0.1 * inch))
    
    # Build PDF
    doc.build(story)

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
