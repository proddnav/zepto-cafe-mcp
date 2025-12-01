#!/usr/bin/env python3
"""Test script to check if Chromium can launch without crashing"""
import asyncio
import sys
import os
import shutil
import time
from playwright.async_api import async_playwright

async def test_browser_launch():
    """Test browser launch with and without persistent context"""
    print("🧪 Testing Chromium browser launch...")
    print("=" * 60)
    
    # Test 1: Regular browser launch (no persistent context)
    print("\n📋 Test 1: Regular browser launch (no persistent context)")
    print("-" * 60)
    try:
        p = await async_playwright().start()
        print("✅ Playwright started")
        
        browser = await p.chromium.launch(headless=False)
        print("✅ Browser launched successfully")
        
        page = await browser.new_page()
        print("✅ Page created")
        
        await page.goto("https://www.zeptonow.com")
        print("✅ Navigated to zeptonow.com")
        
        await asyncio.sleep(2)
        print("✅ Browser is working!")
        
        await browser.close()
        await p.stop()
        print("✅ Browser closed cleanly")
        print("\n✅ Test 1 PASSED: Regular browser works!")
        
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")
        try:
            await p.stop()
        except:
            pass
        return False
    
    # Test 2: Persistent context launch
    print("\n📋 Test 2: Persistent context launch")
    print("-" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(script_dir, "zepto_browser_data_test")
    
    # Clean up test directory if it exists
    if os.path.exists(user_data_dir):
        try:
            shutil.rmtree(user_data_dir)
            print(f"🗑️ Cleaned up old test directory")
        except:
            pass
    
    try:
        p = await async_playwright().start()
        print("✅ Playwright started")
        
        print(f"📂 Creating test directory: {user_data_dir}")
        os.makedirs(user_data_dir, exist_ok=True)
        
        print("🚀 Launching browser with persistent context...")
        context = await asyncio.wait_for(
            p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                viewport={"width": 1280, "height": 720}
            ),
            timeout=30.0
        )
        print("✅ Persistent context launched successfully")
        
        pages = context.pages
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()
        print("✅ Page obtained")
        
        await page.goto("https://www.zeptonow.com")
        print("✅ Navigated to zeptonow.com")
        
        await asyncio.sleep(2)
        print("✅ Browser is working!")
        
        await context.close()
        await p.stop()
        print("✅ Context closed cleanly")
        print("\n✅ Test 2 PASSED: Persistent context works!")
        
        # Clean up test directory
        try:
            shutil.rmtree(user_data_dir)
            print(f"🗑️ Cleaned up test directory")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error details: {str(e)}")
        
        # Check if it's a crash
        error_str = str(e).lower()
        if "segv" in error_str or "crash" in error_str or "signal 11" in error_str or "targetclosederror" in error_str:
            print("\n⚠️  This looks like a browser crash!")
            print("   The browser is crashing when trying to use persistent context.")
            print("   This might be due to:")
            print("   1. Corrupted browser data")
            print("   2. System-level issue")
            print("   3. Incompatible Chromium version")
        
        try:
            await p.stop()
        except:
            pass
        
        # Clean up test directory
        try:
            shutil.rmtree(user_data_dir)
        except:
            pass
        
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 Chromium Browser Launch Test")
    print("=" * 60)
    
    try:
        result = asyncio.run(test_browser_launch())
        print("\n" + "=" * 60)
        if result:
            print("✅ ALL TESTS PASSED - Browser is working!")
            sys.exit(0)
        else:
            print("❌ SOME TESTS FAILED - Check errors above")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)

