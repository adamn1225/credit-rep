"""
AI Letter Generation Module
Uses Ollama (local LLM) or OpenAI GPT-4 to generate personalized credit dispute letters
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# OpenAI configuration (lazy initialization)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_openai_client():
    """Lazy initialize OpenAI client only when needed"""
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}")
        return None

# Ollama configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"  # Using llama3.2 for better text generation

def generate_dispute_letter_ollama(account_info: dict, personal_info: dict = None) -> str:
    """
    Generate a personalized credit dispute letter using Ollama (local LLM)
    
    Args:
        account_info: Dictionary with account details
        personal_info: Dictionary with sender details (optional)
    
    Returns:
        Generated letter text
    """
    
    # Build the prompt
    prompt = f"""You are an expert credit repair specialist. Generate a professional, legally-compliant credit dispute letter.

ACCOUNT INFORMATION:
- Credit Bureau: {account_info.get('bureau', 'N/A')}
- Creditor: {account_info.get('creditor_name', 'N/A')}
- Account Number: {account_info.get('account_number', 'N/A')}
- Account Type: {account_info.get('account_type', 'Not specified')}
- Balance: ${account_info.get('balance', 'N/A')}
- Dispute Reason: {account_info.get('reason', 'N/A')}
"""

    if account_info.get('notes'):
        prompt += f"- Additional Details: {account_info['notes']}\n"

    prompt += """
REQUIREMENTS:
1. Write a formal business letter in a professional tone
2. Cite the Fair Credit Reporting Act (FCRA) rights
3. Clearly state what is being disputed and why
4. Request investigation and correction within 30 days
5. Request written confirmation of results
6. Be firm but respectful
7. Keep it concise (300-500 words)
8. Include proper letter structure (date, recipient, body, closing)
9. Use "To Whom It May Concern:" as greeting
10. Sign off with "Sincerely,"

DO NOT include:
- Sender's personal information in the body (will be added separately)
- Threats or aggressive language
- Irrelevant information
- Legal jargon that's too complex

Generate ONLY the letter body. Start with today's date and the bureau address."""

    try:
        # Call Ollama API
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 600  # Limit response length
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            print(f"Ollama API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error generating letter with Ollama: {e}")
        return None

def generate_dispute_letter_ai(account_info: dict, personal_info: dict = None) -> str:
    """
    Generate a personalized credit dispute letter using AI
    Tries Ollama first (free, local), falls back to OpenAI if needed
    
    Args:
        account_info: Dictionary with account details
            - bureau: Credit bureau name
            - creditor_name: Name of creditor
            - account_number: Account number
            - reason: Dispute reason
            - account_type: Type of account (optional)
            - balance: Account balance (optional)
            - notes: Additional notes (optional)
        personal_info: Dictionary with sender details (optional)
            - name: Full name
            - address: Street address
            - city: City
            - state: State
            - zip: ZIP code
    
    Returns:
        Generated letter text
    """
    
    # Try Ollama first (local, free)
    print("🤖 Generating letter with Ollama...")
    letter = generate_dispute_letter_ollama(account_info, personal_info)
    
    if letter:
        print("✅ Letter generated successfully with Ollama!")
        return letter
    
    # Fallback to OpenAI if Ollama fails
    client = get_openai_client()
    if not client:
        print("⚠️  No AI available (Ollama failed, OpenAI key not set)")
        return None
    
    print("🔄 Falling back to OpenAI GPT-4...")
    
    # Build the prompt (same as Ollama)
    prompt = f"""You are an expert credit repair specialist. Generate a professional, legally-compliant credit dispute letter.

ACCOUNT INFORMATION:
- Credit Bureau: {account_info.get('bureau', 'N/A')}
- Creditor: {account_info.get('creditor_name', 'N/A')}
- Account Number: {account_info.get('account_number', 'N/A')}
- Account Type: {account_info.get('account_type', 'Not specified')}
- Balance: ${account_info.get('balance', 'N/A')}
- Dispute Reason: {account_info.get('reason', 'N/A')}
"""

    if account_info.get('notes'):
        prompt += f"- Additional Details: {account_info['notes']}\n"

    prompt += """
REQUIREMENTS:
1. Write a formal business letter in a professional tone
2. Cite the Fair Credit Reporting Act (FCRA) rights
3. Clearly state what is being disputed and why
4. Request investigation and correction
5. Request written confirmation of results
6. Be firm but respectful
7. Keep it concise (300-500 words)
8. Include proper letter structure (date, recipient, body, closing)
9. Use "Dear Sir or Madam" as greeting
10. Sign off with "Sincerely,"

DO NOT include:
- Sender's personal information in the body (will be added separately)
- Threats or aggressive language
- Irrelevant information
- Legal jargon that's too complex

Generate ONLY the letter body. Start with the date line."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using gpt-4o-mini for cost efficiency
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional credit repair specialist who writes effective, legally-compliant dispute letters. Your letters are clear, firm, and always get results."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,  # Slight creativity but mostly consistent
            max_tokens=800
        )
        
        letter_content = response.choices[0].message.content.strip()
        return letter_content
        
    except Exception as e:
        # Fallback to template if AI fails
        print(f"AI generation failed: {e}")
        return generate_fallback_letter(account_info)


def generate_dispute_letter_premium(account_info: dict, personal_info: dict = None, custom_instructions: str = "") -> str:
    """
    Generate a premium letter using GPT-4 with custom instructions
    This is the paid tier - higher quality, customizable output
    
    Args:
        account_info: Dictionary with account details
        personal_info: Dictionary with sender details (optional)
        custom_instructions: Custom prompt modifications (tone, emphasis, details)
    
    Returns:
        Generated letter text
    """
    client = get_openai_client()
    if not client:
        print("❌ OpenAI API key not configured!")
        return None
    
    print("✨ Generating PREMIUM letter with GPT-4...")
    
    # Build enhanced prompt with custom instructions
    prompt = f"""You are an expert credit repair specialist. Generate a professional, legally-compliant credit dispute letter.

ACCOUNT INFORMATION:
- Credit Bureau: {account_info.get('bureau', 'N/A')}
- Creditor: {account_info.get('creditor_name', 'N/A')}
- Account Number: {account_info.get('account_number', 'N/A')}
- Account Type: {account_info.get('account_type', 'Not specified')}
- Balance: ${account_info.get('balance', 'N/A')}
- Dispute Reason: {account_info.get('reason', 'N/A')}
"""

    if account_info.get('notes'):
        prompt += f"- Additional Details: {account_info['notes']}\n"

    # Add custom instructions
    if custom_instructions:
        prompt += f"\nCUSTOM REQUIREMENTS:\n{custom_instructions}\n"

    prompt += """
STANDARD REQUIREMENTS:
1. Write a formal business letter
2. Cite the Fair Credit Reporting Act (FCRA) rights
3. Clearly state what is being disputed and why
4. Request investigation and correction
5. Request written confirmation of results
6. Include proper letter structure (date, recipient, body, closing)
7. Use "Dear Sir or Madam" as greeting
8. Sign off with "Sincerely,"

DO NOT include:
- Sender's personal information in the body (will be added separately)
- Threats or aggressive language
- Irrelevant information

Generate ONLY the letter body. Start with the date line."""

    try:
        response = client.chat.completions.create(
            model="gpt-4",  # Premium GPT-4 for best quality
            messages=[
                {
                    "role": "system",
                    "content": "You are an elite credit repair specialist with 20+ years experience. Your letters are meticulously crafted, legally bulletproof, and highly effective. You adapt your writing style based on client needs while maintaining professionalism."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,  # Higher creativity for premium tier
            max_tokens=1000  # Allow longer, more detailed letters
        )
        
        letter_content = response.choices[0].message.content.strip()
        print("✅ Premium letter generated successfully!")
        return letter_content
        
    except Exception as e:
        print(f"❌ Premium generation failed: {e}")
        return None


def generate_fallback_letter(account_info: dict) -> str:
    """
    Fallback template if AI generation fails
    """
    from datetime import datetime
    
    today = datetime.now().strftime("%B %d, %Y")
    
    return f"""{today}

{account_info['bureau']}
P.O. Box [Bureau Address]
[City, State ZIP]

Dear Sir or Madam:

I am writing to dispute the following information in my credit file. The items I dispute are inaccurate and I am requesting that they be removed or corrected.

DISPUTED ACCOUNT DETAILS:
Creditor: {account_info['creditor_name']}
Account Number: {account_info['account_number']}
Dispute Reason: {account_info['reason']}

Under the Fair Credit Reporting Act (FCRA), you are required to investigate and verify the accuracy of this information within 30 days of receiving this letter. If you cannot verify this information, it must be removed from my credit report immediately.

I am requesting a complete investigation of this matter and written confirmation of the results. If this information is found to be inaccurate, I expect it to be deleted from my credit report and all inquirers from the past six months to be notified of the deletion.

I am also requesting a copy of the documents used to verify this disputed information. Please send your response to the address on file.

Thank you for your prompt attention to this matter.

Sincerely,

[Signature will be added]
"""


def generate_followup_letter_ai(original_dispute: dict, escalation_level: int = 1) -> str:
    """
    Generate an escalation/follow-up letter using AI
    
    Args:
        original_dispute: Original dispute information
        escalation_level: 1 = first follow-up, 2 = second follow-up, 3+ = final demand
    
    Returns:
        Generated follow-up letter text
    """
    
    escalation_tone = {
        1: "polite but firm reminder",
        2: "more assertive follow-up",
        3: "final demand with legal references"
    }
    
    tone = escalation_tone.get(escalation_level, escalation_tone[3])
    
    prompt = f"""You are a credit repair specialist. Generate a {tone} follow-up letter for a credit dispute that has not received a response.

ORIGINAL DISPUTE:
- Bureau: {original_dispute.get('bureau')}
- Creditor: {original_dispute.get('creditor_name')}
- Account: {original_dispute.get('account_number')}
- Sent Date: {original_dispute.get('sent_date')}
- Days Since Sent: {original_dispute.get('days_since_sent', 30)} days

This is follow-up #{escalation_level}.

REQUIREMENTS:
1. Reference the original dispute and date sent
2. Note that {original_dispute.get('days_since_sent', 30)} days have passed
3. Cite FCRA requirement for 30-day response
4. {"Request immediate response" if escalation_level < 3 else "State intention to file complaint with CFPB if no response"}
5. Maintain professional tone but be {"firm" if escalation_level < 3 else "assertive and include legal consequences"}
6. Keep it concise (200-400 words)

Generate ONLY the letter body starting with the date."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a credit repair specialist handling follow-up correspondence. Your letters are professional, firm, and cite relevant laws."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=600
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"AI generation failed: {e}")
        return generate_fallback_followup(original_dispute, escalation_level)


def generate_fallback_followup(dispute: dict, escalation_level: int) -> str:
    """Fallback template for follow-up letters"""
    from datetime import datetime
    
    today = datetime.now().strftime("%B %d, %Y")
    
    if escalation_level >= 3:
        warning = """
I am prepared to file a complaint with the Consumer Financial Protection Bureau (CFPB) and my state Attorney General's office regarding your failure to comply with federal law. I expect an immediate response to avoid further action."""
    else:
        warning = "I expect a response within 15 days of receiving this letter."
    
    return f"""{today}

{dispute['bureau']}
P.O. Box [Bureau Address]
[City, State ZIP]

Re: Follow-up #{escalation_level} - Disputed Account #{dispute['account_number']}

Dear Sir or Madam:

This is my {"second" if escalation_level == 2 else "third" if escalation_level == 3 else "follow-up"} request regarding the disputed information in my credit file. I sent my original dispute letter on {dispute.get('sent_date', 'N/A')}, which was {dispute.get('days_since_sent', 'over 30')} days ago.

Under the Fair Credit Reporting Act (15 U.S.C. § 1681), you are required to investigate disputes within 30 days. To date, I have not received any response or confirmation of your investigation.

DISPUTED ACCOUNT:
Creditor: {dispute['creditor_name']}
Account Number: {dispute['account_number']}

I am formally requesting:
1. Immediate investigation of this disputed item
2. Written confirmation of your findings
3. Deletion of inaccurate information if it cannot be verified

{warning}

Sincerely,

[Signature will be added]
"""


# Test function
if __name__ == "__main__":
    # Test with sample data
    test_account = {
        'bureau': 'Experian',
        'creditor_name': 'Capital One',
        'account_number': '1234',
        'account_type': 'Credit Card',
        'balance': 1500.00,
        'reason': 'Not my account',
        'notes': 'I never opened this credit card account. This may be identity theft.'
    }
    
    print("Generating AI letter...")
    letter = generate_dispute_letter_ai(test_account)
    print(letter)
    print("\n" + "="*50 + "\n")
