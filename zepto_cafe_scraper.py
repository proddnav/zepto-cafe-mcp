from playwright.sync_api import sync_playwright
import time


def scrape_cafe_product_links(
    category_url: str = "https://www.zepto.com/pip/zepto-cafe/12830",
    scroll_pause: float = 2.0,
    max_scrolls: int = 50,
):
    """
    Scrape all product links from the Zepto Cafe category page.
    
    This function:
    1. Clicks all "See All" buttons (images with alt="CTA.png") to expand product sections
    2. Scrolls to load all products
    3. Scrapes all product links containing '/pn/' in the URL

    Default URL is the Zepto Cafe page:
    https://www.zepto.com/pip/zepto-cafe/12830
    
    Returns:
        list: List of unique product URLs
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(category_url)
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Step 1: Find and click all "See All" buttons (images with alt="CTA.png")
        print("🔍 Looking for 'See All' buttons (CTA.png images)...")
        cta_images = page.query_selector_all('img[alt="CTA.png"]')
        print(f"✅ Found {len(cta_images)} 'See All' buttons")
        
        # Click each "See All" button to expand product sections
        for idx, img in enumerate(cta_images, 1):
            try:
                print(f"🖱️ Clicking 'See All' button {idx}/{len(cta_images)}...")
                # Scroll into view first
                img.scroll_into_view_if_needed()
                time.sleep(0.5)
                
                # Find the clickable parent (usually an <a> tag or button)
                clickable_parent = img.evaluate("""
                    (img) => {
                        // Try to find clickable parent (a, button, or div with onclick)
                        let parent = img.parentElement;
                        let depth = 0;
                        while (parent && parent !== document.body && depth < 5) {
                            const tagName = parent.tagName;
                            const hasOnClick = parent.onclick !== null;
                            const role = parent.getAttribute('role');
                            const classes = parent.className || '';
                            
                            if (tagName === 'A' || tagName === 'BUTTON' || 
                                hasOnClick || role === 'button' ||
                                classes.includes('click') || classes.includes('cursor-pointer')) {
                                return parent;
                            }
                            parent = parent.parentElement;
                            depth++;
                        }
                        // If no clickable parent found, return the image itself
                        return img;
                    }
                """)
                
                if clickable_parent:
                    # Try clicking the parent element
                    try:
                        page.evaluate("(el) => { if (el) el.click(); }", clickable_parent)
                        time.sleep(1.5)  # Wait for content to load after clicking
                        print(f"   ✅ Clicked 'See All' button {idx}")
                    except:
                        # Fallback: try clicking the image directly
                        try:
                            img.click()
                            time.sleep(1.5)
                            print(f"   ✅ Clicked 'See All' button {idx} (direct image click)")
                        except Exception as e2:
                            print(f"   ⚠️ Could not click 'See All' button {idx}: {e2}")
            except Exception as e:
                print(f"   ⚠️ Error clicking 'See All' button {idx}: {e}")
                continue

        print("✅ Finished clicking all 'See All' buttons. Now scraping product links...")
        time.sleep(2)  # Wait a bit more for all content to load

        # Step 2: Scroll to load all products
        print("📜 Scrolling to load all products...")
        last_height = 0
        for scroll_num in range(max_scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                print(f"   ✅ Reached bottom after {scroll_num + 1} scrolls")
                break
            last_height = new_height

        # Step 3: Scrape all product links
        print("🔗 Scraping all product links...")
        # Individual product pages typically contain `/pn/` in the URL, e.g.:
        # https://www.zepto.com/pn/iced-americano/pvid/...
        product_links = page.eval_on_selector_all(
            "a[href*='/pn/']",
            "elements => Array.from(new Set(elements.map(e => e.href)))",
        )

        print(f"\n✅ Found {len(product_links)} unique product links:\n")
        for link in product_links:
            print(link)
        
        browser.close()
        return product_links


def scrape_category_pages(category_urls: list, scroll_pause: float = 2.0, max_scrolls: int = 50):
    """
    Scrape product links from multiple Zepto category pages.
    
    This function:
    1. For each category URL, navigates to the page
    2. Scrolls to load all product cards
    3. Extracts all product links from cards (links containing '/pn/' in URL)
    4. Returns a unique list of all product links from all pages
    
    Args:
        category_urls: List of category page URLs to scrape
        scroll_pause: Time to wait between scrolls (seconds)
        max_scrolls: Maximum number of scroll attempts per page
    
    Returns:
        list: Unique list of all product URLs from all category pages
    """
    all_product_links = set()  # Use set to automatically handle uniqueness
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        for page_idx, category_url in enumerate(category_urls, 1):
            print(f"\n{'='*60}")
            print(f"📄 Processing page {page_idx}/{len(category_urls)}")
            print(f"🔗 URL: {category_url}")
            print(f"{'='*60}\n")
            
            try:
                # Navigate to category page
                page.goto(category_url)
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # Scroll to load all product cards
                print("📜 Scrolling to load all product cards...")
                last_height = 0
                no_change_count = 0
                
                for scroll_num in range(max_scrolls):
                    # Scroll down
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(scroll_pause)
                    
                    # Check if new content loaded
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        no_change_count += 1
                        if no_change_count >= 2:  # Stop if no change for 2 consecutive scrolls
                            print(f"   ✅ Reached bottom after {scroll_num + 1} scrolls")
                            break
                    else:
                        no_change_count = 0
                        last_height = new_height
                
                # Wait a bit more for any lazy-loaded content
                time.sleep(1)
                
                # Find all product card links
                # Product cards typically have links with '/pn/' in the href
                print("🔍 Extracting product links from cards...")
                product_links = page.eval_on_selector_all(
                    "a[href*='/pn/']",
                    "elements => Array.from(new Set(elements.map(e => e.href)))",
                )
                
                # Add to master set (automatically handles uniqueness)
                links_count_before = len(all_product_links)
                all_product_links.update(product_links)
                links_count_after = len(all_product_links)
                new_links = links_count_after - links_count_before
                
                print(f"✅ Found {len(product_links)} product links on this page")
                print(f"   ({new_links} new, {len(product_links) - new_links} duplicates)")
                
            except Exception as e:
                print(f"❌ Error processing page {page_idx}: {e}")
                continue
        
        browser.close()
    
    # Convert set to sorted list for consistent output
    unique_links = sorted(list(all_product_links))
    
    print(f"\n{'='*60}")
    print(f"🎉 SCRAPING COMPLETE!")
    print(f"{'='*60}")
    print(f"📊 Total unique product links found: {len(unique_links)}")
    print(f"\n📋 All unique product links:\n")
    for idx, link in enumerate(unique_links, 1):
        print(f"{idx}. {link}")
    
    return unique_links


if __name__ == "__main__":
    # Scrape multiple category pages
    category_urls = [
        "https://www.zepto.com/uncl/snack-time/5f1a5863-1e20-408a-9084-cd2cb7da8c8c?scid=5f1a5863-1e20-408a-9084-cd2cb7da8c8c&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/all-day-breakfast/9ba0d505-71e5-4dc1-a43e-77a7753c1623?scid=9ba0d505-71e5-4dc1-a43e-77a7753c1623&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/baked-treats/037078a6-8729-410d-ace0-88f2be52d55b?scid=037078a6-8729-410d-ace0-88f2be52d55b&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/chai/47bc0c51-0d3e-4789-a3e9-3a1f33f222a0?scid=47bc0c51-0d3e-4789-a3e9-3a1f33f222a0&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/coffee/27bf4610-ee6e-440c-9a7c-2b4e955dddca?scid=27bf4610-ee6e-440c-9a7c-2b4e955dddca&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/cool-refreshments/0eb842f4-f564-4199-aa7e-5303fefe5236?scid=0eb842f4-f564-4199-aa7e-5303fefe5236&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/Snacks/34e80ff1-a2b7-4247-8914-e5b537c73b63?scid=34e80ff1-a2b7-4247-8914-e5b537c73b63&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/meal-time/fe2a8eed-2c01-4cd7-9d53-3720344bc4bd?scid=fe2a8eed-2c01-4cd7-9d53-3720344bc4bd&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/snack-time/635e8ff0-9f39-4113-b774-effc7425a990?scid=635e8ff0-9f39-4113-b774-effc7425a990&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/desserts/f0864217-589b-40e9-8dac-d0138859a530?scid=f0864217-589b-40e9-8dac-d0138859a530&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/sandwiches/5cd27f48-0dd1-4d72-920a-ebb0dfe8a4b4?scid=5cd27f48-0dd1-4d72-920a-ebb0dfe8a4b4&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/sandwiches/cdfd8d88-dbf0-46ef-a387-ccc766c1fd48?scid=cdfd8d88-dbf0-46ef-a387-ccc766c1fd48&columns=1&cardType=V1_LARGE&hidePassStrip=true",
        "https://www.zepto.com/uncl/italian/1e43d3c1-8268-4fc7-bdcd-61c32f1231bb?scid=1e43d3c1-8268-4fc7-bdcd-61c32f1231bb&columns=1&cardType=V1_LARGE&hidePassStrip=true",
    ]
    
    # Run the multi-page scraper
    scrape_category_pages(category_urls)


