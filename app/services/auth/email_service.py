"""
Email Service for User Notifications
===================================
Handles sending welcome emails, login notifications, and password reset emails.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import aiosmtplib
from typing import Optional
from app.config import settings


class EmailService:
    def __init__(self):
        self.smtp_server = getattr(settings, 'smtp_server', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_username = getattr(settings, 'smtp_username', None)
        self.smtp_password = getattr(settings, 'smtp_password', None)
        self.from_email = getattr(settings, 'from_email', self.smtp_username)
        self.from_name = getattr(settings, 'from_name', 'StoryTeller App')
        self.enabled = getattr(settings, 'email_enabled', False)

    async def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None):
        """
        Send an email using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
        """
        try:
            if not self.enabled or not self.smtp_username or not self.smtp_password:
                print("⚠️ Email service not configured - skipping email send")
                return False

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add text content
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_username,
                password=self.smtp_password,
            )

            print(f"✅ Email sent successfully to {to_email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_welcome_email(self, user_email: str, user_name: str = None):
        """
        Send welcome email to new users
        
        Args:
            user_email: User's email address
            user_name: User's display name (optional)
        """
        subject = "Welcome to StoryTeller! 🎉"
        
        display_name = user_name if user_name else user_email.split('@')[0]
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #4A90E2; margin: 0; font-size: 28px; }}
                .header p {{ color: #666; font-size: 16px; margin: 10px 0 0 0; }}
                .content {{ color: #333; line-height: 1.6; }}
                .feature {{ background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #4A90E2; }}
                .cta {{ text-align: center; margin: 30px 0; }}
                .button {{ display: inline-block; background-color: #4A90E2; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to StoryTeller!</h1>
                    <p>Your magical storytelling adventure begins now</p>
                </div>
                
                <div class="content">
                    <p>Hi {display_name},</p>
                    
                    <p>Welcome to StoryTeller! We're thrilled to have you join our community of storytellers and dreamers.</p>
                    
                    <p>With StoryTeller, you can:</p>
                    
                    <div class="feature">
                        <strong>🎭 Create Personalized Stories</strong><br>
                        Generate unique, age-appropriate stories tailored to your child's interests and moral values.
                    </div>
                    
                    <div class="feature">
                        <strong>🎨 Beautiful Illustrations</strong><br>
                        Every story comes with custom illustrations that bring your tales to life.
                    </div>
                    
                    <div class="feature">
                        <strong>🎤 Voice Cloning</strong><br>
                        Use your own voice to narrate stories, creating a more personal experience for your child.
                    </div>
                    
                    <div class="feature">
                        <strong>📱 Multi-Device Access</strong><br>
                        Access your stories from any device, anytime, anywhere.
                    </div>
                    
                    <p>Ready to create your first story? Simply open the app and let your imagination run wild!</p>
                    
                    <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
                    
                    <p>Happy storytelling!<br>
                    The StoryTeller Team</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 StoryTeller App. All rights reserved.</p>
                    <p>You're receiving this email because you just signed up for StoryTeller.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to StoryTeller! 🎉
        
        Hi {display_name},
        
        Welcome to StoryTeller! We're thrilled to have you join our community of storytellers and dreamers.
        
        With StoryTeller, you can:
        
        🎭 Create Personalized Stories - Generate unique, age-appropriate stories tailored to your child's interests and moral values.
        🎨 Beautiful Illustrations - Every story comes with custom illustrations that bring your tales to life.
        🎤 Voice Cloning - Use your own voice to narrate stories, creating a more personal experience for your child.
        📱 Multi-Device Access - Access your stories from any device, anytime, anywhere.
        
        Ready to create your first story? Simply open the app and let your imagination run wild!
        
        If you have any questions or need help getting started, don't hesitate to reach out to our support team.
        
        Happy storytelling!
        The StoryTeller Team
        
        © 2025 StoryTeller App. All rights reserved.
        You're receiving this email because you just signed up for StoryTeller.
        """
        
        await self.send_email(user_email, subject, html_content, text_content)

    async def send_login_notification(self, user_email: str, user_name: str = None, login_time: datetime = None, device_info: str = None):
        """
        Send login notification email
        
        Args:
            user_email: User's email address
            user_name: User's display name (optional)
            login_time: Login timestamp (optional)
            device_info: Device/browser information (optional)
        """
        subject = "New Login to Your StoryTeller Account"
        
        display_name = user_name if user_name else user_email.split('@')[0]
        login_datetime = login_time if login_time else datetime.utcnow()
        formatted_time = login_datetime.strftime("%B %d, %Y at %I:%M %p UTC")
        device_text = f" from {device_info}" if device_info else ""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #4A90E2; margin: 0; font-size: 24px; }}
                .content {{ color: #333; line-height: 1.6; }}
                .login-info {{ background-color: #e8f4fd; padding: 20px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #4A90E2; }}
                .security-note {{ background-color: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #ffc107; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Login Notification</h1>
                </div>
                
                <div class="content">
                    <p>Hi {display_name},</p>
                    
                    <p>We wanted to let you know that someone just logged into your StoryTeller account.</p>
                    
                    <div class="login-info">
                        <strong>Login Details:</strong><br>
                        📅 Time: {formatted_time}<br>
                        🔍 Account: {user_email}{device_text}
                    </div>
                    
                    <p>If this was you, you can safely ignore this email.</p>
                    
                    <div class="security-note">
                        <strong>⚠️ Didn't log in?</strong><br>
                        If you didn't authorize this login, please change your password immediately and contact our support team.
                    </div>
                    
                    <p>Thank you for keeping your account secure.</p>
                    
                    <p>Best regards,<br>
                    The StoryTeller Team</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 StoryTeller App. All rights reserved.</p>
                    <p>This is a security notification for your StoryTeller account.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Login Notification - StoryTeller Account
        
        Hi {display_name},
        
        We wanted to let you know that someone just logged into your StoryTeller account.
        
        Login Details:
        Time: {formatted_time}
        Account: {user_email}{device_text}
        
        If this was you, you can safely ignore this email.
        
        ⚠️ Didn't log in?
        If you didn't authorize this login, please change your password immediately and contact our support team.
        
        Thank you for keeping your account secure.
        
        Best regards,
        The StoryTeller Team
        
        © 2025 StoryTeller App. All rights reserved.
        This is a security notification for your StoryTeller account.
        """
        
        await self.send_email(user_email, subject, html_content, text_content)

    async def send_password_reset_email(self, user_email: str, reset_token: str, user_name: str = None):
        """
        Send password reset email
        
        Args:
            user_email: User's email address
            reset_token: Password reset token
            user_name: User's display name (optional)
        """
        subject = "Reset Your StoryTeller Password"
        
        display_name = user_name if user_name else user_email.split('@')[0]
        
        # Use Expo default development URL for password reset
        reset_url = f"exp://localhost:19000/--/reset-password?token={reset_token}&email={user_email}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #4A90E2; margin: 0; font-size: 24px; }}
                .content {{ color: #333; line-height: 1.6; }}
                .cta {{ text-align: center; margin: 30px 0; }}
                .button {{ display: inline-block; background-color: #4A90E2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px; }}
                .security-note {{ background-color: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #ffc107; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔑 Reset Your Password</h1>
                </div>
                
                <div class="content">
                    <p>Hi {display_name},</p>
                    
                    <p>We received a request to reset your StoryTeller account password. Click the button below to create a new password:</p>
                    
                    <div class="cta">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </div>
                    
                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{reset_url}</p>
                    
                    <div class="security-note">
                        <strong>⚠️ Important:</strong><br>
                        This password reset link will expire in 1 hour for security reasons. If you didn't request this reset, you can safely ignore this email.
                    </div>
                    
                    <p>If you're having trouble or didn't request this reset, please contact our support team.</p>
                    
                    <p>Best regards,<br>
                    The StoryTeller Team</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 StoryTeller App. All rights reserved.</p>
                    <p>This is a password reset notification for your StoryTeller account.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Reset Your StoryTeller Password
        
        Hi {display_name},
        
        We received a request to reset your StoryTeller account password. 
        
        To reset your password, visit this link:
        {reset_url}
        
        ⚠️ Important:
        This password reset link will expire in 1 hour for security reasons. If you didn't request this reset, you can safely ignore this email.
        
        If you're having trouble or didn't request this reset, please contact our support team.
        
        Best regards,
        The StoryTeller Team
        
        © 2025 StoryTeller App. All rights reserved.
        This is a password reset notification for your StoryTeller account.
        """
        
        await self.send_email(user_email, subject, html_content, text_content)
    
    async def send_password_reset_otp_email(self, user_email: str, otp_code: str, user_name: Optional[str] = None, expiry_minutes: int = 10):
        """
        Send a password reset OTP email
        
        Args:
            user_email: User's email address
            otp_code: 6-digit OTP code
            user_name: User's display name (optional)
            expiry_minutes: OTP expiry time in minutes
        """
        if not self.enabled:
            print("⚠️ Email service is disabled - OTP email not sent")
            return
        
        display_name = user_name if user_name else "StoryTeller User"
        subject = "Your StoryTeller Password Reset Code"
        
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #4A90E2; margin: 0; font-size: 24px; }}
                .content {{ color: #333; line-height: 1.6; }}
                .otp-box {{ background-color: #e8f4fd; padding: 30px; margin: 30px 0; border-radius: 10px; text-align: center; border: 2px dashed #4A90E2; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #4A90E2; letter-spacing: 8px; margin: 15px 0; font-family: 'Courier New', monospace; }}
                .security-note {{ background-color: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #ffc107; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .expiry {{ color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Code</h1>
                </div>
                
                <div class="content">
                    <p>Hi {display_name},</p>
                    
                    <p>We received a request to reset your StoryTeller account password. Use the verification code below to proceed with resetting your password:</p>
                    
                    <div class="otp-box">
                        <div>Your verification code is:</div>
                        <div class="otp-code">{otp_code}</div>
                        <div class="expiry">Expires in {expiry_minutes} minutes</div>
                    </div>
                    
                    <p>Enter this code in the StoryTeller app to create your new password.</p>
                    
                    <div class="security-note">
                        <strong>⚠️ Important:</strong><br>
                        • This code will expire in {expiry_minutes} minutes for security reasons<br>
                        • Do not share this code with anyone<br>
                        • If you didn't request this reset, you can safely ignore this email
                    </div>
                    
                    <p>If you're having trouble or didn't request this reset, please contact our support team.</p>
                    
                    <p>Best regards,<br>
                    The StoryTeller Team</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 StoryTeller App. All rights reserved.</p>
                    <p>This is a password reset notification for your StoryTeller account.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Your StoryTeller Password Reset Code
        
        Hi {display_name},
        
        We received a request to reset your StoryTeller account password. 
        
        Your verification code is: {otp_code}
        
        This code expires in {expiry_minutes} minutes.
        
        Enter this code in the StoryTeller app to create your new password.
        
        ⚠️ Important:
        • This code will expire in {expiry_minutes} minutes for security reasons
        • Do not share this code with anyone
        • If you didn't request this reset, you can safely ignore this email
        
        If you're having trouble or didn't request this reset, please contact our support team.
        
        Best regards,
        The StoryTeller Team
        
        © 2025 StoryTeller App. All rights reserved.
        This is a password reset notification for your StoryTeller account.
        """
        
        await self.send_email(user_email, subject, html_content, text_content)


# Global email service instance
email_service = EmailService()
