"""
SendGrid Email Service for Magic Link Authentication
"""
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@nextcredit.app')

def send_magic_link_email(to_email: str, magic_link: str, username: str = None) -> bool:
    """
    Send magic link email via SendGrid
    
    Args:
        to_email: Recipient email address
        magic_link: Full URL for magic link authentication
        username: Optional username for personalization
    
    Returns:
        bool: True if email sent successfully
    """
    if not SENDGRID_API_KEY or SENDGRID_API_KEY == 'your_sendgrid_api_key_here':
        print("⚠️ SendGrid API key not configured")
        return False
    
    greeting = f"Hi {username}," if username else "Hello,"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; padding: 15px 30px; background: #667eea; 
                      color: white; text-decoration: none; border-radius: 5px; 
                      font-weight: bold; margin: 20px 0; }}
            .button:hover {{ background: #764ba2; }}
            .footer {{ text-align: center; margin-top: 30px; color: #999; font-size: 12px; }}
            .security-notice {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                               padding: 15px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Login to Next Credit</h1>
            </div>
            <div class="content">
                <p>{greeting}</p>
                
                <p>Click the button below to securely log in to your Next Credit account:</p>
                
                <div style="text-align: center;">
                    <a href="{magic_link}" class="button">🔓 Login to Next Credit</a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="background: white; padding: 10px; border-radius: 5px; word-break: break-all;">
                    <code>{magic_link}</code>
                </p>
                
                <div class="security-notice">
                    <strong>⏰ Security Notice:</strong><br>
                    This login link will expire in 15 minutes for your security.
                    If you didn't request this login, you can safely ignore this email.
                </div>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>Next Credit Team</strong>
                </p>
            </div>
            <div class="footer">
                <p>© 2024 Next Credit. All rights reserved.</p>
                <p>This is an automated message, please do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    {greeting}
    
    Click the link below to securely log in to your Next Credit account:
    
    {magic_link}
    
    ⏰ This login link will expire in 15 minutes for your security.
    
    If you didn't request this login, you can safely ignore this email.
    
    Best regards,
    Next Credit Team
    
    ---
    © 2024 Next Credit. All rights reserved.
    """
    
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject='🔐 Your Next Credit Login Link',
        plain_text_content=plain_content,
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ Magic link email sent to {to_email}")
            return True
        else:
            logger.error(f"❌ SendGrid error: {response.status_code} - {response.body}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending magic link email: {str(e)}")
        return False


def send_welcome_email(to_email: str, username: str) -> bool:
    """
    Send welcome email to new user
    
    Args:
        to_email: Recipient email address
        username: Username for personalization
    
    Returns:
        bool: True if email sent successfully
    """
    if not SENDGRID_API_KEY or SENDGRID_API_KEY == 'your_sendgrid_api_key_here':
        logger.error("⚠️ SendGrid API key not configured")
        return False
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .footer {{ text-align: center; margin-top: 30px; color: #999; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Welcome to Next Credit!</h1>
            </div>
            <div class="content">
                <p>Hi {username},</p>
                
                <p>Welcome to Next Credit! Your account has been created successfully.</p>
                
                <p>Here's what you can do with Next Credit:</p>
                <ul>
                    <li>📋 Track and manage credit bureau disputes</li>
                    <li>🤖 Generate AI-powered dispute letters</li>
                    <li>📬 Send certified letters via Lob API</li>
                    <li>📊 Monitor your dispute progress and outcomes</li>
                </ul>
                
                <p>To log in, simply use your email address and we'll send you a secure login link.</p>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>Next Credit Team</strong>
                </p>
            </div>
            <div class="footer">
                <p>© 2024 Next Credit. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Hi {username},
    
    Welcome to Next Credit! Your account has been created successfully.
    
    Here's what you can do with Next Credit:
    - Track and manage credit bureau disputes
    - Generate AI-powered dispute letters
    - Send certified letters via Lob API
    - Monitor your dispute progress and outcomes
    
    To log in, simply use your email address and we'll send you a secure login link.
    
    Best regards,
    Next Credit Team
    
    ---
    © 2024 Next Credit. All rights reserved.
    """
    
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject='🎉 Welcome to Next Credit!',
        plain_text_content=plain_content,
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ Welcome email sent to {to_email}")
            return True
        else:
            logger.error(f"❌ SendGrid error: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending welcome email: {str(e)}")
        return False
