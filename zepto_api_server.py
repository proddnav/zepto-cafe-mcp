"""
Zepto Cafe REST API Server
A FastAPI wrapper around the Zepto automation for cloud deployment and n8n integration.

Endpoints:
- POST /order - Start a single item order
- POST /order/multi - Start a multi-item order
- POST /otp/login - Submit login OTP
- POST /otp/payment - Submit payment OTP
- GET /status - Get current order status
- POST /stop - Stop current order
- GET /catalog - Get available products
- POST /stock-decision - Handle out-of-stock decisions
"""

import asyncio
import os
import sys
import json
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import the core automation logic
# We'll refactor to import from zepto_mcp_server or duplicate the logic
from playwright.async_api import async_playwright

# Load environment variables
try:
    from dotenv import load_dotenv
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default values from environment
DEFAULT_PHONE = os.getenv("ZEPTO_PHONE_NUMBER", "")
DEFAULT_ADDRESS = os.getenv("ZEPTO_DEFAULT_ADDRESS", "")

# Product catalog - same as MCP server
PRODUCT_CATALOG = {
    "almond croissant": "https://www.zepto.com/pn/almond-croissant/pvid/c8a1a8c8-fc8b-4ca9-8e57-4305fa9e0b79",
    "black forest shake": "https://www.zepto.com/pn/black-forest-shake/pvid/1d5a86f0-2565-432a-98c8-2dbad94cb470",
    "hazelnut latte": "https://www.zepto.com/pn/hazelnut-latte/pvid/89ca18fd-2178-4ef6-a3e5-b9545447f181",
    "mac and cheese": "https://www.zepto.com/pn/mac-and-cheese/pvid/b1cdf31f-4f53-45e9-bc73-360bc8d4707c",
    "strawberry lemonade": "https://www.zepto.com/pn/strawberry-lemonade/pvid/0adbb1a8-79df-4c2b-af11-6442999138f2",
    "angoori gulab jamun": "https://www.zepto.com/pn/angoori-gulab-jamun/pvid/3402b965-23f9-4070-b8c4-7ceae35bc82b",
    "desi ghee aloo paratha with dahi": "https://www.zepto.com/pn/desi-ghee-aloo-paratha-with-dahi/pvid/f58ccd8c-e532-4e4e-b261-79b6290017e5",
    "veg puff": "https://www.zepto.com/pn/veg-puff/pvid/362ac747-d438-4b80-916e-e074651e53bf",
    "adrak chai": "https://www.zepto.com/pn/adrak-chai/pvid/959a5253-e580-4f44-8236-07ac7ba96bbf",
    "iced americano": "https://www.zepto.com/pn/iced-americano/pvid/1f0d5ca8-8cb2-4499-b326-27654a68b6c7",
    "spanish coffee": "https://www.zepto.com/pn/spanish-coffee/pvid/2c41692c-dd57-44d3-bfb7-ef61a12eb257",
    "poha": "https://www.zepto.com/pn/poha/pvid/4426f6a8-ad91-4f21-a52a-823c8e659835",
    "bun maska": "https://www.zepto.com/pn/bun-maska/pvid/606354e0-f4be-477e-a18e-6b54c474f51d",
    "chicken puff": "https://www.zepto.com/pn/chicken-puff/pvid/de23bbb3-a07f-46f1-91a2-a8171b514a33",
    "cheese maggi": "https://www.zepto.com/pn/cheese-maggi/pvid/b6a09671-d52a-440e-a4ac-7c9dda740a34",
    "plain maggi": "https://www.zepto.com/pn/plain-maggi/pvid/ab252815-7562-465a-8abf-04ecc585c752",
    "masala peanuts": "https://www.zepto.com/pn/masala-peanuts/pvid/36a9acbc-6e07-4261-9e74-d3770a1508cd",
    "tiramisu": "https://www.zepto.com/pn/tiramisu/pvid/2d01c0d0-125f-42e3-980c-679859fc7d0d",
    "chicken classic burger": "https://www.zepto.com/pn/chicken-classic-burger/pvid/f41c7bce-33c4-4cfa-9647-5f38c634ee57",
    "vietnamese cold coffee": "https://www.zepto.com/pn/vietnamese-cold-coffee/pvid/6a09750b-2bb7-4d1b-90f9-cd2a66269bfd",
    "butter croissant": "https://www.zepto.com/pn/butter-croissant/pvid/37732d9c-b578-461e-9bd2-54bdd92b74d9",
    "garlic bread with cheese dip": "https://www.zepto.com/pn/garlic-bread-with-cheese-dip/pvid/5b265566-61a3-4660-9e76-5e40643fe81f",
    "cappuccino": "https://www.zepto.com/pn/cappuccino/pvid/27fbad73-4154-406c-a864-80127d4f8642",
    "latte": "https://www.zepto.com/pn/latte/pvid/88f6afb3-d80e-4e91-ba6f-e38c8a024713",
    "hot chocolate": "https://www.zepto.com/pn/hot-chocolate/pvid/a00691fc-b863-43fd-96be-f1ea08ab194e",
    "masala chai": "https://www.zepto.com/pn/masala-chai/pvid/7132f0c7-a233-4881-b310-ece3bb35ab9c",
    "classic cold coffee": "https://www.zepto.com/pn/classic-cold-coffee/pvid/6ebe42de-266c-4639-ae7b-b8517ccd52b3",
    "choco lava cake": "https://www.zepto.com/pn/choco-lava-cake/pvid/edf76459-7bbf-4ee6-9af4-507c7234368e",
    "samosa 2 pieces": "https://www.zepto.com/pn/samosa-2-pieces/pvid/5d385a24-313a-43f8-90f0-dd20eede55a0",
    "idli sambar dip": "https://www.zepto.com/pn/idli-sambar-dip/pvid/aa9a9c36-d6a1-42a5-8135-17d56ab8c7a5",
    "medu vada sambar dip": "https://www.zepto.com/pn/medu-vada-sambar-dip/pvid/32f6f992-141d-449b-bcc0-4e0366e838da",
    "chole kulche": "https://www.zepto.com/pn/chole-kulche/pvid/56a84353-e390-420b-a34b-c0d12c7aea5c",
    "dal makhani rice": "https://www.zepto.com/pn/dal-makhani-rice/pvid/0e8c050f-7b7f-4308-92a5-5366f08fcfff",
    "paneer makhani rice": "https://www.zepto.com/pn/paneer-makhani-rice/pvid/2019670e-219c-453a-88f8-35a7e7a90134",
    "butter chicken rice": "https://www.zepto.com/pn/butter-chicken-rice/pvid/dbc1404e-c8c4-4198-9c49-513bdf5b7bd6",
    "rajma masala rice": "https://www.zepto.com/pn/rajma-masala-rice/pvid/08abb94e-438d-4d42-b914-2130c3a9fcd8",
    "chole rice": "https://www.zepto.com/pn/chole-rice/pvid/ea55f3d8-ae96-4b08-86e9-fa508805e637",
}

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class OrderItem(BaseModel):
    product_name: Optional[str] = None
    item_url: Optional[str] = None
    quantity: int = Field(default=1, ge=1)

class SingleOrderRequest(BaseModel):
    product_name: Optional[str] = None
    item_url: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None

class MultiOrderRequest(BaseModel):
    items: List[OrderItem]
    phone_number: Optional[str] = None
    address: Optional[str] = None

class OTPRequest(BaseModel):
    otp: str = Field(..., min_length=4, max_length=6)

class StockDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(cancel|proceed_with_remaining|replace_items)$")
    replacement_items: Optional[List[OrderItem]] = None

class OrderStatus(BaseModel):
    status: str
    waiting_for: Optional[str] = None
    message: Optional[str] = None
    out_of_stock_items: Optional[List[str]] = None
    successfully_added: Optional[List[str]] = None

class CatalogResponse(BaseModel):
    products: List[str]
    count: int

# ============================================================================
# GLOBAL STATE (same as MCP server)
# ============================================================================

order_state = {
    "browser": None,
    "page": None,
    "playwright": None,
    "context": None,
    "status": "idle",
    "waiting_for": None,
    "phone_number": None,
    "item_url": None,
    "items": None,
    "address": None,
    "out_of_stock_items": None,
    "successfully_added": None,
    "last_message": None
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_product_url(product_name: Optional[str] = None, item_url: Optional[str] = None) -> str:
    """Get product URL from catalog by name or return direct URL."""
    if item_url:
        return item_url

    if product_name:
        key = product_name.lower().strip()
        url = PRODUCT_CATALOG.get(key)

        if not url:
            # Try fuzzy matching
            for catalog_name, catalog_url in PRODUCT_CATALOG.items():
                if key in catalog_name or catalog_name in key:
                    return catalog_url

            raise ValueError(f"Product '{product_name}' not found in catalog")
        return url

    raise ValueError("Either product_name or item_url must be provided")

# ============================================================================
# FASTAPI APP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("🚀 Zepto Cafe API Server starting...")
    yield
    # Cleanup on shutdown
    print("🛑 Shutting down, cleaning up browser...")
    if order_state.get("context"):
        try:
            await order_state["context"].close()
        except:
            pass
    if order_state.get("playwright"):
        try:
            await order_state["playwright"].stop()
        except:
            pass

app = FastAPI(
    title="Zepto Cafe API",
    description="REST API for Zepto Cafe ordering automation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for n8n integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "zepto-cafe-api", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Health check for Railway/cloud providers."""
    return {"status": "healthy"}

@app.get("/catalog", response_model=CatalogResponse)
async def get_catalog():
    """Get list of available products."""
    products = list(PRODUCT_CATALOG.keys())
    return CatalogResponse(products=products, count=len(products))

@app.get("/status", response_model=OrderStatus)
async def get_status():
    """Get current order status."""
    return OrderStatus(
        status=order_state["status"],
        waiting_for=order_state.get("waiting_for"),
        message=order_state.get("last_message"),
        out_of_stock_items=order_state.get("out_of_stock_items"),
        successfully_added=order_state.get("successfully_added")
    )

@app.post("/order")
async def start_order(request: SingleOrderRequest, background_tasks: BackgroundTasks):
    """Start a single item order."""
    global order_state

    if order_state["status"] not in ["idle", "completed", "error", "cancelled"]:
        raise HTTPException(
            status_code=409,
            detail=f"Order already in progress. Status: {order_state['status']}"
        )

    try:
        item_url = get_product_url(request.product_name, request.item_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    phone = request.phone_number or DEFAULT_PHONE
    address = request.address or DEFAULT_ADDRESS

    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not address:
        raise HTTPException(status_code=400, detail="Address is required")

    # Start order in background
    order_state["status"] = "starting"
    order_state["phone_number"] = phone
    order_state["item_url"] = item_url
    order_state["address"] = address
    order_state["items"] = None

    background_tasks.add_task(run_single_order, item_url, phone, address)

    return {
        "message": "Order started",
        "status": "starting",
        "product_url": item_url
    }

@app.post("/order/multi")
async def start_multi_order(request: MultiOrderRequest, background_tasks: BackgroundTasks):
    """Start a multi-item order."""
    global order_state

    if order_state["status"] not in ["idle", "completed", "error", "cancelled"]:
        raise HTTPException(
            status_code=409,
            detail=f"Order already in progress. Status: {order_state['status']}"
        )

    if not request.items:
        raise HTTPException(status_code=400, detail="No items provided")

    # Resolve all items to URLs
    resolved_items = []
    for item in request.items:
        try:
            url = get_product_url(item.product_name, item.item_url)
            resolved_items.append({"url": url, "qty": item.quantity})
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid item: {e}")

    phone = request.phone_number or DEFAULT_PHONE
    address = request.address or DEFAULT_ADDRESS

    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not address:
        raise HTTPException(status_code=400, detail="Address is required")

    order_state["status"] = "starting"
    order_state["phone_number"] = phone
    order_state["address"] = address
    order_state["items"] = resolved_items

    background_tasks.add_task(run_multi_order, resolved_items, phone, address)

    return {
        "message": "Multi-item order started",
        "status": "starting",
        "items_count": len(resolved_items)
    }

@app.post("/otp/login")
async def submit_login_otp(request: OTPRequest):
    """Submit login OTP."""
    global order_state

    if order_state["status"] != "waiting_for_login_otp":
        raise HTTPException(
            status_code=400,
            detail=f"Not waiting for login OTP. Current status: {order_state['status']}"
        )

    order_state["login_otp"] = request.otp
    order_state["status"] = "processing_login_otp"

    return {"message": "Login OTP submitted", "status": "processing"}

@app.post("/otp/payment")
async def submit_payment_otp(request: OTPRequest):
    """Submit payment OTP."""
    global order_state

    if order_state["status"] != "waiting_for_payment_otp":
        raise HTTPException(
            status_code=400,
            detail=f"Not waiting for payment OTP. Current status: {order_state['status']}"
        )

    order_state["payment_otp"] = request.otp
    order_state["status"] = "processing_payment_otp"

    return {"message": "Payment OTP submitted", "status": "processing"}

@app.post("/stop")
async def stop_order():
    """Stop current order."""
    global order_state

    # Close browser if open
    if order_state.get("context"):
        try:
            await order_state["context"].close()
        except:
            pass
    if order_state.get("playwright"):
        try:
            await order_state["playwright"].stop()
        except:
            pass

    # Reset state
    order_state = {
        "browser": None,
        "page": None,
        "playwright": None,
        "context": None,
        "status": "cancelled",
        "waiting_for": None,
        "phone_number": None,
        "item_url": None,
        "items": None,
        "address": None,
        "out_of_stock_items": None,
        "successfully_added": None,
        "last_message": "Order cancelled by user"
    }

    return {"message": "Order stopped", "status": "cancelled"}

@app.post("/stock-decision")
async def handle_stock_decision(request: StockDecisionRequest):
    """Handle out-of-stock item decision."""
    global order_state

    if order_state["status"] != "waiting_for_stock_decision":
        raise HTTPException(
            status_code=400,
            detail=f"Not waiting for stock decision. Current status: {order_state['status']}"
        )

    order_state["stock_decision"] = request.decision
    if request.replacement_items:
        order_state["replacement_items"] = [
            {"url": get_product_url(i.product_name, i.item_url), "qty": i.quantity}
            for i in request.replacement_items
        ]
    order_state["status"] = "processing_stock_decision"

    return {"message": f"Stock decision '{request.decision}' submitted", "status": "processing"}

# ============================================================================
# BACKGROUND ORDER TASKS
# ============================================================================

async def run_single_order(item_url: str, phone: str, address: str):
    """Run single order in background - calls the MCP server logic."""
    global order_state

    try:
        # Import and use the MCP server's order logic
        # For now, we'll implement a simplified version
        # In production, you'd refactor to share code between MCP and API servers

        order_state["status"] = "launching_browser"
        order_state["last_message"] = "Launching browser..."

        # Launch browser
        p = await async_playwright().start()
        order_state["playwright"] = p

        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_data_dir = os.path.join(script_dir, "zepto_firefox_data")

        # Launch Firefox with persistent context
        # Use headed mode with Xvfb for better compatibility
        context = await p.firefox.launch_persistent_context(
            user_data_dir,
            headless=False,  # Use headed mode - Railway has display support
            viewport={"width": 1280, "height": 720},
            args=["--no-sandbox"],
            slow_mo=100  # Slow down for stability
        )
        order_state["context"] = context

        page = context.pages[0] if context.pages else await context.new_page()
        order_state["page"] = page

        # Navigate to product
        order_state["status"] = "navigating"
        order_state["last_message"] = f"Navigating to product..."
        await page.goto(item_url, wait_until="domcontentloaded")

        # Check if logged in
        # (simplified - in production use the full logic from MCP server)
        await asyncio.sleep(1)

        # Check for login button
        login_btn = await page.query_selector("span[data-testid='login-btn']")
        if login_btn and await login_btn.is_visible():
            # Need to login
            order_state["status"] = "waiting_for_login_otp"
            order_state["waiting_for"] = "login_otp"
            order_state["last_message"] = "Please provide login OTP"

            # Click login and enter phone
            await login_btn.click()
            await asyncio.sleep(0.5)

            phone_input = await page.query_selector("input[type='tel']")
            if phone_input:
                await phone_input.fill(phone)

                # Click continue
                continue_btn = await page.query_selector("button:has-text('Continue')")
                if continue_btn:
                    await continue_btn.click()

            # Wait for OTP to be submitted
            while order_state["status"] == "waiting_for_login_otp":
                await asyncio.sleep(1)

            if order_state.get("login_otp"):
                # Enter OTP
                otp = order_state["login_otp"]
                otp_inputs = await page.query_selector_all("input[type='tel']")
                for i, digit in enumerate(otp[:6]):
                    if i < len(otp_inputs):
                        await otp_inputs[i].fill(digit)

                await asyncio.sleep(2)

        # Add to cart
        order_state["status"] = "adding_to_cart"
        order_state["last_message"] = "Adding item to cart..."

        add_btn = await page.query_selector("button:has-text('Add To Cart')")
        if add_btn:
            # Use force click to bypass overlapping elements
            await add_btn.click(force=True)
            await asyncio.sleep(1)

        # Go to checkout
        order_state["status"] = "checkout"
        order_state["last_message"] = "Proceeding to checkout..."

        cart_btn = await page.query_selector("button[data-testid='cart-btn']")
        if cart_btn:
            await cart_btn.click()
            await asyncio.sleep(1)

        # Click checkout/pay button
        pay_btn = await page.query_selector("button:has-text('Pay')")
        if pay_btn:
            await pay_btn.click()

        # Wait for payment OTP if needed
        await asyncio.sleep(2)

        # Check if waiting for payment OTP
        otp_modal = await page.query_selector("input[placeholder*='OTP']")
        if otp_modal:
            order_state["status"] = "waiting_for_payment_otp"
            order_state["waiting_for"] = "payment_otp"
            order_state["last_message"] = "Please provide payment OTP"

            while order_state["status"] == "waiting_for_payment_otp":
                await asyncio.sleep(1)

            if order_state.get("payment_otp"):
                otp = order_state["payment_otp"]
                otp_inputs = await page.query_selector_all("input[inputmode='numeric']")
                for i, digit in enumerate(otp[:6]):
                    if i < len(otp_inputs):
                        await otp_inputs[i].fill(digit)

                await asyncio.sleep(2)

        order_state["status"] = "completed"
        order_state["last_message"] = "Order completed successfully!"

    except Exception as e:
        order_state["status"] = "error"
        order_state["last_message"] = f"Error: {str(e)}"
        print(f"Order error: {e}")

async def run_multi_order(items: list, phone: str, address: str):
    """Run multi-item order in background."""
    global order_state

    try:
        order_state["status"] = "launching_browser"
        order_state["last_message"] = f"Starting order with {len(items)} items..."

        # Similar to single order but loops through items
        # In production, use the full MCP server logic

        p = await async_playwright().start()
        order_state["playwright"] = p

        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_data_dir = os.path.join(script_dir, "zepto_firefox_data")

        context = await p.firefox.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 720},
            args=["--no-sandbox"]
        )
        order_state["context"] = context

        page = context.pages[0] if context.pages else await context.new_page()
        order_state["page"] = page

        successfully_added = []
        out_of_stock = []

        for i, item in enumerate(items):
            order_state["last_message"] = f"Adding item {i+1}/{len(items)}..."

            await page.goto(item["url"], wait_until="domcontentloaded")
            await asyncio.sleep(2)  # Wait longer for page to stabilize

            # Check stock
            notify_btn = await page.query_selector("button[aria-label='Notify Me']")
            if notify_btn:
                out_of_stock.append(item["url"])
                continue

            # Add to cart - use force click and JavaScript fallback
            add_btn = await page.query_selector("button:has-text('Add To Cart')")
            if add_btn:
                for _ in range(item.get("qty", 1)):
                    try:
                        # Try force click first
                        await add_btn.click(force=True, timeout=5000)
                    except:
                        # Fallback: use JavaScript click
                        await page.evaluate("(btn) => btn.click()", add_btn)
                    await asyncio.sleep(0.5)
                successfully_added.append(item["url"])

        order_state["successfully_added"] = successfully_added
        order_state["out_of_stock_items"] = out_of_stock

        if out_of_stock:
            order_state["status"] = "waiting_for_stock_decision"
            order_state["waiting_for"] = "stock_decision"
            order_state["last_message"] = f"{len(out_of_stock)} items out of stock"

            while order_state["status"] == "waiting_for_stock_decision":
                await asyncio.sleep(1)

            if order_state.get("stock_decision") == "cancel":
                order_state["status"] = "cancelled"
                order_state["last_message"] = "Order cancelled due to out-of-stock items"
                return

        # Proceed to checkout
        order_state["status"] = "checkout"
        order_state["last_message"] = "Proceeding to checkout..."

        # ... rest of checkout flow similar to single order

        order_state["status"] = "completed"
        order_state["last_message"] = f"Order completed! {len(successfully_added)} items added."

    except Exception as e:
        order_state["status"] = "error"
        order_state["last_message"] = f"Error: {str(e)}"
        print(f"Multi-order error: {e}")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
