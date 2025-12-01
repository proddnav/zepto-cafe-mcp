#!/usr/bin/env python3
"""
Setup script to log in to Zepto and save credentials in Firefox persistent context.
Run this once to save your login session, then future orders will use the saved session.
"""
import asyncio
import os
from playwright.async_api import async_playwright

async def setup_firefox_login():
    """Launch Firefox, navigate to Zepto, and wait for user to log in manually."""
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    firefox_data_dir = os.path.join(script_dir, "zepto_firefox_data")
    
    print("=" * 60)
    print("🔥 Firefox Login Setup for Zepto")
    print("=" * 60)
    print(f"\n📂 Firefox data directory: {firefox_data_dir}")
    print("\nThis script will:")
    print("1. Launch Firefox browser")
    print("2. Navigate to Zepto website")
    print("3. Wait for you to log in manually")
    print("4. Save your login session for future orders")
    print("\n" + "=" * 60)
    
    # Clean up old directory if it exists
    if os.path.exists(firefox_data_dir):
        import shutil
        backup_dir = f"{firefox_data_dir}_backup_{int(asyncio.get_event_loop().time())}"
        try:
            shutil.move(firefox_data_dir, backup_dir)
            print(f"📦 Backed up existing Firefox data to: {backup_dir}")
        except:
            print("⚠️ Could not backup existing data, will use existing directory")
    else:
        os.makedirs(firefox_data_dir, exist_ok=True)
        print(f"✅ Created Firefox data directory")
    
    p = await async_playwright().start()
    
    try:
        print("\n🚀 Launching Firefox with persistent context...")
        context = await p.firefox.launch_persistent_context(
            user_data_dir=firefox_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 720}
        )
        
        pages = context.pages
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()
        
        print("✅ Firefox launched successfully")
        print("\n🌐 Navigating to Zepto website...")
        await page.goto("https://www.zeptonow.com", wait_until="domcontentloaded")
        await asyncio.sleep(1)
        
        print("\n" + "=" * 60)
        print("📋 INSTRUCTIONS:")
        print("=" * 60)
        print("\n1. In the Firefox window that just opened:")
        print("   - Click 'Login' or 'Sign In'")
        print("   - Enter your phone number")
        print("   - Enter the OTP you receive")
        print("   - Complete the login process")
        print("\n2. Once you are logged in and see your account:")
        print("   - Come back to this terminal")
        print("   - Press ENTER to save your login session")
        print("\n" + "=" * 60)
        print("\n⏳ Waiting for you to log in...")
        print("   (Press ENTER after you've logged in to save the session)")
        
        # Wait for user to press Enter
        input()
        
        # Check if user is logged in
        print("\n🔍 Checking if you're logged in...")
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # Check for login indicators
        try:
            # Check for cookies
            cookies = await context.cookies()
            zepto_cookies = [c for c in cookies if "zeptonow" in c.get("domain", "").lower() and c.get("value")]
            
            if zepto_cookies:
                print(f"✅ Found {len(zepto_cookies)} Zepto cookies - login session saved!")
                
                # Try to check for login button (should not be visible if logged in)
                try:
                    login_btn = await page.query_selector("span[data-testid='login-btn']")
                    if login_btn:
                        is_visible = await login_btn.is_visible(timeout=1000)
                        if not is_visible:
                            print("✅ Login button not visible - you appear to be logged in!")
                        else:
                            print("⚠️ Login button is still visible - you may not be fully logged in")
                    else:
                        print("✅ No login button found - you appear to be logged in!")
                except:
                    print("✅ Could not verify login button, but cookies are saved")
                
                print("\n" + "=" * 60)
                print("✅ SUCCESS! Your login session has been saved!")
                print("=" * 60)
                print(f"\n📂 Session saved in: {firefox_data_dir}")
                print("\n🎉 Future orders will automatically use this saved login session.")
                print("   You won't need to log in again!")
                print("\n" + "=" * 60)
            else:
                print("⚠️ No Zepto cookies found. You may not be logged in.")
                print("   Please make sure you completed the login process.")
                print("   You can run this script again to retry.")
        except Exception as e:
            print(f"⚠️ Error checking login status: {e}")
            print("   But the session data has been saved. Future orders will try to use it.")
        
        print("\n✅ Closing browser...")
        await context.close()
        await p.stop()
        print("✅ Setup complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        try:
            await context.close()
        except:
            pass
        await p.stop()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(setup_firefox_login())
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")

