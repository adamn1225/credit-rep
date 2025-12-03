"""
Email utility for sending verification and password reset emails
Uses Python's built-in smtplib (like nodemailer for Python)
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email(to_email, subject, html_body, text_body=None):
    """
    Send an email using SMTP (Gmail, Outlook, etc.)
    
    Environment Variables Required:
    - SMTP_HOST: smtp.gmail.com, smtp-mail.outlook.com, etc.
    - SMTP_PORT: 587 (TLS) or 465 (SSL)
    - SMTP_USER: your-email@gmail.com
    - SMTP_PASSWORD: your-app-password
    - FROM_EMAIL: sender email address
    """
    
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('FROM_EMAIL', smtp_user)
    
    if not smtp_user or not smtp_password:
        print("⚠️  SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD in .env")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add text and HTML parts
        if text_body:
            part1 = MIMEText(text_body, 'plain')
            msg.attach(part1)
        
        part2 = MIMEText(html_body, 'html')
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()  # Upgrade to secure connection
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Email send failed: {str(e)}")
        return False


def send_verification_email(email, token, app_url):
    """Send email verification link"""
    verification_url = f"{app_url}/verify-email?token={token}"
    
    subject = "Verify Your Email - Next Credit"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Next Credit</h1>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Verify Your Email Address</h2>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Thank you for signing up! Please verify your email address to unlock full access to:
                </p>
                
                <ul style="color: #666; font-size: 16px; line-height: 1.8;">
                    <li>✅ AI-powered dispute letter generation</li>
                    <li>✅ Send letters via certified mail (Lob API)</li>
                    <li>✅ Document analysis and tracking</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background: #667eea; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                
                <p style="color: #999; font-size: 14px; margin-top: 30px;">
                    Or copy this link: <br>
                    <code style="background: #e9ecef; padding: 5px 10px; border-radius: 3px; display: inline-block; margin-top: 10px;">{verification_url}</code>
                </p>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    This link expires in 24 hours. If you didn't create an account, please ignore this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
    Next Credit - Verify Your Email
    
    Thank you for signing up!
    
    Please verify your email address by clicking this link:
    {verification_url}
    
    This link expires in 24 hours.
    
    If you didn't create an account, please ignore this email.
    """
    
    return send_email(email, subject, html_body, text_body)


def send_password_reset_email(email, token, app_url):
    """Send password reset link"""
    reset_url = f"{app_url}/reset-password?token={token}"
    
    subject = "Reset Your Password - Next Credit"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Next Credit</h1>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Reset Your Password</h2>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    We received a request to reset your password. Click the button below to create a new password:
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background: #667eea; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p style="color: #999; font-size: 14px; margin-top: 30px;">
                    Or copy this link: <br>
                    <code style="background: #e9ecef; padding: 5px 10px; border-radius: 3px; display: inline-block; margin-top: 10px;">{reset_url}</code>
                </p>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    This link expires in 1 hour. If you didn't request a password reset, please ignore this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
    Next Credit - Reset Your Password
    
    We received a request to reset your password.
    
    Click this link to create a new password:
    {reset_url}
    
    This link expires in 1 hour.
    
    If you didn't request a password reset, please ignore this email.
    """
    
    return send_email(email, subject, html_body, text_body)


def send_welcome_email(email, first_name):
    """Send welcome email after verification"""
    subject = "Welcome to Next Credit! 🎉"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">✅ Email Verified!</h1>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Welcome, {first_name}!</h2>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Your email has been verified and you now have full access to all features:
                </p>
                
                <ul style="color: #666; font-size: 16px; line-height: 1.8;">
                    <li>✅ AI Letter Generation (OpenAI GPT-4)</li>
                    <li>✅ Certified Mail Sending (Lob API)</li>
                    <li>✅ Document Analysis</li>
                    <li>✅ Dispute Tracking</li>
                </ul>
                
                <div style="background: #e7f3ff; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; border-radius: 5px;">
                    <p style="color: #0c5460; margin: 0; font-weight: bold;">
                        👉 Next Steps:
                    </p>
                    <ol style="color: #0c5460; margin: 10px 0 0 0; padding-left: 20px;">
                        <li>Upload your credit reports</li>
                        <li>Add derogatory accounts</li>
                        <li>Generate AI dispute letters</li>
                        <li>Send via certified mail</li>
                    </ol>
                </div>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Questions? Reply to this email or contact support.
                </p>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
    Welcome to Next Credit, {first_name}!
    
    Your email has been verified! You now have full access to:
    - AI Letter Generation (OpenAI GPT-4)
    - Certified Mail Sending (Lob API)
    - Document Analysis
    - Dispute Tracking
    
    Next Steps:
    1. Upload your credit reports
    2. Add derogatory accounts
    3. Generate AI dispute letters
    4. Send via certified mail
    
    Questions? Reply to this email or contact support.
    """
    
    return send_email(email, subject, html_body, text_body)
