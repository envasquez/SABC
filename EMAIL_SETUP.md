# 📧 Email Setup Guide for SABC Password Reset

This guide will help you set up email functionality for the password reset feature. It's designed to be simple and use free Gmail SMTP.

## 🔧 Quick Setup (5 minutes)

### Step 1: Create a Gmail Account for the Club
1. Create a new Gmail account like `saustinbassclub@gmail.com`
2. This will be your "sender" email address

### Step 2: Generate App Password
1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Click "Security"
3. Enable "2-Step Verification" if not already enabled
4. Click "App Passwords"
5. Generate a new app password for "Mail"
6. **Save this password** - you'll need it for Step 3

### Step 3: Set Environment Variables

Add these environment variables to your deployment:

```bash
# Required for email to work
SMTP_USERNAME=saustinbassclub@gmail.com
SMTP_PASSWORD=your_16_character_app_password_here
FROM_EMAIL=noreply@saustinbc.com
WEBSITE_URL=https://your-domain.com

# Optional
CLUB_NAME="South Austin Bass Club"
```

## 🚀 For Digital Ocean Deployment

In your Digital Ocean App Platform:

1. Go to your app settings
2. Click "Environment Variables"
3. Add the variables listed above
4. Redeploy your app

## 🧪 Testing

Once configured, you can test by:

1. Go to `/forgot-password`
2. Enter a valid club member email
3. Check if email arrives (including spam folder)
4. Click the reset link and change password
5. Log in with new password

## 🛠️ Advanced Configuration

### Rate Limiting
- Users can only request 3 password resets per hour
- Tokens expire after 30 minutes
- All attempts are logged for security

### Security Features
- Secure token generation
- Email enumeration protection
- Failed attempt logging
- IP address tracking

## 📋 What Members Will Experience

### For Non-Tech-Savvy Members:
1. **Simple Process**: Click "Forgot Password" → Enter email → Check email
2. **Clear Instructions**: Step-by-step guidance with friendly language
3. **Help Page**: Available at `/reset-password/help`
4. **Mobile Friendly**: Works on phones and tablets
5. **Large Buttons**: Easy to click for older users

### Email Content:
- **Plain English**: No technical jargon
- **Clear Call-to-Action**: Big "Reset My Password" button
- **Time Limit Warning**: Shows when link expires
- **Help Information**: What to do if they need assistance

## ⚠️ Troubleshooting

### Email Not Sending?
- Check SMTP credentials are correct
- Verify Gmail App Password (not regular password)
- Check app logs for error messages

### Users Not Receiving Emails?
- Check spam/junk folders
- Verify email addresses in member database
- Try different email providers (Gmail, Yahoo, etc.)

### Rate Limited?
- Users can only request 3 resets per hour
- This prevents abuse and spam

## 📞 Support for Members

If members have trouble:
1. Direct them to `/reset-password/help`
2. Check their email address in admin panel
3. Ask them to check spam folder
4. Try from a different browser
5. As last resort, admin can manually reset their password

## 🔒 Security Notes

- All password reset attempts are logged
- Tokens are single-use and expire quickly
- Rate limiting prevents abuse
- Email enumeration attacks are prevented
- IP addresses are tracked for security auditing

---

**✅ Once configured, the password reset system will work automatically and help your members regain access to their accounts easily!**
