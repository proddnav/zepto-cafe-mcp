from playwright.sync_api import sync_playwright
import time


def scrape_product_links(category_url: str, scroll_pause: float = 2.0, max_scrolls: int = 50):
    """Scrape all product links from a Zepto category page (e.g. Cafe).

    Args:
        category_url: Full URL to the category page (copy from your browser).
        scroll_pause: Seconds to wait after each scroll to let items load.
        max_scrolls: Safety cap on how many times to scroll.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(category_url)
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        last_height = 0
        for _ in range(max_scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Product pages on Zepto typically contain `/pn/` in the URL, e.g.:
        # https://www.zepto.com/pn/iced-americano/pvid/...
        product_links = page.eval_on_selector_all(
            "a[href*='/pn/']",
            "elements => Array.from(new Set(elements.map(e => e.href)))"
        )

        for link in product_links:
            print(link)

        browser.close()


ADDRESS_SELECTORS = {
    "Hsr Home": "div.c4ZmYS:has-text('Hsr Home')",
    "Office New Cafe": "div.c4ZmYS:has-text('Office New Cafe')",
    "Hyd Home": "div.c4ZmYS:has-text('Hyd Home')",
}


def select_address(page, address_name: str):
    # Special handling: Jo's address requires scrolling inside the saved-addresses container
    if address_name.lower() in {"jo", "jo's address", "jo address"}:
        container = page.locator("div.fsVuP")
        target = page.locator(
            "span.line-clamp-2.break-all:has-text('1St Floor, Trillium Rose, JV Hills, Hyderabad')"
        )

        # Try scrolling down a few times until the address becomes visible
        for _ in range(20):
            if target.count() > 0 and target.first.is_visible():
                target.first.click()
                return
            if container.count() > 0:
                container.first.evaluate("el => { el.scrollTop = el.scrollTop + 400; }")
            time.sleep(0.5)

        # Fallback: try clicking even if not confirmed visible
        if target.count() > 0:
            target.first.click()
            return
        raise Exception("Jo's address not found in saved addresses list.")

    # All other known addresses can be clicked directly without extra scrolling
    selector = ADDRESS_SELECTORS.get(
        address_name, f"div.c4ZmYS:has-text('{address_name}')"
    )
    page.click(selector)


def login_and_order(phone_number, product_url, address_name=None):
    import os
    if address_name is None:
        address_name = os.getenv("ZEPTO_DEFAULT_ADDRESS", "Hsr Home")  # Fallback for testing
    """Complete flow: Login, Add to cart, Select address, Go to payment"""
    
    print(f"🚀 Starting Zepto order automation...")
    
    with sync_playwright() as p:
        # Launch browser (visible so you can enter OTP)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Step 1: Go to product page
        print("📱 Opening product page...")
        page.goto(product_url)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        
        # Step 2: Click Login button
        print("🔐 Clicking login...")
        page.click("span[data-testid='login-btn']")
        time.sleep(2)
        
        # Step 3: Enter phone number
        print(f"📞 Entering phone number: {phone_number}")
        page.fill("input[placeholder='Enter Phone Number']", phone_number)
        time.sleep(1)
        
        # Step 4: Click Continue button
        print("➡️  Clicking Continue...")
        page.click("button:has-text('Continue')")
        time.sleep(3)
        
        # Step 5: Wait for OTP - 25 seconds
        print("\n" + "="*60)
        print("⏸️  Waiting 25 seconds for OTP entry...")
        print("⏸️  Please enter the OTP in the browser window NOW")
        print("="*60 + "\n")
        
        time.sleep(25)
        
        print("▶️  Resuming automation...")
        
        # Step 6: Navigate to product page after login
        print("🔄 Loading product page after login...")
        page.goto(product_url)
        page.wait_for_load_state("networkidle")
        time.sleep(5)
        
        # Step 7: Close any popups if they exist
        try:
            page.click("button:has-text('Close')", timeout=2000)
        except:
            pass
        
        # Step 8: Wait for Add to Cart button
        print("⏳ Waiting for Add to Cart button...")
        page.wait_for_selector("button.WJXJe:has-text('Add To Cart')", timeout=15000)
        time.sleep(2)
        
        # Step 9: Scroll button into view
        print("📜 Scrolling to Add to Cart button...")
        page.evaluate("""
            const button = document.querySelector("button.WJXJe");
            if (button) {
                button.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        """)
        time.sleep(3)
        
        # Step 10: Click Add to Cart
        print("🛒 Adding item to cart...")
        page.evaluate("""
            const buttons = document.querySelectorAll("button.WJXJe");
            for (let btn of buttons) {
                if (btn.textContent.includes('Add To Cart')) {
                    btn.click();
                    break;
                }
            }
        """)
        time.sleep(4)
        print("✅ Item added!")
        
        # Step 11: Click Cart icon
        print("🛍️  Opening cart...")
        page.click("button[data-testid='cart-btn']")
        time.sleep(3)
        
        # Step 12: Click "Add Address to proceed"
        print("📍 Proceeding to address selection...")
        page.click("button:has-text('Add Address to proceed')")
        time.sleep(3)
        
        # Step 13: Select address
        print(f"🏠 Selecting address: {address_name}")
        select_address(page, address_name)
        time.sleep(2)
        
        # Step 14: Click "Click to Pay"
        print("💳 Proceeding to payment...")
        page.click("button:has-text('Click to Pay')")
        time.sleep(5)
        
        # Step 15: Select HDFC Bank Credit
        print("💳 Selecting HDFC Bank Credit payment...")
        page.click("article:has-text('HDFC Bank Credit')")
        time.sleep(3)
        
        # Step 16: Click "Proceed to Pay"
        print("✅ Clicking Proceed to Pay...")
        page.click("article:has-text('Proceed to Pay')")
        time.sleep(5)
        
        # Step 17: Wait for payment OTP page
        print("\n" + "="*60)
        print("⏸️  Waiting 30 seconds for PAYMENT OTP entry...")
        print("⏸️  Please enter the payment OTP in the browser NOW")
        print("="*60 + "\n")
        
        # Wait for OTP input field to appear
        try:
            page.wait_for_selector("input[name='otpValue']", timeout=10000)
            print("✅ Payment OTP field detected!")
        except:
            print("⚠️  OTP field not found, but continuing...")
        
        # Give user 30 seconds to enter payment OTP
        time.sleep(30)
        
        # Step 18: Click CONFIRM button
        print("✅ Clicking CONFIRM button...")
        page.click("button#submitBtn")
        time.sleep(5)
        
        print("\n" + "="*60)
        print("🎉 ORDER COMPLETE!")
        print("✅ Payment confirmed and order placed!")
        print("⏳ Browser will stay open for 30 more seconds...")
        print("="*60 + "\n")
        
        time.sleep(30)
        
        browser.close()
        print("🏁 Automation complete! Check your order confirmation.")


def login_and_order_multiple(phone_number, items, address_name=None):
    import os
    if address_name is None:
        address_name = os.getenv("ZEPTO_DEFAULT_ADDRESS", "Hsr Home")  # Fallback for testing
    """Login once, add multiple products (with quantities) to cart, then select address and pay.

    items:
        - Either an iterable of product URLs (each counted as quantity 1), e.g.:
            ["url1", "url2"]
        - Or an iterable of (url, quantity) pairs, e.g.:
            [("url1", 2), ("url2", 3)]
    """
    print(f"🚀 Starting Zepto multi-item order automation...")

    # Normalize input into list of (url, qty) with qty >= 1
    normalized: list[tuple[str, int]] = []
    for entry in items:
        if isinstance(entry, str):
            normalized.append((entry, 1))
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            url, qty = entry[0], int(entry[1])
            if qty < 1:
                continue
            normalized.append((url, qty))
        else:
            # Ignore malformed entries silently to keep flow simple
            continue

    if not normalized:
        print("⚠️ No valid product items provided, aborting.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        first_url = normalized[0][0]

        # Step 1: Go to first product page
        print("📱 Opening first product page...")
        page.goto(first_url)
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Step 2: Click Login button
        print("🔐 Clicking login...")
        page.click("span[data-testid='login-btn']")
        time.sleep(2)

        # Step 3: Enter phone number
        print(f"📞 Entering phone number: {phone_number}")
        page.fill("input[placeholder='Enter Phone Number']", phone_number)
        time.sleep(1)

        # Step 4: Click Continue button
        print("➡️  Clicking Continue...")
        page.click("button:has-text('Continue')")
        time.sleep(3)

        # Step 5: Wait for OTP - 25 seconds
        print("\n" + "=" * 60)
        print("⏸️  Waiting 25 seconds for OTP entry...")
        print("⏸️  Please enter the OTP in the browser window NOW")
        print("=" * 60 + "\n")

        time.sleep(25)

        print("▶️  Resuming automation...")

        # Loop over all items and add each to cart with its quantity
        for idx, (url, qty) in enumerate(normalized, start=1):
            print(f"\n=== Adding product {idx}/{len(normalized)} ===")
            print(f"🔄 Loading product page: {url}")
            page.goto(url)
            page.wait_for_load_state("networkidle")
            time.sleep(5)

            # Close any popups if they exist
            try:
                page.click("button:has-text('Close')", timeout=2000)
            except:
                pass

            for n in range(qty):
                # Wait for Add to Cart button
                print(f"⏳ Waiting for Add To Cart button (#{n+1}/{qty})...")
                page.wait_for_selector(
                    "button.WJXJe:has-text('Add To Cart')", timeout=15000
                )
                time.sleep(2)

                # Scroll button into view
                print("📜 Scrolling to Add To Cart button...")
                page.evaluate("""
                    const button = document.querySelector("button.WJXJe");
                    if (button) {
                        button.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                """)
                time.sleep(3)

                # Click Add to Cart
                print("🛒 Adding item to cart...")
                page.evaluate("""
                    const buttons = document.querySelectorAll("button.WJXJe");
                    for (let btn of buttons) {
                        if (btn.textContent.includes('Add To Cart')) {
                            btn.click();
                            break;
                        }
                    }
                """)
                time.sleep(4)
            print(f"✅ Added {qty} to cart!")

        # After all items are added, proceed to cart and checkout
        print("\n🛍️  Opening cart...")
        page.click("button[data-testid='cart-btn']")
        time.sleep(3)

        print("📍 Proceeding to address selection...")
        page.click("button:has-text('Add Address to proceed')")
        time.sleep(3)

        print(f"🏠 Selecting address: {address_name}")
        select_address(page, address_name)
        time.sleep(2)

        print("💳 Proceeding to payment...")
        page.click("button:has-text('Click to Pay')")
        time.sleep(5)

        print("💳 Selecting HDFC Bank Credit payment...")
        page.click("article:has-text('HDFC Bank Credit')")
        time.sleep(3)

        print("✅ Clicking Proceed to Pay...")
        page.click("article:has-text('Proceed to Pay')")
        time.sleep(5)

        print("\n" + "=" * 60)
        print("⏸️  Waiting 30 seconds for PAYMENT OTP entry...")
        print("⏸️  Please enter the payment OTP in the browser NOW")
        print("=" * 60 + "\n")

        try:
            page.wait_for_selector("input[name='otpValue']", timeout=10000)
            print("✅ Payment OTP field detected!")
        except:
            print("⚠️  OTP field not found, but continuing...")

        time.sleep(30)

        print("✅ Clicking CONFIRM button...")
        page.click("button#submitBtn")
        time.sleep(5)

        print("\n" + "=" * 60)
        print("🎉 ORDER COMPLETE!")
        print("✅ Payment confirmed and order placed for all items!")
        print("⏳ Browser will stay open for 30 more seconds...")
        print("=" * 60 + "\n")

        time.sleep(30)

        browser.close()
        print("🏁 Multi-item automation complete! Check your order confirmation.")


CAFE_PRODUCT_URLS = [
    "https://www.zepto.com/pn/almond-croissant/pvid/c8a1a8c8-fc8b-4ca9-8e57-4305fa9e0b79",
    "https://www.zepto.com/pn/black-forest-shake/pvid/1d5a86f0-2565-432a-98c8-2dbad94cb470",
    "https://www.zepto.com/pn/hazelnut-latte/pvid/89ca18fd-2178-4ef6-a3e5-b9545447f181",
    "https://www.zepto.com/pn/mac-and-cheese/pvid/b1cdf31f-4f53-45e9-bc73-360bc8d4707c",
    "https://www.zepto.com/pn/strawberry-lemonade/pvid/0adbb1a8-79df-4c2b-af11-6442999138f2",
    "https://www.zepto.com/pn/angoori-gulab-jamun/pvid/3402b965-23f9-4070-b8c4-7ceae35bc82b",
    "https://www.zepto.com/pn/desi-ghee-aloo-paratha-with-dahi/pvid/f58ccd8c-e532-4e4e-b261-79b6290017e5",
    "https://www.zepto.com/pn/black-pepper-maggi-with-peanuts/pvid/a5213c4d-6c69-4c1d-a4bd-85777cac0e1e",
    "https://www.zepto.com/pn/veg-puff/pvid/362ac747-d438-4b80-916e-e074651e53bf",
    "https://www.zepto.com/pn/adrak-chai/pvid/959a5253-e580-4f44-8236-07ac7ba96bbf",
    "https://www.zepto.com/pn/iced-americano/pvid/1f0d5ca8-8cb2-4499-b326-27654a68b6c7",
    "https://www.zepto.com/pn/spanish-coffee/pvid/2c41692c-dd57-44d3-bfb7-ef61a12eb257",
    "https://www.zepto.com/pn/poha/pvid/4426f6a8-ad91-4f21-a52a-823c8e659835",
    "https://www.zepto.com/pn/bun-maska/pvid/606354e0-f4be-477e-a18e-6b54c474f51d",
    "https://www.zepto.com/pn/chicken-puff/pvid/de23bbb3-a07f-46f1-91a2-a8171b514a33",
    "https://www.zepto.com/pn/cheese-maggi/pvid/b6a09671-d52a-440e-a4ac-7c9dda740a34",
    "https://www.zepto.com/pn/plain-maggi/pvid/ab252815-7562-465a-8abf-04ecc585c752",
    "https://www.zepto.com/pn/masala-peanuts/pvid/36a9acbc-6e07-4261-9e74-d3770a1508cd",
    "https://www.zepto.com/pn/rawa-upma/pvid/9a3c38f9-9671-4a7a-b7bf-e19829e31fba",
    "https://www.zepto.com/pn/millet-muesli-almond-cranberry/pvid/94ae3352-e03f-43d5-845e-84e5f4fe8da5",
    "https://www.zepto.com/pn/medu-vada-sambar-dip/pvid/32f6f992-141d-449b-bcc0-4e0366e838da",
    "https://www.zepto.com/pn/mini-butter-croissants/pvid/85073836-96bd-4bdf-a66f-e4796e644e94",
    "https://www.zepto.com/pn/chili-cheese-toast/pvid/a4241249-58d2-4c88-b9df-8f1dba9f5f86",
    "https://www.zepto.com/pn/butter-croissant/pvid/37732d9c-b578-461e-9bd2-54bdd92b74d9",
    "https://www.zepto.com/pn/garlic-bread-with-cheese-dip/pvid/5b265566-61a3-4660-9e76-5e40643fe81f",
    "https://www.zepto.com/pn/butter-chicken-steamed-bao/pvid/797fd5a2-c58e-4b47-9fb0-1b3e7c69235a",
    "https://www.zepto.com/pn/chicken-tandoori-momos/pvid/77583353-0155-444f-9311-d4eeca0ddfb7",
    "https://www.zepto.com/pn/double-egg-cheese-sandwich/pvid/32430f91-b606-4735-89fc-941f266b371f",
    "https://www.zepto.com/pn/tiramisu/pvid/2d01c0d0-125f-42e3-980c-679859fc7d0d",
    "https://www.zepto.com/pn/chicken-classic-burger/pvid/f41c7bce-33c4-4cfa-9647-5f38c634ee57",
    "https://www.zepto.com/pn/bulls-eye-egg-2pcs/pvid/4b4962cb-3ba0-4ff8-8764-7d628d2fd09e",
    "https://www.zepto.com/pn/vietnamese-cold-coffee/pvid/6a09750b-2bb7-4d1b-90f9-cd2a66269bfd",
]


# Run the function
if __name__ == "__main__":
    # Get phone number and address from environment variables or use placeholders
    import os
    PHONE_NUMBER = os.getenv("ZEPTO_PHONE_NUMBER", "YOUR_PHONE_NUMBER_HERE")
    PRODUCT_URL = "https://www.zepto.com/pn/iced-americano/pvid/1f0d5ca8-8cb2-4499-b326-27654a68b6c7"
    ADDRESS = os.getenv("ZEPTO_DEFAULT_ADDRESS", "YOUR_ADDRESS_LABEL_HERE")
    
    login_and_order(PHONE_NUMBER, PRODUCT_URL, ADDRESS)