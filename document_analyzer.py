"""
AI Document Analyzer
Uses OpenAI to analyze credit reports, dispute responses, and supporting documents
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import PyPDF2

load_dotenv()

def get_openai_client():
    """Lazy initialization of OpenAI client"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)

def extract_text_from_pdf(pdf_path, max_pages=10):
    """Extract text from PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(min(len(pdf_reader.pages), max_pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            return text
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def analyze_credit_report(pdf_text):
    """
    Analyze credit report and extract derogatory accounts
    """
    client = get_openai_client()
    prompt = f"""You are a credit repair expert analyzing a credit report. 
Extract ALL derogatory accounts (collections, charge-offs, late payments, etc.) from this credit report.

For each derogatory account, provide:
1. Bureau (Experian, Equifax, or TransUnion)
2. Creditor name
3. Account number (last 4 digits if available)
4. Account type (Credit Card, Auto Loan, Medical, Collection, etc.)
5. Balance amount
6. Recommended dispute reason (be specific based on the issue)
7. Priority (High/Medium/Low based on impact)

Credit Report Text:
{pdf_text[:8000]}

Return a JSON object with this structure:
{{
    "accounts": [
        {{
            "bureau": "Experian",
            "creditor_name": "ABC Collections",
            "account_number": "1234",
            "account_type": "Collection",
            "balance": 500.00,
            "dispute_reason": "Account does not belong to me - possible identity theft",
            "priority": "High",
            "notes": "Collection from 2020, no documentation provided"
        }}
    ],
    "summary": "Found X derogatory accounts. Focus on high-priority items first.",
    "recommendations": ["Specific action steps for user"]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a credit repair expert. Extract derogatory accounts from credit reports and provide actionable dispute strategies."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    
    except Exception as e:
        return {
            "error": str(e),
            "accounts": [],
            "summary": "AI analysis failed",
            "recommendations": []
        }

def analyze_bureau_response(pdf_text, original_dispute_reason=None):
    """
    Analyze bureau response letter
    """
    client = get_openai_client()
    prompt = f"""You are a credit repair expert analyzing a credit bureau response letter.

Original Dispute: {original_dispute_reason}

Bureau Response:
{pdf_text[:8000]}

Analyze the response and provide:
1. Outcome: Was the dispute successful, verified, or partially successful?
2. Next action: What should the user do next?
3. Escalation needed: Should this be escalated?
4. Key findings: What did the bureau say?
5. Timeline: Any deadlines mentioned?

Return JSON:
{{
    "outcome": "verified|deleted|updated|pending",
    "success": true/false,
    "next_action": "Specific step to take",
    "escalation_recommended": true/false,
    "escalation_reason": "Why escalate",
    "key_findings": ["Point 1", "Point 2"],
    "timeline": "Any deadlines or dates",
    "followup_strategy": "What to do next"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a credit repair expert analyzing bureau response letters."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    
    except Exception as e:
        return {
            "error": str(e),
            "outcome": "unknown",
            "success": False,
            "next_action": "Manual review required"
        }

def analyze_supporting_document(pdf_text, document_type):
    """
    Analyze supporting evidence documents
    """
    client = get_openai_client()
    prompt = f"""You are a credit repair expert analyzing a {document_type} document.

Document Content:
{pdf_text[:8000]}

Extract key information:
1. Document date
2. Key facts that support dispute
3. Account numbers or references mentioned
4. Amounts or balances
5. How this document helps the dispute case

Return JSON:
{{
    "document_date": "Date from document",
    "key_facts": ["Fact 1", "Fact 2"],
    "accounts_mentioned": ["Account numbers found"],
    "amounts": ["Any dollar amounts"],
    "dispute_support": "How this helps the case",
    "usability": "strong|moderate|weak"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a credit repair expert analyzing supporting documents."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    
    except Exception as e:
        return {
            "error": str(e),
            "key_facts": [],
            "dispute_support": "Analysis failed"
        }

def analyze_document(file_path, document_type, context=None):
    """
    Main document analysis function
    Routes to appropriate analyzer based on document type
    """
    # Extract text from PDF
    if file_path.lower().endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    else:
        return {"error": "Only PDF files are supported currently"}
    
    if not text or text.startswith("Error"):
        return {"error": "Could not extract text from PDF"}
    
    # Route to appropriate analyzer
    if document_type == "credit_report":
        return analyze_credit_report(text)
    elif document_type == "bureau_response":
        return analyze_bureau_response(text, context or "")
    elif document_type in ["evidence", "bank_statement", "receipt", "other"]:
        return analyze_supporting_document(text, document_type)
    else:
        return {"error": "Unknown document type"}

# Example usage
if __name__ == "__main__":
    # Test the analyzer
    result = analyze_document("sample.pdf", "credit_report")
    print(json.dumps(result, indent=2))
