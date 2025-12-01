# Security Guide for GitHub

## ✅ What's Protected

Your private details are now protected:

1. **Phone Number**: Moved to environment variable `ZEPTO_PHONE_NUMBER`
   - Not hardcoded in the code
   - Set in Claude Desktop config or `.env` file
   - `.env` is excluded from git

2. **Address Labels**: Moved to environment variable `ZEPTO_DEFAULT_ADDRESS` (optional)
   - No hardcoded default addresses
   - Can be provided per-order or set as default
   - Only in `.env` file (excluded from git) if set
   - Note: `ADDRESS_SELECTORS` dictionary contains example labels only (not your actual addresses)

3. **Browser Data**: All excluded from git
   - `zepto_browser_data/` - Contains cookies, sessions
   - `zepto_firefox_data/` - Contains saved passwords, cookies
   - All backup directories excluded

3. **Login Sessions**: Stored locally only
   - Never committed to git
   - Only on your local machine

## 📋 Before Pushing to GitHub

### 1. Verify .gitignore is working

```bash
cd /Users/Pranav_1/zepto-mcp
git status
```

You should NOT see:
- ❌ `zepto_browser_data/`
- ❌ `zepto_firefox_data/`
- ❌ `.env`
- ❌ Any backup directories

### 2. Check for hardcoded phone numbers

```bash
grep -r "9959547700" . --exclude-dir=.git
```

Should only show:
- ✅ `.env.example` (example file, safe)
- ✅ This SECURITY.md file (documentation, safe)
- ✅ `zepto_automation.py` (placeholder, safe)

### 3. Review what will be committed

```bash
git add .
git status
```

Review the list - make sure no sensitive files are included.

## 🔒 Safe to Commit

✅ **Safe files:**
- `zepto_mcp_server.py` - Main code (no hardcoded credentials)
- `setup_firefox_login.py` - Setup script
- `zepto_automation.py` - Automation code (has placeholder)
- `zepto_cafe_scraper.py` - Scraper code
- `README.md` - Documentation
- `.gitignore` - Git ignore rules
- `.env.example` - Example config (no real data)
- `*.md` - Documentation files

## ⚠️ Never Commit

❌ **Never commit:**
- `.env` - Your actual phone number
- `zepto_browser_data/` - Browser cookies/sessions
- `zepto_firefox_data/` - Saved passwords/cookies
- Any backup directories
- `__pycache__/` - Python cache

## 🚀 Initial Git Setup

If this is a new repository:

```bash
cd /Users/Pranav_1/zepto-mcp
git init
git add .gitignore README.md SECURITY.md *.py *.md
git add .env.example
git status  # Review what will be committed
git commit -m "Initial commit: Zepto MCP Server"
```

## 📝 Claude Desktop Config

Update your Claude Desktop config to use environment variable:

```json
{
  "mcpServers": {
    "zepto-cafe": {
      "command": "python3",
      "args": ["/Users/Pranav_1/zepto-mcp/zepto_mcp_server.py"],
      "env": {
        "ZEPTO_PHONE_NUMBER": "your_phone_number_here"
      }
    }
  }
}
```

This way your phone number is in Claude Desktop config (local only), not in the code.

## ✅ Final Checklist

Before pushing:
- [ ] `.gitignore` exists and includes browser data directories
- [ ] No hardcoded phone numbers in code (except placeholders)
- [ ] `.env` file exists but is NOT committed
- [ ] Browser data directories are NOT in git
- [ ] README.md explains setup without exposing your data

