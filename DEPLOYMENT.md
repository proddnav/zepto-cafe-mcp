# Zepto Cafe Cloud Deployment Guide

Deploy your Zepto Cafe ordering bot to the cloud with Telegram integration via n8n.

## Architecture

```
Telegram Bot → n8n (AI parsing) → Zepto API Server (Railway) → Zepto Website
```

## Prerequisites

1. **Railway account** - https://railway.app (free tier available)
2. **n8n instance** - Self-hosted or n8n.cloud
3. **Telegram Bot** - Create via @BotFather
4. **OpenAI API key** - For order parsing

---

## Step 1: Deploy to Railway

### Option A: One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/zepto-cafe)

### Option B: Manual Deploy

1. **Push to GitHub**
   ```bash
   cd zepto-cafe-mcp
   git add .
   git commit -m "Add cloud deployment files"
   git push origin main
   ```

2. **Create Railway Project**
   - Go to https://railway.app/new
   - Select "Deploy from GitHub repo"
   - Choose your `zepto-cafe-mcp` repository

3. **Configure Environment Variables**
   In Railway dashboard → Variables, add:
   ```
   ZEPTO_PHONE_NUMBER=your_phone_number
   ZEPTO_DEFAULT_ADDRESS=Hsr Home
   PORT=8000
   ```

4. **Deploy**
   - Railway auto-deploys on push
   - Wait for build to complete (~3-5 minutes)
   - Copy your Railway URL: `https://your-app.railway.app`

---

## Step 2: Set Up Browser Session

**Important**: The Zepto automation requires a logged-in browser session. For cloud deployment:

### Option A: Pre-authenticated Docker Image (Recommended)

1. Run locally first to create session:
   ```bash
   python setup_firefox_login.py
   ```

2. The `zepto_firefox_data/` directory contains your session.

3. In Railway, use a persistent volume:
   - Settings → Volumes → Add Volume
   - Mount path: `/app/zepto_firefox_data`

### Option B: Session via API

The first order will require OTP authentication:
1. Start an order via API/Telegram
2. System will pause and request OTP
3. Submit OTP via `/otp/login` endpoint
4. Session is saved for future orders

---

## Step 3: Create Telegram Bot

1. **Create Bot**
   - Open Telegram, search for `@BotFather`
   - Send `/newbot`
   - Choose a name: `Zepto Cafe Bot`
   - Choose username: `your_zepto_bot`
   - Save the **API token**

2. **Configure Bot**
   ```
   /setdescription - Order from Zepto Cafe via Telegram
   /setcommands -
   order - Place a new order
   status - Check order status
   cancel - Cancel current order
   help - Show help
   ```

---

## Step 4: Set Up n8n Workflow

### Import the Workflow

1. Open your n8n instance
2. Go to **Workflows** → **Import from File**
3. Upload `n8n_telegram_workflow.json`

### Configure Credentials

1. **Telegram Bot**
   - Settings → Credentials → Add Credential
   - Type: Telegram
   - Access Token: Your bot token from BotFather

2. **OpenAI API**
   - Settings → Credentials → Add Credential
   - Type: OpenAI
   - API Key: Your OpenAI API key

### Set Environment Variables

In n8n Settings → Variables, add:
```
ZEPTO_API_URL=https://your-app.railway.app
```

### Activate the Workflow

1. Open the imported workflow
2. Update credential references in each node
3. Click **Save**
4. Toggle **Active** to ON

---

## Step 5: Test the Integration

1. **Send message to your Telegram bot**:
   ```
   Order 2 iced americano and 1 croissant
   ```

2. **Expected flow**:
   - n8n receives message
   - AI parses order items
   - API server starts browser automation
   - Bot confirms order started
   - If OTP needed, bot asks for it
   - Send OTP number directly
   - Order completes

3. **Check status**:
   ```
   status
   ```

4. **Cancel if needed**:
   ```
   cancel
   ```

---

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Railway health check |
| `/catalog` | GET | List available products |
| `/status` | GET | Current order status |
| `/order` | POST | Start single item order |
| `/order/multi` | POST | Start multi-item order |
| `/otp/login` | POST | Submit login OTP |
| `/otp/payment` | POST | Submit payment OTP |
| `/stop` | POST | Cancel current order |
| `/stock-decision` | POST | Handle out-of-stock items |

### Example: Start Order

```bash
curl -X POST https://your-app.railway.app/order/multi \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"product_name": "iced americano", "quantity": 2},
      {"product_name": "butter croissant", "quantity": 1}
    ],
    "address": "Hsr Home"
  }'
```

### Example: Submit OTP

```bash
curl -X POST https://your-app.railway.app/otp/login \
  -H "Content-Type: application/json" \
  -d '{"otp": "123456"}'
```

---

## Troubleshooting

### Browser Session Issues

**Problem**: Order fails with "not logged in"

**Solution**:
1. Check Railway logs for session errors
2. Re-run `setup_firefox_login.py` locally
3. Ensure persistent volume is mounted
4. First order after deploy needs OTP

### n8n Workflow Not Triggering

**Problem**: Telegram messages not processed

**Solution**:
1. Verify bot token is correct
2. Check webhook URL in Telegram settings
3. Ensure workflow is activated
4. Check n8n execution logs

### AI Parsing Errors

**Problem**: Orders not being parsed correctly

**Solution**:
1. Check OpenAI API key is valid
2. Review the AI prompt in the workflow
3. Add more product variations to prompt
4. Check for rate limiting

### Railway Deployment Fails

**Problem**: Build or deploy errors

**Solution**:
1. Check Railway build logs
2. Ensure Dockerfile is correct
3. Verify all dependencies in requirements.txt
4. Check for Playwright installation issues

---

## Cost Estimates

| Service | Free Tier | Paid |
|---------|-----------|------|
| Railway | $5 credit/month | $0.01/GB-hr |
| n8n Cloud | 5 workflows | $20/month |
| OpenAI | - | ~$0.001/order |
| **Total** | ~Free | ~$25/month |

---

## Security Notes

1. **Never commit `.env` files** with credentials
2. Use Railway's environment variables for secrets
3. The Zepto session contains authentication tokens - keep volume secure
4. Consider rate limiting API endpoints in production

---

## Support

- Issues: https://github.com/your-repo/issues
- n8n Community: https://community.n8n.io
- Railway Docs: https://docs.railway.app
