"""
Test script for cart clearing functionality.
This script will:
1. Open a browser with persistent context (to use existing login)
2. Navigate to product pages
3. Add items to cart (with quantities > 1 to test quantity reduction)
4. Test the cart clearing function
"""

import asyncio
from playwright.async_api import async_playwright
import os

# Import the cart clearing function from the MCP server
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zepto_mcp_server import clear_cart_if_needed

async def test_cart_clearing():
    """Test the cart clearing functionality"""
    
    # Use the same persistent context directory as the MCP server
    user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zepto_browser_data")
    
    async with async_playwright() as p:
        # Launch browser with persistent context (to use existing login)
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-notifications",
                "--disable-infobars",
            ],
        )
        
        page = await context.new_page()
        
        # Handle dialogs
        page.on("dialog", lambda dialog: dialog.dismiss())
        
        print("🌐 Navigating to Zepto homepage...")
        await page.goto("https://www.zepto.com", wait_until="networkidle")
        await asyncio.sleep(2)
        
        # Check if logged in
        login_button = await page.query_selector('button:has-text("Login")')
        if login_button:
            print("⚠️ Not logged in. Please log in first using setup_login.py")
            print("   Or the cart clearing will be tested on an empty cart.")
        else:
            print("✅ Appears to be logged in")
        
        # Add some items to cart for testing
        print("\n📦 Adding items to cart for testing...")
        
        # Product URLs to add (you can modify these)
        test_products = [
            {
                "url": "https://www.zepto.com/pn/butter-chicken-steamed-bao/pvid/797fd5a2-c58e-4b47-9fb0-1b3e7c69235a",
                "name": "Butter Chicken Steamed Bao",
                "qty": 2  # Add 2 to test quantity reduction
            },
            {
                "url": "https://www.zepto.com/pn/chicken-puff/pvid/de23bbb3-a07f-46f1-91a2-a8171b514a33",
                "name": "Chicken Puff",
                "qty": 1
            },
            {
                "url": "https://www.zepto.com/pn/veg-steamed-pizza-bao/pvid/cf9fb663-e925-413e-99cd-4e49a06d2cd2",
                "name": "Veg Steamed Pizza Bao",
                "qty": 3  # Add 3 to test quantity reduction
            }
        ]
        
        for product in test_products:
            print(f"\n   Adding {product['name']} (qty: {product['qty']})...")
            await page.goto(product["url"], wait_until="networkidle")
            await asyncio.sleep(1.5)
            
            # Check if "Add To Cart" button exists
            add_to_cart = await page.query_selector("button.WJXJe:has-text('Add To Cart')")
            if not add_to_cart:
                print(f"      ⚠️ 'Add To Cart' button not found for {product['name']}")
                continue
            
            # Click "Add To Cart" once
            await page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll("button.WJXJe");
                    for (let btn of buttons) {
                        if (btn.textContent.includes('Add To Cart')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            await asyncio.sleep(1)
            
            # If quantity > 1, click + button (qty - 1) times
            if product['qty'] > 1:
                for i in range(product['qty'] - 1):
                    plus_btn = await page.query_selector("button[aria-label='Add']")
                    if plus_btn:
                        await plus_btn.click()
                        await asyncio.sleep(0.5)
                    else:
                        print(f"      ⚠️ Could not find + button for {product['name']}")
                        break
            
            print(f"      ✅ Added {product['qty']}x {product['name']}")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Check cart badge
        cart_badge = await page.query_selector('span[data-testid="cart-items-number"]')
        if cart_badge:
            badge_text = await cart_badge.text_content()
            print(f"\n🛒 Cart badge shows: {badge_text}")
        else:
            print("\n⚠️ No cart badge found - cart might be empty")
        
        # Now test the cart clearing function
        print("\n" + "="*60)
        print("🧪 TESTING CART CLEARING FUNCTION")
        print("="*60 + "\n")
        
        await clear_cart_if_needed(page)
        
        # Verify cart is empty
        await asyncio.sleep(1)
        cart_badge_after = await page.query_selector('span[data-testid="cart-items-number"]')
        if cart_badge_after:
            badge_text_after = await cart_badge_after.text_content()
            print(f"\n⚠️ Cart badge still shows: {badge_text_after}")
        else:
            print("\n✅ Cart badge removed - cart is empty!")
        
        print("\n" + "="*60)
        print("✅ TEST COMPLETE")
        print("="*60)
        
        # Keep browser open for manual inspection
        print("\n⏸️  Browser will stay open for 30 seconds for manual inspection...")
        print("   Press Ctrl+C to close early")
        try:
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            print("\n👋 Closing browser...")
        
        await context.close()


if __name__ == "__main__":
    print("🧪 Cart Clearing Test Script")
    print("="*60)
    print("This script will:")
    print("1. Open browser with persistent login")
    print("2. Add test items to cart (with quantities > 1)")
    print("3. Test the cart clearing function")
    print("4. Verify cart is empty")
    print("="*60 + "\n")
    
    asyncio.run(test_cart_clearing())


