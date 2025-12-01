# Zepto MCP Server

Automated ordering system for Zepto Cafe using Playwright and MCP (Model Context Protocol).

## Features

- 🚀 Automated order placement
- 🔐 Persistent login sessions (saved in Firefox)
- 📦 Multi-item cart support
- ⚡ Optimized for speed (~35-65 seconds per order)
- 🎯 Address selection with fuzzy matching

## Setup

### 1. Install Dependencies

```bash
pip3 install playwright mcp python-dotenv
python3 -m playwright install firefox
```

**Note**: `python-dotenv` is optional - if not installed, the code will use environment variables from Claude Desktop config or system environment.

### 2. Configure Phone Number and Address

You have two options:

#### Option A: Use Claude Desktop Config (Recommended)

Add environment variables directly in Claude Desktop config (see Step 4 below). No `.env` file needed.

#### Option B: Use .env File (Optional)

If you want to use a `.env` file, create it (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your phone number and optional default address:

```
ZEPTO_PHONE_NUMBER=your_phone_number_here
ZEPTO_DEFAULT_ADDRESS=your_address_label_here  # Optional: e.g., 'Hsr Home', 'Office New Cafe'
```

**Note**: The code will automatically load `.env` if `python-dotenv` is installed. If not, it will use system environment variables or Claude Desktop config.

**Important**: Never commit `.env` to git - it contains sensitive information.

### 3. Set Up Login Session

Run the setup script to save your login:

```bash
python3 setup_firefox_login.py
```

This will:
1. Open Firefox
2. Navigate to Zepto
3. Wait for you to log in manually
4. Save your session for future orders

### 4. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zepto-cafe": {
      "command": "python3",
      "args": ["/Users/Pranav_1/zepto-mcp/zepto_mcp_server.py"],
      "env": {
        "ZEPTO_PHONE_NUMBER": "your_phone_number_here",
        "ZEPTO_DEFAULT_ADDRESS": "your_address_label_here"  # Optional
      }
    }
  }
}
```

## Usage

Once configured, you can order through Claude Desktop:

- "Order an iced americano to my office address"
- "Can you order a hazelnut latte from Zepto Cafe"
- "Order multiple items: hazelnut latte, almond croissant"

## Security

- ✅ Phone number stored in environment variable (not in code)
- ✅ Browser data directories excluded from git
- ✅ Login sessions stored locally (never committed)
- ✅ No API keys or secrets in code

## Files Structure

- `zepto_mcp_server.py` - Main MCP server
- `setup_firefox_login.py` - Login setup script
- `.env` - Your configuration (not in git)
- `zepto_firefox_data/` - Browser session data (not in git)

## Troubleshooting

If browser crashes:
1. Close all Firefox/Chrome windows
2. Delete `zepto_firefox_data/` directory
3. Run `setup_firefox_login.py` again

## License

MIT

