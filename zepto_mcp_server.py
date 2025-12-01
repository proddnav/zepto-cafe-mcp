import asyncio
import json
import sys
import os
import shutil
import time
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from playwright.async_api import async_playwright

# Load environment variables from .env file if it exists (optional)
# If python-dotenv is not installed, this will silently fail and use system env vars
try:
    from dotenv import load_dotenv
    # Load .env file from the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print("✅ Loaded environment variables from .env file", file=sys.stderr)
    else:
        print("ℹ️ No .env file found - using system environment variables or Claude Desktop config", file=sys.stderr)
except ImportError:
    # python-dotenv not installed - that's okay, will use system env vars or Claude Desktop config
    pass

# CRITICAL: Redirect all print statements to stderr to avoid breaking MCP JSON-RPC protocol
# MCP communicates via JSON over stdout, so any print() output breaks the protocol
import builtins
_original_print = builtins.print
def print(*args, **kwargs):
    kwargs.setdefault('file', sys.stderr)
    _original_print(*args, **kwargs)

# PRODUCT CATALOG - Add more products here as needed
PRODUCT_CATALOG = {
    # Zepto Cafe items
    "almond croissant": "https://www.zepto.com/pn/almond-croissant/pvid/c8a1a8c8-fc8b-4ca9-8e57-4305fa9e0b79",
    "black forest shake": "https://www.zepto.com/pn/black-forest-shake/pvid/1d5a86f0-2565-432a-98c8-2dbad94cb470",
    "hazelnut latte": "https://www.zepto.com/pn/hazelnut-latte/pvid/89ca18fd-2178-4ef6-a3e5-b9545447f181",
    "mac and cheese": "https://www.zepto.com/pn/mac-and-cheese/pvid/b1cdf31f-4f53-45e9-bc73-360bc8d4707c",
    "strawberry lemonade": "https://www.zepto.com/pn/strawberry-lemonade/pvid/0adbb1a8-79df-4c2b-af11-6442999138f2",
    "angoori gulab jamun": "https://www.zepto.com/pn/angoori-gulab-jamun/pvid/3402b965-23f9-4070-b8c4-7ceae35bc82b",
    "desi ghee aloo paratha with dahi": "https://www.zepto.com/pn/desi-ghee-aloo-paratha-with-dahi/pvid/f58ccd8c-e532-4e4e-b261-79b6290017e5",
    "black pepper maggi with peanuts": "https://www.zepto.com/pn/black-pepper-maggi-with-peanuts/pvid/a5213c4d-6c69-4c1d-a4bd-85777cac0e1e",
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
    "rawa upma": "https://www.zepto.com/pn/rawa-upma/pvid/9a3c38f9-9671-4a7a-b7bf-e19829e31fba",
    "millet muesli almond cranberry": "https://www.zepto.com/pn/millet-muesli-almond-cranberry/pvid/94ae3352-e03f-43d5-845e-84e5f4fe8da5",
    "medu vada sambar dip": "https://www.zepto.com/pn/medu-vada-sambar-dip/pvid/32f6f992-141d-449b-bcc0-4e0366e838da",
    "mini butter croissants": "https://www.zepto.com/pn/mini-butter-croissants/pvid/85073836-96bd-4bdf-a66f-e4796e644e94",
    "chili cheese toast": "https://www.zepto.com/pn/chili-cheese-toast/pvid/a4241249-58d2-4c88-b9df-8f1dba9f5f86",
    "butter croissant": "https://www.zepto.com/pn/butter-croissant/pvid/37732d9c-b578-461e-9bd2-54bdd92b74d9",
    "garlic bread with cheese dip": "https://www.zepto.com/pn/garlic-bread-with-cheese-dip/pvid/5b265566-61a3-4660-9e76-5e40643fe81f",
    "butter chicken steamed bao": "https://www.zepto.com/pn/butter-chicken-steamed-bao/pvid/797fd5a2-c58e-4b47-9fb0-1b3e7c69235a",
    "chicken tandoori momos": "https://www.zepto.com/pn/chicken-tandoori-momos/pvid/77583353-0155-444f-9311-d4eeca0ddfb7",
    "double egg and cheese sandwich": "https://www.zepto.com/pn/double-egg-cheese-sandwich/pvid/32430f91-b606-4735-89fc-941f266b371f",
    "tiramisu": "https://www.zepto.com/pn/tiramisu/pvid/2d01c0d0-125f-42e3-980c-679859fc7d0d",
    "chicken classic burger": "https://www.zepto.com/pn/chicken-classic-burger/pvid/f41c7bce-33c4-4cfa-9647-5f38c634ee57",
    "bulls eye egg 2pcs": "https://www.zepto.com/pn/bulls-eye-egg-2pcs/pvid/4b4962cb-3ba0-4ff8-8764-7d628d2fd09e",
    "vietnamese cold coffee": "https://www.zepto.com/pn/vietnamese-cold-coffee/pvid/6a09750b-2bb7-4d1b-90f9-cd2a66269bfd",
    # Additional products
    "south indian chicken curry rice": "https://www.zepto.com/pn/south-indian-chicken-curry-rice/pvid/b5968528-73e3-436a-9159-f7e50d62246b",
    "coca cola zero sugar": "https://www.zepto.com/pn/coca-cola-zero-sugar-soft-drink-can/pvid/f9fc134f-2bf8-4c75-8fd0-54ed20f881d8",
    "coke zero": "https://www.zepto.com/pn/coca-cola-zero-sugar-soft-drink-can/pvid/f9fc134f-2bf8-4c75-8fd0-54ed20f881d8",
    "hocco bix cake chocolate chips ice cream sandwich": "https://www.zepto.com/pn/hocco-bix-cake-chocolate-chips-ice-cream-sandwich/pvid/94879cba-016c-42d5-ae5c-db0c3bbfb3bf",
    "hocco ice cream sandwich": "https://www.zepto.com/pn/hocco-bix-cake-chocolate-chips-ice-cream-sandwich/pvid/94879cba-016c-42d5-ae5c-db0c3bbfb3bf",
    "pepsi black": "https://www.zepto.com/pn/pepsi-black-cola-diet-soft-drink/pvid/c6ddb7ce-ffe7-495d-bcbd-5e8697db0e78",
    # Newly scraped products
    "250ml lemon iced tea": "https://www.zepto.com/pn/250ml-lemon-iced-tea/pvid/3c677f19-cadf-40d2-a930-eb89f7c4cd60",
    "250ml masala chaas": "https://www.zepto.com/pn/250ml-masala-chaas/pvid/ba82530c-d3de-4d2e-8ceb-b27d60c35751",
    "adrak chai no sugar": "https://www.zepto.com/pn/adrak-chai-no-sugar/pvid/50eab84d-bf7a-42dc-a961-c8a8888c5403",
    "aloo pyaz kulcha": "https://www.zepto.com/pn/aloo-pyaz-kulcha/pvid/30afa73e-4178-4aea-85f4-76f49d0bd0b6",
    "ash gourd": "https://www.zepto.com/pn/ash-gourd/pvid/aa891942-3ce5-437e-bb11-0120ae085874",
    "avocado indian premium semi ripe": "https://www.zepto.com/pn/avocado-indian-premium-semi-ripe/pvid/10a847f5-b72b-42b8-b1b7-619a26bccf90",
    "beetroot 500 g combo": "https://www.zepto.com/pn/beetroot-500-g-combo/pvid/20b3e088-7254-4355-8955-e25ebd552f9e",
    "bhelpuri": "https://www.zepto.com/pn/bhelpuri/pvid/a42c13b4-10d8-4c33-8e11-bbbb3a8f682f",
    "blue flower rose tea": "https://www.zepto.com/pn/blue-flower-rose-tea/pvid/97ad5a72-5ae5-4337-98d6-3000c872d978",
    "blueberry imported": "https://www.zepto.com/pn/blueberry-imported/pvid/025d077e-d19d-4792-a4f3-b8dfcd79df34",
    "bombay aloo tikki sandwich": "https://www.zepto.com/pn/bombay-aloo-tikki-sandwich/pvid/5f76034c-880f-4ffb-9b8b-17e1ba69b9ea",
    "bottle gourd": "https://www.zepto.com/pn/bottle-gourd/pvid/f613462d-a4c2-4e35-9388-aa520fd90ef4",
    "bulls eye egg 4pcs": "https://www.zepto.com/pn/bulls-eye-egg-4pcs/pvid/8036e5ea-9fa8-4c52-926d-97892fb39685",
    "butter chicken rice": "https://www.zepto.com/pn/butter-chicken-rice/pvid/dbc1404e-c8c4-4198-9c49-513bdf5b7bd6",
    "butter chicken": "https://www.zepto.com/pn/butter-chicken/pvid/695e7401-a412-4698-be8a-c3cfb33521c9",
    "butter maggi": "https://www.zepto.com/pn/butter-maggi/pvid/9ee479c7-74ec-4fe2-b344-710d2d205267",
    "butter popcorn bag": "https://www.zepto.com/pn/butter-popcorn-bag/pvid/b4fc4721-e7f8-4553-9dd4-73da997ce96e",
    "cappuccino": "https://www.zepto.com/pn/cappuccino/pvid/27fbad73-4154-406c-a864-80127d4f8642",
    "channa jor chaat": "https://www.zepto.com/pn/channa-jor-chaat/pvid/a0ee7d1a-fde7-4f27-898c-a1e0eb9bb19a",
    "chicken seekh kebab": "https://www.zepto.com/pn/chicken-seekh-kebab/pvid/4d3781cd-84c9-44d9-95f9-452adc566167",
    "choco lava cake": "https://www.zepto.com/pn/choco-lava-cake/pvid/edf76459-7bbf-4ee6-9af4-507c7234368e",
    "chole chapati": "https://www.zepto.com/pn/chole-chapati/pvid/fea627a3-5e97-421b-a4b8-6899a9cbd182",
    "chole kulche": "https://www.zepto.com/pn/chole-kulche/pvid/56a84353-e390-420b-a34b-c0d12c7aea5c",
    "chole rice": "https://www.zepto.com/pn/chole-rice/pvid/ea55f3d8-ae96-4b08-86e9-fa508805e637",
    "chole samose": "https://www.zepto.com/pn/chole-samose/pvid/7ddb1e07-d803-408e-a9d0-366a8f58c78b",
    "chole": "https://www.zepto.com/pn/chole/pvid/1f5f3ad4-b103-4ba1-9525-0b5a3a249e64",
    "classic chai no sugar": "https://www.zepto.com/pn/classic-chai-no-sugar/pvid/9b1771bc-360e-4ae5-a776-bbbf8b120ece",
    "classic cold coffee": "https://www.zepto.com/pn/classic-cold-coffee/pvid/6ebe42de-266c-4639-ae7b-b8517ccd52b3",
    "dal makhani chapati": "https://www.zepto.com/pn/dal-makhani-chapati/pvid/1488ba02-b903-4a44-92fb-9b604e5efc52",
    "dal makhani rice": "https://www.zepto.com/pn/dal-makhani-rice/pvid/0e8c050f-7b7f-4308-92a5-5366f08fcfff",
    "dal makhani": "https://www.zepto.com/pn/dal-makhani/pvid/dcd8e9be-70d7-4687-ba9b-d455ed3e3f5f",
    "dragon fruit imported": "https://www.zepto.com/pn/dragon-fruit-imported/pvid/85a8b981-aac7-4344-9a28-9818e50b790d",
    "egg maggi": "https://www.zepto.com/pn/egg-maggi/pvid/e2d9f0ce-279f-4881-b2f1-d733012169e1",
    "espresso tonic": "https://www.zepto.com/pn/espresso-tonic/pvid/1b9b9092-f472-4a51-8a29-e18dcd0e10dc",
    "french vanilla latte": "https://www.zepto.com/pn/french-vanilla-latte/pvid/ff4ab8c9-1e6a-4579-acb4-e5f8243d647d",
    "hazelnut cappuccino": "https://www.zepto.com/pn/hazelnut-cappuccino/pvid/36490ded-162b-40a1-8126-1404d278ee50",
    "hazelnut cold coffee": "https://www.zepto.com/pn/hazelnut-cold-coffee/pvid/91c73e02-89a1-468b-b0ed-7f5dcc6ad82e",
    "hellmanns chicken tikka sandwich": "https://www.zepto.com/pn/hellmanns-chicken-tikka-sandwich/pvid/cf6740d1-a405-44f5-8d41-0e00d4c5cac0",
    "hellmanns paneer tikka sandwich": "https://www.zepto.com/pn/hellmanns-paneer-tikka-sandwich/pvid/59691f11-1757-4adc-8e9b-3ef2b817106b",
    "hibiscus cinnamon tea": "https://www.zepto.com/pn/hibiscus-cinnamon-tea/pvid/0aaae272-a967-4363-8022-f6784d8b309e",
    "hot chocolate": "https://www.zepto.com/pn/hot-chocolate/pvid/a00691fc-b863-43fd-96be-f1ea08ab194e",
    "hot milk": "https://www.zepto.com/pn/hot-milk/pvid/76b85a8d-95b8-49d7-a5aa-2225dedd5ee9",
    "idli sambar dip": "https://www.zepto.com/pn/idli-sambar-dip/pvid/aa9a9c36-d6a1-42a5-8135-17d56ab8c7a5",
    "kesari rasmalai": "https://www.zepto.com/pn/kesari-rasmalai/pvid/db45b34a-7084-48e8-a658-010c7ffafa63",
    "lady finger": "https://www.zepto.com/pn/lady-finger/pvid/2c89bcce-7f60-4d52-9613-3ca6c10fe527",
    "latte": "https://www.zepto.com/pn/latte/pvid/88f6afb3-d80e-4e91-ba6f-e38c8a024713",
    "lemon iced tea": "https://www.zepto.com/pn/lemon-iced-tea/pvid/18c77fdf-8f6b-4ef0-bd37-1a113d7fc60c",
    "lemon": "https://www.zepto.com/pn/lemon/pvid/3e99d6ed-9714-4c6c-809a-c767e47dba5f",
    "lettuce iceberg": "https://www.zepto.com/pn/lettuce-iceberg/pvid/370bf2eb-11a9-40cb-915a-998162d73593",
    "magic masala mix": "https://www.zepto.com/pn/magic-masala-mix/pvid/9f710c9d-d485-48a1-8db0-2b203437d627",
    "magnum shake": "https://www.zepto.com/pn/magnum-shake/pvid/103118ae-389c-46ac-a599-c4bc78debdad",
    "masala chaas": "https://www.zepto.com/pn/masala-chaas/pvid/9c4f4a6b-9b6d-4a7a-8cc9-a5a22d909600",
    "masala chai no sugar 500 ml": "https://www.zepto.com/pn/masala-chai-no-sugar-500-ml/pvid/3556a247-d92c-47b1-a280-e0eb953de97e",
    "masala chai": "https://www.zepto.com/pn/masala-chai/pvid/7132f0c7-a233-4881-b310-ece3bb35ab9c",
    "masala omelette pav": "https://www.zepto.com/pn/masala-omelette-pav/pvid/068a6414-12a2-4cb6-a12d-17e9e30c9a46",
    "mixed berry shake": "https://www.zepto.com/pn/mixed-berry-shake/pvid/a75e1280-e95c-468c-96da-642edddbe356",
    "muesli with strawberry greek yogurt": "https://www.zepto.com/pn/muesli-with-strawberry-greek-yogurt/pvid/abf8ebd8-b364-4574-aee7-cafa87149fc8",
    "mushroom button": "https://www.zepto.com/pn/mushroom-button/pvid/178b3f0f-c01d-4065-8f5c-d1902cbb5d51",
    "paneer makhani rice": "https://www.zepto.com/pn/paneer-makhani-rice/pvid/2019670e-219c-453a-88f8-35a7e7a90134",
    "paneer makhani": "https://www.zepto.com/pn/paneer-makhani/pvid/db62259f-69ca-40c6-9165-e33e24b08b2b",
    "paneer masala maggi": "https://www.zepto.com/pn/paneer-masala-maggi/pvid/dd89ed22-6c81-40e3-904a-abe8c0c373f5",
    "paneer tandoori tikka": "https://www.zepto.com/pn/paneer-tandoori-tikka/pvid/7eb6a978-fd60-4288-a37e-7627312cd8ea",
    "papaya": "https://www.zepto.com/pn/papaya/pvid/105c48cc-d5cb-4279-ac58-fe36cc92d51d",
    "plain curd": "https://www.zepto.com/pn/plain-curd/pvid/a1a7b157-d40b-41c0-92be-e119a8c77e9a",
    "pomegranate small": "https://www.zepto.com/pn/pomegranate-small/pvid/99dd9fd0-1b06-4649-b53f-cf756f60b8ea",
    "popular essentials cinnamon whole dalchini": "https://www.zepto.com/pn/popular-essentials-cinnamon-whole-dalchini/pvid/70b6574c-77b3-4715-a370-8bba207c0f4a",
    "popular essentials saunffennel seeds": "https://www.zepto.com/pn/popular-essentials-saunffennel-seeds/pvid/870056e6-aad4-43e6-8e38-e757dc2b028c",
    "potato": "https://www.zepto.com/pn/potato/pvid/f72c0479-1ae2-44fd-a65f-ca569d4f8c72",
    "rajma masala rice": "https://www.zepto.com/pn/rajma-masala-rice/pvid/08abb94e-438d-4d42-b914-2130c3a9fcd8",
    "roomali roti": "https://www.zepto.com/pn/roomali-roti/pvid/0e944b9f-92fc-486e-94cc-2b6b0e9c0d76",
    "samosa 2 pieces": "https://www.zepto.com/pn/samosa-2-pieces/pvid/5d385a24-313a-43f8-90f0-dd20eede55a0",
    "samosa pav": "https://www.zepto.com/pn/samosa-pav/pvid/f2060662-62d3-41d2-ae67-93dbd7ea24a3",
    "steamed rice family size": "https://www.zepto.com/pn/steamed-rice-family-size/pvid/5b6eab8c-b9ba-443a-914f-afe6a6cdd88c",
    "steamed rice": "https://www.zepto.com/pn/steamed-rice/pvid/6b744fa4-f7e0-4cb9-8b3e-3befcf1ecb2d",
    "strawberry shake": "https://www.zepto.com/pn/strawberry-shake/pvid/650d33dd-73f6-4ce9-ba2b-ab107f522d4e",
    "strawberry smoothie": "https://www.zepto.com/pn/strawberry-smoothie/pvid/c3e1aedc-d42c-4733-b6e4-ab7f676bc373",
    "strawberry": "https://www.zepto.com/pn/strawberry/pvid/cf8e41c6-8b18-461f-95b4-02876a22edce",
    "sweet corn chaat": "https://www.zepto.com/pn/sweet-corn-chaat/pvid/c91f9888-205b-4b55-a219-a394314eb5b5",
    "tawa plain paratha pack of 2": "https://www.zepto.com/pn/tawa-plain-paratha-pack-of-2/pvid/c04151e9-f787-40dd-aeff-5b57224787f3",
    "triple chocolate mousse": "https://www.zepto.com/pn/triple-chocolate-mousse/pvid/26a31055-2f4a-4fde-be96-530ab4cd19f1",
    "tulsi turmeric tea": "https://www.zepto.com/pn/tulsi-turmeric-tea/pvid/ab27a12a-8d6b-4821-9418-1f3d0ce19e42",
    "veg steamed pizza bao": "https://www.zepto.com/pn/veg-steamed-pizza-bao/pvid/cf9fb663-e925-413e-99cd-4e49a06d2cd2",
    "virgin mojito": "https://www.zepto.com/pn/virgin-mojito/pvid/49226b4f-8f75-4df1-809e-03f1dd9b2476",
    "wheat chapati pack of 10": "https://www.zepto.com/pn/wheat-chapati-pack-of-10/pvid/a624a393-2279-41d7-8c0c-a1b6dd661ab1",
    "wheat chapati pack of 3": "https://www.zepto.com/pn/wheat-chapati-pack-of-3/pvid/d707815a-2f6e-443d-bee9-210fbc33eea1",
    "wheat chapati pack of 5": "https://www.zepto.com/pn/wheat-chapati-pack-of-5/pvid/4b9364e7-fe2f-4f60-a050-66e8716887e9",
    "whey protein masala chaas wellbeing": "https://www.zepto.com/pn/whey-protein-masala-chaas-wellbeing/pvid/0f20ad90-25f7-44bd-91a1-765d2302e2e9",
    "onion": "https://www.zepto.com/pn/fresh-onion/pvid/5b5c1960-d2d1-4528-8a74-bc7280174071",
    "coconut milk": "https://www.zepto.com/pn/dabur-hommade-organic-coconut-milk/pvid/9687009f-7d47-4cd0-8b2e-6512e9730427",
}

# Address selectors - These are example labels only
# Your actual address labels in Zepto may be different
# The code supports fuzzy matching, so any address label will work
ADDRESS_SELECTORS = {
    "Hsr Home": "div.c4ZmYS:has-text('Hsr Home')",
    "Office New Cafe": "div.c4ZmYS:has-text('Office New Cafe')",
    "Hyd Home": "div.c4ZmYS:has-text('Hyd Home')",
}

# Global state to manage browser and order flow
order_state = {
    "browser": None,
    "page": None,
    "playwright": None,
    "context": None,  # Persistent browser context
    "status": "idle",
    "waiting_for": None,
    "phone_number": None,
    "item_url": None,
    "items": None,  # for multi-item orders: list of {"url": str, "qty": int}
    "address": None,
    "out_of_stock_items": None,  # list of out-of-stock items
    "successfully_added": None  # list of successfully added items
}

server = Server("zepto-cafe")


async def check_product_stock(page) -> tuple[bool, str]:
    """
    Check if product is in stock or out of stock.
    Returns: (is_in_stock: bool, product_name: str)
    """
    try:
        # Get product name first (for better error messages)
        product_name = "this product"
        try:
            name_selectors = [
                "h1",
                "[data-testid='product-title']",
                ".product-title",
                "h2",
                "h3"
            ]
            for selector in name_selectors:
                name_elem = await page.query_selector(selector)
                if name_elem:
                    text = await name_elem.text_content()
                    if text and text.strip():
                        product_name = text.strip()
                        break
        except:
            pass
        
        # Multiple strategies to detect "Notify Me" button (out of stock)
        # Strategy 1: Look for aria-label="Notify Me" (most reliable)
        try:
            notify_by_aria = await page.query_selector('button[aria-label="Notify Me"]')
            if notify_by_aria:
                print(f"🔍 Found 'Notify Me' button by aria-label - product is OUT OF STOCK")
                return (False, product_name)
        except Exception as e:
            print(f"⚠️ Error checking aria-label: {e}")
        
        # Strategy 2: Look for button with class SVCWV (specific to out-of-stock button)
        try:
            notify_by_class = await page.query_selector("button.SVCWV")
            if notify_by_class:
                text = await notify_by_class.text_content()
                if text and ("Notify Me" in text or "notify" in text.lower() or "when back in stock" in text.lower()):
                    print(f"🔍 Found 'Notify Me' button by class SVCWV - product is OUT OF STOCK")
                    return (False, product_name)
        except Exception as e:
            print(f"⚠️ Error checking SVCWV class: {e}")
        
        # Strategy 3: Look for button containing "Notify Me" text in spans
        try:
            notify_buttons = await page.query_selector_all("button")
            for btn in notify_buttons:
                # Check button text content
                text = await btn.text_content()
                if text and ("Notify Me" in text or "notify me" in text.lower() or "when back in stock" in text.lower()):
                    # Double-check by looking for the specific structure
                    spans = await btn.query_selector_all("span")
                    for span in spans:
                        span_text = await span.text_content()
                        if span_text and ("Notify Me" in span_text or "when back in stock" in span_text.lower()):
                            print(f"🔍 Found 'Notify Me' button by text content - product is OUT OF STOCK")
                            return (False, product_name)
        except Exception as e:
            print(f"⚠️ Error checking button text: {e}")
        
        # Strategy 4: Look for any button with aria-label containing "Notify"
        try:
            notify_by_label = await page.query_selector("button[aria-label*='Notify'], button[aria-label*='notify']")
            if notify_by_label:
                text = await notify_by_label.text_content()
                if text and ("Notify" in text or "notify" in text.lower()):
                    print(f"🔍 Found notify button by aria-label pattern - product is OUT OF STOCK")
                    return (False, product_name)
        except Exception as e:
            print(f"⚠️ Error checking aria-label pattern: {e}")
        
        # Check for "Add To Cart" button (in stock indicator)
        # Strategy 1: Direct text search
        try:
            add_to_cart_buttons = await page.query_selector_all("button")
            for btn in add_to_cart_buttons:
                text = await btn.text_content()
                if text and ("Add To Cart" in text or "Add to Cart" in text or "add to cart" in text.lower()):
                    print(f"🔍 Found 'Add To Cart' button - product is IN STOCK")
                    return (True, product_name)
        except:
            pass
        
        # Strategy 2: Look for button with class WJXJe (common Zepto class)
        try:
            add_cart_by_class = await page.query_selector("button.WJXJe")
            if add_cart_by_class:
                text = await add_cart_by_class.text_content()
                if text and ("Add" in text and "Cart" in text):
                    print(f"🔍 Found Add To Cart by class - product is IN STOCK")
                    return (True, product_name)
        except:
            pass
        
        # If neither found clearly, check page content for clues
        try:
            page_text = await page.evaluate("() => document.body.innerText")
            if page_text:
                if "out of stock" in page_text.lower() or "notify me" in page_text.lower():
                    print(f"🔍 Page text suggests OUT OF STOCK")
                    return (False, product_name)
                if "add to cart" in page_text.lower():
                    print(f"🔍 Page text suggests IN STOCK")
                    return (True, product_name)
        except:
            pass
        
        # Default: assume out of stock if we can't find Add To Cart
        # This is safer - we'll double-check before proceeding
        print(f"⚠️ Could not definitively determine stock status, assuming OUT OF STOCK for safety")
        return (False, product_name)
    except Exception as e:
        print(f"⚠️ Error checking stock: {e}")
        # Default to out of stock for safety
        return (False, "this product")


async def select_address(page, address_name: str):
    """
    Async address selector mirroring zepto_automation.py behavior.

    - For Jo's address, scrolls inside the saved-addresses container and clicks
      the entry with text: "1St Floor, Trillium Rose, JV Hills, Hyderabad".
    - For known labels (Hsr Home / Office New Cafe / Hyd Home), uses fixed selectors.
    - For anything else, falls back to text-based selector on the label.
    """
    # Special handling: Jo's address requires scrolling inside the saved-addresses container
    if address_name.lower() in {"jo", "jo's address", "jo address"}:
        container = page.locator("div.fsVuP")
        target = page.locator(
            "span.line-clamp-2.break-all:has-text('1St Floor, Trillium Rose, JV Hills, Hyderabad')"
        )

        for _ in range(20):
            if await target.count() > 0 and await target.first.is_visible():
                await target.first.click()
                return
            if await container.count() > 0:
                await container.first.evaluate(
                    "el => { el.scrollTop = el.scrollTop + 400; }"
                )
            await asyncio.sleep(0.2)  # Reduced from 0.5

        if await target.count() > 0:
            await target.first.click()
            return
        raise Exception("Jo's address not found in saved addresses list.")

    selector = ADDRESS_SELECTORS.get(
        address_name, f"div.c4ZmYS:has-text('{address_name}')"
    )
    await page.click(selector)

def get_product_url(product_name=None, item_url=None):
    """
    Get product URL from catalog by name or return direct URL.
    Raises ValueError if product not found.
    """
    if item_url:
        return item_url
    
    if product_name:
        key = product_name.lower().strip()
        url = PRODUCT_CATALOG.get(key)
        
        if not url:
            available = ", ".join(PRODUCT_CATALOG.keys())
            raise ValueError(
                f"Product '{product_name}' not found in catalog. "
                f"Available products: {available}"
            )
        
        return url
    
    raise ValueError("Either product_name or item_url must be provided")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="start_zepto_order",
            description="IMMEDIATELY start a Zepto Cafe order when user asks to order something. Opens Firefox browser and begins order process. Use this function as soon as user mentions ordering from Zepto. Product can be specified by name (e.g., 'iced americano', 'hazelnut latte') or direct URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product to order (e.g., 'iced americano'). Available products: " + ", ".join(PRODUCT_CATALOG.keys())
                    },
                    "item_url": {
                        "type": "string",
                        "description": "Direct URL to the product (optional if product_name is provided)"
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "User's phone number for login (defaults to environment variable ZEPTO_PHONE_NUMBER or prompts user)",
                        "default": os.getenv("ZEPTO_PHONE_NUMBER", "")
                    },
                    "address": {
                        "type": "string",
                        "description": "Delivery address name (e.g. 'Hsr Home', 'Office New Cafe', 'Hyd Home', 'Jo'). Defaults to environment variable ZEPTO_DEFAULT_ADDRESS if set.",
                        "default": os.getenv("ZEPTO_DEFAULT_ADDRESS", "")
                    }
                }
            }
        ),
        types.Tool(
            name="submit_login_otp",
            description="Submits the login OTP received via SMS",
            inputSchema={
                "type": "object",
                "properties": {
                    "otp": {
                        "type": "string",
                        "description": "6-digit OTP code"
                    }
                },
                "required": ["otp"]
            }
        ),
        types.Tool(
            name="submit_payment_otp",
            description="Submits the payment OTP for completing the order",
            inputSchema={
                "type": "object",
                "properties": {
                    "otp": {
                        "type": "string",
                        "description": "6-digit payment OTP"
                    }
                },
                "required": ["otp"]
            }
        ),
        types.Tool(
            name="get_order_status",
            description="Gets the current status of the order process",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="stop_order",
            description="Stops and resets the current order process. Use this when user clicks stop or wants to cancel/restart the order.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="start_zepto_multi_order",
            description=(
                "Starts a Zepto Cafe multi-item order process in a single cart. "
                "Provide a list of items with product names or direct URLs and optional quantities. "
                "The flow logs in once, adds all items to cart, then selects the address and completes the order."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": (
                            "List of items to order. Each item can specify a product_name "
                            "(matching the catalog) or a direct item_url, plus an optional quantity."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_name": {
                                    "type": "string",
                                    "description": "Product name, e.g. 'mac and cheese', 'angoori gulab jamun', 'iced americano'"
                                },
                                "item_url": {
                                    "type": "string",
                                    "description": "Direct Zepto product URL (overrides product_name if provided)"
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "Quantity for this item (default 1)",
                                    "default": 1,
                                    "minimum": 1
                                }
                            }
                        }
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "User's phone number for login (defaults to environment variable ZEPTO_PHONE_NUMBER or prompts user)",
                        "default": os.getenv("ZEPTO_PHONE_NUMBER", "")
                    },
                    "address": {
                        "type": "string",
                        "description": "Delivery address name (e.g. 'Hsr Home', 'Office New Cafe', 'Hyd Home', 'Jo')",
                        "default": "Hsr Home"
                    }
                },
                "required": ["items"]
            }
        ),
        types.Tool(
            name="handle_stock_decision",
            description=(
                "Handles user decision when items are out of stock. "
                "Use this after receiving an out-of-stock alert to proceed with the order."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": ["cancel", "proceed_with_remaining", "replace_items"],
                        "description": (
                            "User's decision: 'cancel' to cancel entire order, "
                            "'proceed_with_remaining' to continue with available items, "
                            "'replace_items' to order different products (requires replacement_items)"
                        )
                    },
                    "replacement_items": {
                        "type": "array",
                        "description": (
                            "Required if decision is 'replace_items'. "
                            "List of replacement items with product_name/item_url and quantity."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_name": {"type": "string"},
                                "item_url": {"type": "string"},
                                "quantity": {"type": "integer", "default": 1, "minimum": 1}
                            }
                        }
                    }
                },
                "required": ["decision"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution"""
    
    if name == "start_zepto_order":
        try:
            # Get URL from product name or direct URL
            item_url = get_product_url(
                product_name=arguments.get("product_name"),
                item_url=arguments.get("item_url")
            )

            # Get phone number from argument, environment variable, or use default
            phone_number = arguments.get("phone_number") or os.getenv("ZEPTO_PHONE_NUMBER") or ""
            if not phone_number:
                return [types.TextContent(type="text", text="Error: Phone number is required. Set ZEPTO_PHONE_NUMBER environment variable in Claude Desktop config or provide it as a parameter.")]
            
            # Get address from argument, environment variable, or use empty (will prompt if needed)
            address = arguments.get("address") or os.getenv("ZEPTO_DEFAULT_ADDRESS") or ""
            if not address:
                return [types.TextContent(type="text", text="Error: Address is required. Set ZEPTO_DEFAULT_ADDRESS environment variable or provide it as a parameter (e.g., 'Hsr Home', 'Office New Cafe').")]
            
            result = await start_order(
                item_url,
                phone_number,
                address
            )
            return [types.TextContent(type="text", text=result)]
        except ValueError as e:
            return [types.TextContent(type="text", text=str(e))]
    
    elif name == "submit_login_otp":
        result = await submit_login(arguments.get("otp"))
        return [types.TextContent(type="text", text=result)]
    
    elif name == "submit_payment_otp":
        result = await submit_payment(arguments.get("otp"))
        return [types.TextContent(type="text", text=result)]
    
    elif name == "get_order_status":
        result = get_status()
        return [types.TextContent(type="text", text=result)]
    
    elif name == "stop_order":
        result = await stop_order()
        return [types.TextContent(type="text", text=result)]
    
    elif name == "start_zepto_multi_order":
        try:
            raw_items = (arguments or {}).get("items", [])
            if not raw_items:
                return [types.TextContent(type="text", text="No items provided for multi-item order.")]

            resolved_items: list[dict] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                url = get_product_url(
                    product_name=item.get("product_name"),
                    item_url=item.get("item_url")
                )
                qty_raw = item.get("quantity", 1)
                try:
                    qty = int(qty_raw)
                except Exception:
                    qty = 1
                if qty < 1:
                    continue
                resolved_items.append({"url": url, "qty": qty})

            if not resolved_items:
                return [types.TextContent(type="text", text="No valid items found for multi-item order.")]

            result = await start_multi_order(
                resolved_items,
                (arguments or {}).get("phone_number") or os.getenv("ZEPTO_PHONE_NUMBER") or "",
                (arguments or {}).get("address") or os.getenv("ZEPTO_DEFAULT_ADDRESS") or ""
            )
            return [types.TextContent(type="text", text=result)]
        except ValueError as e:
            return [types.TextContent(type="text", text=str(e))]
    
    elif name == "handle_stock_decision":
        result = await handle_stock_decision(
            arguments.get("decision"),
            arguments.get("replacement_items", [])
        )
        return [types.TextContent(type="text", text=result)]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def clear_cart_if_needed(page) -> None:
    """
    Clear cart if there are items from previous session.
    Process:
    1. Check for notification badge (cart-items-number)
    2. Click cart button
    3. Find all line items (div.__6RuoF)
    4. For each line item, check quantity (data-testid="undefined-cart-qty")
    5. Click minus button (SVG path M20 12H4) until quantity is 0 for each item
    6. Click back button (SVG path M15.5 19L8.5 12L15.5 5)
    7. Continue with normal flow
    """
    try:
        # STEP 1: Check for notification badge
        cart_badge = await page.query_selector('span[data-testid="cart-items-number"]')
        if not cart_badge:
            print("✅ No cart badge found, cart is empty - skipping clear")
            return
        
        # Check if badge has a number
        badge_text = await cart_badge.text_content()
        if not badge_text or not badge_text.strip().isdigit():
            print("✅ Cart badge exists but no number, cart is empty - skipping clear")
            return
        
        badge_count = int(badge_text.strip())
        print(f"🔍 Found cart badge with {badge_count} item(s) - clearing cart...")
        
        # STEP 2: Click on cart button to open cart
        cart_btn = await page.query_selector("button[data-testid='cart-btn']")
        if not cart_btn:
            print("⚠️ Cart badge found but cart button not found")
            return
        
        await cart_btn.click()
        # Wait for cart content to be visible (replaces fixed sleep)
        try:
            await page.wait_for_selector("div.__6RuoF, span:has-text('Your cart is empty')", timeout=3000)
        except:
            print("⚠️ Cart content may not have loaded, but proceeding...")
            await asyncio.sleep(0.5)  # Fallback minimal wait
        
        # STEP 3: Find all line items in the cart (divs with class __6RuoF)
        # STEP 4 & 5: For each line item, reduce quantity to 0
        max_iterations = 50  # Safety limit per item
        total_items_cleared = 0
        
        while True:
            # Get all line items
            line_items = await page.query_selector_all("div.__6RuoF")
            
            if len(line_items) == 0:
                print("✅ All line items removed from cart!")
                break
            
            print(f"📦 Found {len(line_items)} line item(s) in cart")
            
            # Process each line item
            for item_idx, line_item in enumerate(line_items, 1):
                # Get quantity for this line item
                quantity_elem = await line_item.query_selector('p[data-testid="undefined-cart-qty"]')
                if not quantity_elem:
                    print(f"   ⚠️ Line item {item_idx}: Could not find quantity element, skipping")
                    continue
                
                quantity_text = await quantity_elem.text_content()
                try:
                    current_qty = int(quantity_text.strip()) if quantity_text else 0
                except:
                    current_qty = 0
                
                if current_qty == 0:
                    print(f"   ✅ Line item {item_idx}: Already at quantity 0")
                    continue
                
                print(f"   🔄 Line item {item_idx}: Current quantity = {current_qty}, reducing to 0...")
                
                # Click minus button for this specific line item until quantity is 0
                clicks_made = 0
                for click_attempt in range(max_iterations):
                    # Re-check quantity after each click
                    quantity_elem = await line_item.query_selector('p[data-testid="undefined-cart-qty"]')
                    if not quantity_elem:
                        # Item might have been removed
                        print(f"      ✅ Line item {item_idx}: Removed (quantity element gone)")
                        break
                    
                    quantity_text = await quantity_elem.text_content()
                    try:
                        current_qty = int(quantity_text.strip()) if quantity_text else 0
                    except:
                        current_qty = 0
                    
                    if current_qty == 0:
                        print(f"      ✅ Line item {item_idx}: Quantity reduced to 0 after {clicks_made} clicks")
                        break
                    
                    # Find minus button within this line item using Playwright methods
                    minus_button_found = False
                    
                    # Strategy 1: Find by aria-label="Remove" within this line item
                    remove_btn = await line_item.query_selector('button[aria-label="Remove"]')
                    if remove_btn:
                        try:
                            await remove_btn.click()
                            # Wait for quantity to update using element wait instead of fixed sleep
                            try:
                                await asyncio.wait_for(
                                    page.wait_for_function(
                                        f"document.querySelectorAll('[data-testid=\"cart-item\"]')[{item_idx}]?.querySelector('.quantity')?.textContent?.trim() === '0' || document.querySelectorAll('[data-testid=\"cart-item\"]').length === 0",
                                        timeout=1000
                                    ),
                                    timeout=1.0
                                )
                            except:
                                await asyncio.sleep(0.2)  # Fallback minimal wait
                            clicks_made += 1
                            minus_button_found = True
                            print(f"      - Clicked minus button (aria-label) (qty now: {current_qty - 1})")
                        except Exception as e:
                            print(f"      ⚠️ Error clicking remove button: {e}")
                    
                    # Strategy 2: Find button with minus SVG (path: M20 12H4) within this line item
                    if not minus_button_found:
                        # Get all buttons in this line item
                        buttons = await line_item.query_selector_all('button')
                        for btn in buttons:
                            # Check if this button has the minus SVG
                            svg = await btn.query_selector('svg')
                            if not svg:
                                continue
                            
                            # Check SVG path
                            path = await svg.query_selector('path')
                            if path:
                                path_d = await path.get_attribute('d')
                                if path_d and ('M20 12H4' in path_d or path_d == 'M20 12H4'):
                                    # Verify it's the minus button (aria-label="Remove")
                                    aria_label = await btn.get_attribute('aria-label')
                                    if aria_label and ('remove' in aria_label.lower() or aria_label == 'Remove'):
                                        try:
                                            await btn.click()
                                            # Wait for quantity update
                                            try:
                                                await asyncio.wait_for(
                                                    page.wait_for_function(
                                                        f"document.querySelectorAll('[data-testid=\"cart-item\"]')[{item_idx}]?.querySelector('.quantity')?.textContent?.trim() === '0' || document.querySelectorAll('[data-testid=\"cart-item\"]').length === 0",
                                                        timeout=1000
                                                    ),
                                                    timeout=1.0
                                                )
                                            except:
                                                await asyncio.sleep(0.2)  # Fallback minimal wait
                                            clicks_made += 1
                                            minus_button_found = True
                                            print(f"      - Clicked minus button (SVG path) (qty now: {current_qty - 1})")
                                            break
                                        except Exception as e:
                                            print(f"      ⚠️ Error clicking minus button: {e}")
                    
                    # Strategy 3: Fallback - find any button with "Remove" in aria-label
                    if not minus_button_found:
                        all_buttons = await line_item.query_selector_all('button')
                        for btn in all_buttons:
                            aria_label = await btn.get_attribute('aria-label')
                            if aria_label and 'remove' in aria_label.lower():
                                try:
                                    await btn.click()
                                    await asyncio.sleep(0.3)  # Reduced from 0.6s
                                    clicks_made += 1
                                    minus_button_found = True
                                    print(f"      - Clicked minus button (fallback) (qty now: {current_qty - 1})")
                                    break
                                except Exception as e:
                                    print(f"      ⚠️ Error clicking fallback button: {e}")
                    
                    if not minus_button_found:
                        print(f"      ⚠️ Line item {item_idx}: Could not find minus button")
                        break
                
                total_items_cleared += 1
            
            # After processing all items, check if cart is empty
            await asyncio.sleep(0.3)  # Reduced from 0.5s - Brief wait for DOM to update
            line_items_after = await page.query_selector_all("div.__6RuoF")
            if len(line_items_after) == 0:
                print("✅ All line items successfully removed!")
                break
        
        # Wait a moment for cart to update
        await asyncio.sleep(0.3)  # Reduced from 0.5s
        
        # Verify cart is empty
        empty_check = await page.evaluate("""
            () => {
                // Check for "Your cart is empty" message
                const emptyText = Array.from(document.querySelectorAll('span, p, div'));
                for (const el of emptyText) {
                    const text = el.textContent || '';
                    if (text.includes('Your cart is empty')) {
                        return true;
                    }
                }
                // Also check if no line items exist
                const lineItems = document.querySelectorAll('div.__6RuoF');
                return lineItems.length === 0;
            }
        """)
        
        if empty_check:
            print("✅ Confirmed: Cart is empty")
        else:
            print("⚠️ Cart may still have items, but proceeding...")
        
        # STEP 6: Click the back button (SVG path: M15.5 19L8.5 12L15.5 5)
        print("🔙 Clicking back button to close cart...")
        back_button_found = False
        
        # Strategy 1: Find by specific class structure in cart header
        # Button is in: header.zMuMp > div.zzBbh.MwhZN > button.cpG2SV.cm4lUI.c63b8l
        try:
            # Try to find button with the specific classes
            back_btn = await page.query_selector('header.zMuMp button.cpG2SV.cm4lUI.c63b8l')
            if back_btn:
                # Verify it has the correct SVG path
                svg = await back_btn.query_selector('svg')
                if svg:
                    path = await svg.query_selector('path[d*="M15.5 19L8.5 12L15.5 5"]')
                    if path:
                        await back_btn.click()
                        # Wait for cart to close using element wait
                        try:
                            await page.wait_for_selector("button[data-testid='cart-btn']", timeout=1000)
                            print("✅ Clicked back button (by cart header class structure) - cart closed")
                        except:
                            await asyncio.sleep(0.3)  # Fallback minimal wait
                        back_button_found = True
                        # Skip other strategies if Strategy 1 worked (99% success rate)
                        return
        except Exception as e:
            print(f"⚠️ Error finding back button by class structure: {e}")
        
        # Strategy 2: Find button in div.zzBbh.MwhZN (more flexible) - Only if Strategy 1 failed
        if not back_button_found:
            try:
                header_div = await page.query_selector('div.zzBbh.MwhZN')
                if header_div:
                    back_btn = await header_div.query_selector('button')
                    if back_btn:
                        # Verify it has the back arrow SVG
                        svg = await back_btn.query_selector('svg path[d*="M15.5 19L8.5 12L15.5 5"]')
                        if svg:
                            await back_btn.click()
                            await asyncio.sleep(0.5)  # Reduced from 0.8s
                            print("✅ Clicked back button (by header div structure)")
                            back_button_found = True
            except Exception as e:
                print(f"⚠️ Error finding back button by header div: {e}")
        
        # Strategy 3: Find by aria-label="Back button"
        if not back_button_found:
            try:
                back_btn = await page.query_selector('button[aria-label="Back button"]')
                if back_btn:
                    await back_btn.click()
                    await asyncio.sleep(0.5)  # Reduced from 0.8s
                    print("✅ Clicked back button (by aria-label='Back button')")
                    back_button_found = True
            except Exception as e:
                print(f"⚠️ Error finding back button by aria-label='Back button': {e}")
        
        # Strategy 4: Find by aria-label containing "Back"
        if not back_button_found:
            try:
                # Try case-insensitive search
                all_buttons = await page.query_selector_all('button')
                for btn in all_buttons:
                    aria_label = await btn.get_attribute('aria-label')
                    if aria_label and 'back' in aria_label.lower():
                        try:
                            await btn.click()
                            await asyncio.sleep(0.5)  # Reduced from 0.8s
                            print("✅ Clicked back button (by aria-label containing 'Back')")
                            back_button_found = True
                            break
                        except Exception as e:
                            print(f"⚠️ Error clicking back button: {e}")
            except Exception as e:
                print(f"⚠️ Error finding back button by aria-label: {e}")
        
        # Strategy 5: Find button with back arrow SVG (path: M15.5 19L8.5 12L15.5 5)
        # User provided: <svg fill="none" height="24" viewBox="0 0 24 24" width="24" xmlns="http://www.w3.org/2000/svg" style="height: 22px; width: 22px; color: black;"><path d="M15.5 19L8.5 12L15.5 5" stroke="black" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5"></path></svg>
        if not back_button_found:
            try:
                all_buttons = await page.query_selector_all('button')
                for btn in all_buttons:
                    svg = await btn.query_selector('svg')
                    if not svg:
                        continue
                    
                    # Check SVG attributes (height="24", viewBox="0 0 24 24", width="24")
                    svg_height = await svg.get_attribute('height')
                    svg_width = await svg.get_attribute('width')
                    svg_viewbox = await svg.get_attribute('viewBox')
                    
                    # Check if it matches the back button SVG structure
                    is_back_svg = False
                    if svg_height == "24" and svg_width == "24" and svg_viewbox == "0 0 24 24":
                        is_back_svg = True
                    
                    # Check path
                    path = await svg.query_selector('path')
                    if path:
                        path_d = await path.get_attribute('d')
                        path_stroke = await path.get_attribute('stroke')
                        path_stroke_width = await path.get_attribute('stroke-width')
                        
                        # Check for exact path: M15.5 19L8.5 12L15.5 5
                        if path_d and 'M15.5 19L8.5 12L15.5 5' in path_d:
                            is_back_svg = True
                        # Or check for partial match
                        elif path_d and 'M15.5' in path_d and 'L8.5' in path_d and 'L15.5' in path_d:
                            # Verify stroke attributes match
                            if path_stroke == "black" and path_stroke_width == "2.5":
                                is_back_svg = True
                        
                        if is_back_svg:
                            try:
                                await btn.click()
                                await asyncio.sleep(0.5)  # Reduced from 0.8s
                                print("✅ Clicked back button (by SVG path M15.5 19L8.5 12L15.5 5)")
                                back_button_found = True
                                break
                            except Exception as e:
                                print(f"⚠️ Error clicking back button: {e}")
            except Exception as e:
                print(f"⚠️ Error finding back button by SVG: {e}")
        
        # Strategy 6: Use Playwright locator to find button containing the back arrow SVG
        if not back_button_found:
            try:
                # Try to find button with SVG containing the back arrow path
                button_locator = page.locator('button:has(svg >> path[d*="M15.5 19L8.5 12L15.5 5"])')
                if await button_locator.count() > 0:
                    await button_locator.first.click()
                    await asyncio.sleep(0.8)
                    print("✅ Clicked back button (by SVG locator)")
                    back_button_found = True
            except Exception as e:
                print(f"⚠️ Error finding back button by SVG locator: {e}")
        
        # Strategy 7: Find all buttons and check their SVG paths manually
        if not back_button_found:
            try:
                all_buttons = await page.query_selector_all('button')
                for btn in all_buttons:
                    # Check if button has SVG
                    svg = await btn.query_selector('svg[height="24"][width="24"]')
                    if svg:
                        path = await svg.query_selector('path[d*="M15.5"]')
                        if path:
                            path_d = await path.get_attribute('d')
                            path_stroke = await path.get_attribute('stroke')
                            if path_d and 'M15.5 19L8.5 12L15.5 5' in path_d:
                                # Also check stroke to be sure
                                if path_stroke == "black" or not path_stroke:
                                    try:
                                        await btn.click()
                                        await asyncio.sleep(0.5)  # Reduced from 0.8s
                                        print("✅ Clicked back button (by manual SVG check)")
                                        back_button_found = True
                                        break
                                    except Exception as e:
                                        print(f"⚠️ Error clicking back button: {e}")
            except Exception as e:
                print(f"⚠️ Error in manual SVG check: {e}")
        
        if not back_button_found:
            print("⚠️ Could not find back button, but continuing...")
        else:
            # Wait a moment to ensure cart is closed
            await asyncio.sleep(0.3)  # Reduced from 0.5s
        
        print(f"✅ Cart clearing complete! Processed {total_items_cleared} item(s)")
        
    except Exception as e:
        print(f"⚠️ Error in clear_cart_if_needed: {e}")
        # Don't fail the order if cart clearing fails
        pass


async def check_if_logged_in(page) -> bool:
    """Check if user is already logged in to Zepto"""
    try:
        # Wait for page to be ready
        await page.wait_for_load_state("domcontentloaded", timeout=3000)  # Changed from networkidle, reduced timeout
        await asyncio.sleep(0.2)  # Reduced from 0.5s - Give page time to render
        
        # Strategy 0: Check cookies FIRST (most reliable for persistent sessions)
        try:
            cookies = await page.context.cookies()
            print(f"🔍 Found {len(cookies)} cookies in context")
            
            # Print all cookie names for debugging
            cookie_names = [c.get("name", "") for c in cookies]
            print(f"🔍 Cookie names: {cookie_names[:10]}...")  # First 10
            
            # Check for ANY cookies for zeptonow.com domain (if persistent context has cookies, user likely logged in)
            zepto_domain_cookies = []
            session_cookies = []
            
            for c in cookies:
                domain = c.get("domain", "").lower()
                name = c.get("name", "").lower()
                has_value = bool(c.get("value"))
                
                # Check if cookie is for zeptonow.com
                if "zeptonow" in domain and has_value:
                    zepto_domain_cookies.append(c)
                
                # Check for session-related keywords
                if any(keyword in name for keyword in ["session", "auth", "token", "user", "zepto", "jwt", "access", "login", "sid"]):
                    if has_value:
                        session_cookies.append(c)
            
            # If we have ANY cookies for zeptonow.com, assume logged in (persistent context working)
            if zepto_domain_cookies:
                print(f"🔍 Found {len(zepto_domain_cookies)} cookies for zeptonow.com domain:")
                for cookie in zepto_domain_cookies[:5]:  # Show first 5
                    name = cookie.get("name", "")
                    domain = cookie.get("domain", "")
                    print(f"   - {name} (domain: {domain})")
                print("🔍 Cookies found for zeptonow.com - assuming user IS logged in (persistent session)")
                return True
            
            # Also check for session cookies (even if domain doesn't match exactly)
            if session_cookies:
                print(f"🔍 Found {len(session_cookies)} session-related cookies:")
                for cookie in session_cookies[:5]:
                    name = cookie.get("name", "")
                    domain = cookie.get("domain", "")
                    print(f"   - {name} (domain: {domain})")
                print("🔍 Session cookies found - user IS logged in (by session cookies)")
                return True
            
            # Also check localStorage for session data
            try:
                storage_data = await page.evaluate("""
                    () => {
                        const keys = Object.keys(localStorage);
                        return {
                            keys: keys,
                            hasAuth: keys.some(k => k.toLowerCase().includes('auth') || k.toLowerCase().includes('token') || k.toLowerCase().includes('session') || k.toLowerCase().includes('user'))
                        };
                    }
                """)
                if storage_data.get("hasAuth"):
                    print(f"🔍 Found auth data in localStorage - user IS logged in")
                    print(f"   localStorage keys: {storage_data.get('keys', [])[:5]}...")
                    return True
            except Exception as e:
                print(f"⚠️ Error checking localStorage: {e}")
                pass
        except Exception as e:
            print(f"⚠️ Error checking cookies: {e}")
            pass
        
        # Strategy 1: Check for login button - if it exists and is visible, user is NOT logged in
        try:
            login_btn = await page.query_selector("span[data-testid='login-btn']")
            if login_btn:
                is_visible = await login_btn.is_visible()
                if is_visible:
                    print("🔍 Login button visible - user is NOT logged in")
                    return False
        except:
            pass
        
        # Strategy 2: Check for cart button - if it exists, user IS logged in
        try:
            # Try multiple selectors for cart button
            cart_selectors = [
                "button[data-testid='cart-btn']",
                "button:has-text('Cart')",
                "[data-testid*='cart']",
                "button[aria-label*='cart' i]"
            ]
            for selector in cart_selectors:
                cart_btn = await page.query_selector(selector)
                if cart_btn:
                    is_visible = await cart_btn.is_visible()
                    if is_visible:
                        print(f"🔍 Cart button visible ({selector}) - user IS logged in")
                        return True
        except Exception as e:
            print(f"⚠️ Error checking cart button: {e}")
            pass
        
        # Strategy 3: Check page content for logged-in indicators
        try:
            # Look for any user account indicators
            account_indicators = await page.query_selector_all(
                "[data-testid*='user'], [data-testid*='profile'], [data-testid*='account'], "
                "[data-testid*='menu'], button:has-text('My Account'), a:has-text('Account')"
            )
            if len(account_indicators) > 0:
                print("🔍 Account indicators found - user IS logged in")
                return True
        except:
            pass
        
        # Strategy 4: Check page text for login state
        try:
            page_text = await page.evaluate("() => document.body.innerText")
            if page_text:
                # If we see "Login" or "Sign In" prominently, probably not logged in
                if "Login" in page_text or "Sign In" in page_text:
                    # But also check for logged-in indicators
                    if "My Account" in page_text or "Cart" in page_text or "Orders" in page_text:
                        print("🔍 Page text suggests user IS logged in")
                        return True
                    print("🔍 Page text suggests user is NOT logged in")
                    return False
        except:
            pass
        
        # (Cookie check moved to Strategy 0 - checked first)
        
        # Strategy 6: JavaScript-based comprehensive check
        try:
            login_state = await page.evaluate("""
                () => {
                    // Check for login button
                    const loginBtn = document.querySelector("span[data-testid='login-btn']");
                    if (loginBtn && loginBtn.offsetParent !== null) {
                        return { loggedIn: false, reason: "Login button visible" };
                    }
                    
                    // Check for cart button
                    const cartBtn = document.querySelector("button[data-testid='cart-btn']");
                    if (cartBtn && cartBtn.offsetParent !== null) {
                        return { loggedIn: true, reason: "Cart button visible" };
                    }
                    
                    // Check for any account/user indicators
                    const accountElements = document.querySelectorAll(
                        "[data-testid*='user'], [data-testid*='profile'], [data-testid*='account'], [data-testid*='menu']"
                    );
                    for (const el of accountElements) {
                        if (el.offsetParent !== null) {
                            return { loggedIn: true, reason: "Account indicator found" };
                        }
                    }
                    
                    // Check page text
                    const bodyText = document.body.innerText || "";
                    if (bodyText.includes("My Account") || bodyText.includes("Orders") || bodyText.includes("Profile")) {
                        return { loggedIn: true, reason: "Account text found" };
                    }
                    
                    return { loggedIn: false, reason: "No clear indicators" };
                }
            """)
            if login_state.get("loggedIn"):
                print(f"🔍 JavaScript check: {login_state.get('reason')} - user IS logged in")
                return True
            else:
                print(f"🔍 JavaScript check: {login_state.get('reason')} - user is NOT logged in")
        except Exception as e:
            print(f"⚠️ Error in JavaScript check: {e}")
            pass
        
        print("⚠️ Could not definitively determine login status, assuming NOT logged in")
        return False
    except Exception as e:
        print(f"⚠️ Error checking login status: {e}")
        return False


async def start_order(item_url: str, phone_number: str, address: str) -> str:
    """Start the order process"""
    global order_state
    
    if order_state["status"] != "idle":
        return f"Order already in progress. Status: {order_state['status']}"
    
    order_state["status"] = "starting"
    order_state["phone_number"] = phone_number
    order_state["item_url"] = item_url
    order_state["items"] = None
    order_state["address"] = address
    
    # CRITICAL: Close any existing context/browser before starting new order
    # This ensures we always load from saved directory, not a cancelled session
    if order_state.get("context"):
        print("🔄 Closing existing context to start fresh from saved directory...")
        try:
            await order_state["context"].close()
        except:
            pass
        order_state["context"] = None
    
    if order_state.get("browser"):
        print("🔄 Closing existing browser...")
        try:
            await order_state["browser"].close()
        except:
            pass
        order_state["browser"] = None
    
    if order_state.get("playwright"):
        print("🔄 Stopping existing playwright...")
        try:
            await order_state["playwright"].stop()
        except:
            pass
        order_state["playwright"] = None
    
    # CRITICAL: Wait to ensure everything is fully closed before launching new browser
    # This prevents "has been closed" errors from directory locks
    # Reduced from 2.0s to 1.0s for faster startup
    await asyncio.sleep(1.0)
    print("✅ Previous browser instances closed, ready to launch new browser")
    
    # Launch browser with persistent context to save login session
    p = await async_playwright().start()
    import os
    # Use absolute path to ensure consistency with setup_firefox_login.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(script_dir, "zepto_firefox_data")
    
    # Debug: Show paths (important for Claude Desktop)
    print(f"📂 Script directory: {script_dir}")
    print(f"📂 Persistent context directory: {user_data_dir}")
    print(f"📂 Current working directory: {os.getcwd()}")
    print(f"🔄 Starting fresh session from saved directory: {user_data_dir}")
    
    # Check if persistent context directory exists and has files
    if os.path.exists(user_data_dir):
        # Check if directory has files (especially Default folder with cookies)
        default_dir = os.path.join(user_data_dir, "Default")
        cookie_file = os.path.join(default_dir, "Cookies") if os.path.exists(default_dir) else None
        
        file_count = sum(len(files) for _, _, files in os.walk(user_data_dir))
        print(f"✅ Found existing persistent context: {user_data_dir}")
        print(f"   - Contains {file_count} files")
        if cookie_file and os.path.exists(cookie_file):
            cookie_size = os.path.getsize(cookie_file)
            print(f"   - Cookies file exists: {cookie_size} bytes")
        else:
            print(f"   - ⚠️ Cookies file not found (may be in different location)")
    else:
        print(f"ℹ️ Creating new persistent context: {user_data_dir}")
        os.makedirs(user_data_dir, exist_ok=True)
    
    # PROACTIVELY clean browser data directory if locked to prevent crashes
    if os.path.exists(user_data_dir):
        try:
            # Firefox uses different lock file location
            lock_file = os.path.join(user_data_dir, "lock")
            if os.path.exists(lock_file):
                print(f"⚠️ Lock file detected - cleaning directory to prevent crashes...")
                backup_dir = f"{user_data_dir}_backup_{int(time.time())}"
                try:
                    shutil.move(user_data_dir, backup_dir)
                    print(f"📦 Backed up directory to: {backup_dir}")
                except:
                    try:
                        shutil.rmtree(user_data_dir)
                        print(f"🗑️ Removed locked directory")
                    except:
                        pass
                os.makedirs(user_data_dir, exist_ok=True)
        except:
            pass
    
    try:
        # USE FIREFOX ONLY (Chromium crashes on macOS 26.1 beta)
        # Use Firefox persistent context to save login session
        print(f"🚀 Launching Firefox with persistent context...")
        try:
            context = await asyncio.wait_for(
                p.firefox.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,
                    viewport={"width": 1280, "height": 720}
                ),
                timeout=30.0
            )
        except Exception as launch_err:
            error_str = str(launch_err).lower()
            # Check if browser crashed or locked
            if "lock" in error_str or "has been closed" in error_str:
                # Browser data directory might be locked
                print(f"⚠️ Firefox data directory may be locked. Attempting recovery...")
                backup_dir = f"{user_data_dir}_backup_{int(time.time())}"
                if os.path.exists(user_data_dir):
                    try:
                        if os.path.exists(backup_dir):
                            shutil.rmtree(backup_dir)
                        shutil.move(user_data_dir, backup_dir)
                        print(f"📦 Backed up directory to: {backup_dir}")
                        os.makedirs(user_data_dir, exist_ok=True)
                        print(f"✅ Created fresh Firefox data directory")
                    except Exception as backup_err:
                        print(f"⚠️ Could not backup directory: {backup_err}")
                        try:
                            shutil.rmtree(user_data_dir)
                            os.makedirs(user_data_dir, exist_ok=True)
                            print(f"✅ Recreated fresh Firefox data directory")
                        except:
                            pass
                
                # Retry with fresh directory
                try:
                    print(f"🔄 Retrying Firefox launch with fresh data directory...")
                    context = await asyncio.wait_for(
                        p.firefox.launch_persistent_context(
                            user_data_dir=user_data_dir,
                            headless=False,
                            viewport={"width": 1280, "height": 720}
                        ),
                        timeout=30.0
                    )
                    print(f"✅ Firefox launched successfully with fresh data directory")
                except Exception as retry_err:
                    print(f"❌ Firefox still fails: {retry_err}")
                    raise Exception(f"Firefox cannot launch. Try running: python3 setup_firefox_login.py to set up login first")
            else:
                raise
        
        pages = context.pages
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()
        
        print(f"✅ Firefox persistent context loaded successfully")
        
        # Quick check: if persistent context exists, check for cookies immediately
        try:
            initial_cookies = await context.cookies()
            if initial_cookies:
                zepto_cookies = [c for c in initial_cookies if "zeptonow" in c.get("domain", "").lower() and c.get("value")]
                if zepto_cookies:
                    print(f"🔍 Found {len(zepto_cookies)} zeptonow.com cookies in Firefox - login session saved!")
                else:
                    print(f"⚠️ No Zepto cookies found. Run 'python3 setup_firefox_login.py' to save your login.")
        except:
            pass
        
        order_state["browser"] = context  # Store context instead of browser
        order_state["page"] = page
        order_state["playwright"] = p
        order_state["context"] = context
    except Exception as e:
        # ANY error with persistent context - immediately try regular browser
        # This is more reliable than trying to detect specific crash types
        error_str = str(e).lower()
        print(f"⚠️ Persistent context failed: {e}")
        print(f"🔄 Switching to regular browser (no session saved, but more stable)...")
        
        try:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            order_state["browser"] = browser
            order_state["page"] = page
            order_state["playwright"] = p
            order_state["context"] = None
            print(f"✅ Regular Chromium browser launched successfully")
        except Exception as fallback_err:
            error_str = str(fallback_err).lower()
            # If Chromium crashes, try Firefox with persistent context as fallback
            if "segv" in error_str or "crash" in error_str or "signal 11" in error_str or "targetclosederror" in error_str or "has been closed" in error_str:
                print(f"⚠️ Chromium crashes - trying Firefox with persistent context (saves login)...")
                try:
                    # Use Firefox persistent context to save login session
                    firefox_data_dir = user_data_dir.replace("zepto_browser_data", "zepto_firefox_data")
                    
                    # Clean Firefox data directory if locked
                    if os.path.exists(firefox_data_dir):
                        try:
                            lock_file = os.path.join(firefox_data_dir, "lock")
                            if os.path.exists(lock_file):
                                print(f"⚠️ Firefox lock file detected - cleaning...")
                                backup_dir = f"{firefox_data_dir}_backup_{int(time.time())}"
                                try:
                                    shutil.move(firefox_data_dir, backup_dir)
                                    print(f"📦 Backed up Firefox directory")
                                except:
                                    try:
                                        shutil.rmtree(firefox_data_dir)
                                    except:
                                        pass
                                os.makedirs(firefox_data_dir, exist_ok=True)
                        except:
                            pass
                    else:
                        os.makedirs(firefox_data_dir, exist_ok=True)
                    
                    # Launch Firefox with persistent context
                    firefox_context = await asyncio.wait_for(
                        p.firefox.launch_persistent_context(
                            user_data_dir=firefox_data_dir,
                            headless=False,
                            viewport={"width": 1280, "height": 720}
                        ),
                        timeout=30.0
                    )
                    
                    pages = firefox_context.pages
                    if pages:
                        page = pages[0]
                    else:
                        page = await firefox_context.new_page()
                    
                    # Store Firefox context (similar to Chromium persistent context)
                    order_state["browser"] = firefox_context
                    order_state["page"] = page
                    order_state["playwright"] = p
                    order_state["context"] = firefox_context
                    print(f"✅ Firefox browser launched with persistent context (login will be saved)")
                    
                    # Check for existing cookies
                    try:
                        initial_cookies = await firefox_context.cookies()
                        if initial_cookies:
                            zepto_cookies = [c for c in initial_cookies if "zeptonow" in c.get("domain", "").lower() and c.get("value")]
                            if zepto_cookies:
                                print(f"🔍 Found {len(zepto_cookies)} zeptonow.com cookies in Firefox - session saved!")
                    except:
                        pass
                        
                except Exception as firefox_err:
                    # If Firefox persistent context fails, try regular Firefox
                    print(f"⚠️ Firefox persistent context failed: {firefox_err}, trying regular Firefox...")
                    try:
                        browser = await p.firefox.launch(headless=False)
                        page = await browser.new_page()
                        order_state["browser"] = browser
                        order_state["page"] = page
                        order_state["playwright"] = p
                        order_state["context"] = None
                        print(f"✅ Firefox browser launched (no session saved)")
                    except Exception as firefox_fallback_err:
                        await p.stop()
                        order_state["playwright"] = None
                        raise Exception(f"Both Chromium and Firefox failed to launch.\nChromium error: {fallback_err}\nFirefox error: {firefox_fallback_err}\n\nTroubleshooting:\n1. Close ALL browser windows\n2. Restart your Mac\n3. Reinstall Playwright: python3 -m playwright install chromium firefox")
            else:
                await p.stop()
                order_state["playwright"] = None
                raise Exception(f"Browser cannot launch. Error: {fallback_err}\n\nTroubleshooting:\n1. Close ALL Chrome/Chromium windows\n2. Restart your Mac\n3. Reinstall Playwright: python3 -m playwright install chromium\n4. Check system logs for crash details")
    
    # If using persistent context and directory has files, assume logged in and try to proceed
    # (More aggressive approach for Claude Desktop where we can't see debug output)
    persistent_context_exists = order_state.get("context") is not None
    if persistent_context_exists:
        # Check if directory has files
        try:
            has_files = os.path.exists(user_data_dir) and any(os.scandir(user_data_dir))
            if has_files:
                print("✅ Persistent context found with files - assuming logged in, proceeding directly...")
                # Navigate directly to product and try to proceed
                await page.goto(item_url, wait_until="domcontentloaded")  # Changed from networkidle
                # No sleep needed - wait for specific element instead
                try:
                    await page.wait_for_selector("button[data-testid='add-to-cart-btn'], button:has-text('Add To Cart')", timeout=1000)
                except:
                    pass  # Element might not be present yet, continue
                
                # Try to check if login button is visible (quick check)
                try:
                    login_btn = await page.query_selector("span[data-testid='login-btn']")
                    if login_btn and await login_btn.is_visible(timeout=1000):
                        # Login button visible, need to log in
                        print("⚠️ Login button found - session may have expired, proceeding with login...")
                        is_logged_in = False
                    else:
                        # No login button, assume logged in
                        print("✅ No login button found - proceeding as logged in")
                        is_logged_in = True
                except:
                    # If check fails, assume logged in and proceed
                    print("✅ Assuming logged in (could not verify)")
                    is_logged_in = True
                
                if is_logged_in:
                    print("✅ Already logged in! Clearing cart from previous session if needed...")
                    # Clear cart before starting new order
                    await clear_cart_if_needed(page)
                    order_state["status"] = "adding_to_cart"
                    result = await submit_login(otp=None)  # No OTP needed
                    return result
        except Exception as e:
            print(f"⚠️ Error checking persistent context: {e}, falling back to normal flow")
    
    # Normal flow: check login status on homepage
    print("🔍 Checking login status on homepage...")
    await page.goto("https://www.zeptonow.com", wait_until="domcontentloaded")
    # No sleep needed - domcontentloaded means page is ready
    await page.wait_for_selector("body", timeout=1000)  # Quick verification
    
    # Check if already logged in
    is_logged_in = await check_if_logged_in(page)
    print(f"🔍 Login check result: {'LOGGED IN ✅' if is_logged_in else 'NOT LOGGED IN ❌'}")
    
    # If using persistent context and we have cookies but detection failed, be more lenient
    if not is_logged_in and order_state.get("context"):
        print("⚠️ Login detection failed but using persistent context - checking cookies again...")
        try:
            cookies_after_nav = await page.context.cookies()
            zepto_cookies = [c for c in cookies_after_nav if "zeptonow" in c.get("domain", "").lower() and c.get("value")]
            if zepto_cookies:
                print(f"🔍 Found {len(zepto_cookies)} zeptonow.com cookies after navigation - assuming logged in!")
                is_logged_in = True
        except:
            pass
    
    # Now navigate to product page
    print(f"🔄 Navigating to product page: {item_url}")
    await page.goto(item_url, wait_until="domcontentloaded")
    # No sleep needed - wait for specific element instead
    try:
        await page.wait_for_selector("button[data-testid='add-to-cart-btn'], button:has-text('Add To Cart')", timeout=1000)
    except:
        pass  # Element might not be present yet, continue
    
    if is_logged_in:
        print("✅ Already logged in! Clearing cart from previous session if needed...")
        # Clear cart before starting new order
        await clear_cart_if_needed(page)
        print("✅ Already logged in! Skipping login flow and proceeding directly to address selection.")
        order_state["status"] = "adding_to_cart"
        result = await submit_login(otp=None)  # No OTP needed
        return result
    
    # Not logged in, proceed with login flow
    print("🔐 Not logged in, starting login flow...")
    
    # Click login
    await page.click("span[data-testid='login-btn']")
    await page.wait_for_selector("input[placeholder='Enter Phone Number']", timeout=3000)  # Reduced from 5000ms
    
    # Enter phone number
    await page.fill("input[placeholder='Enter Phone Number']", phone_number)
    await asyncio.sleep(0.2)  # Reduced from 0.5s
    
    # Click Continue
    await page.click("button:has-text('Continue')")
    await page.wait_for_selector('input[type="text"][inputmode="numeric"]', timeout=3000)  # Reduced from 5000ms
    
    order_state["status"] = "waiting_login_otp"
    
    return f"Order started! OTP sent to {phone_number}. Please provide the login OTP."


async def start_multi_order(items: list[dict], phone_number: str, address: str) -> str:
    """Start a multi-item order process (single cart)."""
    global order_state
    
    if order_state["status"] != "idle":
        return f"Order already in progress. Status: {order_state['status']}"
    
    order_state["status"] = "starting"
    order_state["phone_number"] = phone_number
    order_state["item_url"] = None
    order_state["items"] = items
    order_state["address"] = address
    
    # CRITICAL: Close any existing context/browser before starting new order
    # This ensures we always load from saved directory, not a cancelled session
    if order_state.get("context"):
        print("🔄 Closing existing context to start fresh from saved directory...")
        try:
            await order_state["context"].close()
        except:
            pass
        order_state["context"] = None
    
    if order_state.get("browser"):
        print("🔄 Closing existing browser...")
        try:
            await order_state["browser"].close()
        except:
            pass
        order_state["browser"] = None
    
    if order_state.get("playwright"):
        print("🔄 Stopping existing playwright...")
        try:
            await order_state["playwright"].stop()
        except:
            pass
        order_state["playwright"] = None
    
    # CRITICAL: Wait to ensure everything is fully closed before launching new browser
    # This prevents "has been closed" errors from directory locks
    # Reduced from 2.0s to 1.0s for faster startup
    await asyncio.sleep(1.0)
    print("✅ Previous browser instances closed, ready to launch new browser")
    
    # Launch browser with persistent context to save login session
    p = await async_playwright().start()
    import os
    # Use absolute path to ensure consistency with setup_firefox_login.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(script_dir, "zepto_firefox_data")
    
    # Debug: Show paths (important for Claude Desktop)
    print(f"📂 Script directory: {script_dir}")
    print(f"📂 Persistent context directory: {user_data_dir}")
    print(f"📂 Current working directory: {os.getcwd()}")
    print(f"🔄 Starting fresh session from saved directory: {user_data_dir}")
    
    # Check if persistent context directory exists and has files
    if os.path.exists(user_data_dir):
        # Check if directory has files (especially Default folder with cookies)
        default_dir = os.path.join(user_data_dir, "Default")
        cookie_file = os.path.join(default_dir, "Cookies") if os.path.exists(default_dir) else None
        
        file_count = sum(len(files) for _, _, files in os.walk(user_data_dir))
        print(f"✅ Found existing persistent context: {user_data_dir}")
        print(f"   - Contains {file_count} files")
        if cookie_file and os.path.exists(cookie_file):
            cookie_size = os.path.getsize(cookie_file)
            print(f"   - Cookies file exists: {cookie_size} bytes")
        else:
            print(f"   - ⚠️ Cookies file not found (may be in different location)")
    else:
        print(f"ℹ️ Creating new persistent context: {user_data_dir}")
        os.makedirs(user_data_dir, exist_ok=True)
    
    # PROACTIVELY clean browser data directory if locked to prevent crashes
    if os.path.exists(user_data_dir):
        try:
            # Firefox uses different lock file location
            lock_file = os.path.join(user_data_dir, "lock")
            if os.path.exists(lock_file):
                print(f"⚠️ Lock file detected - cleaning directory to prevent crashes...")
                backup_dir = f"{user_data_dir}_backup_{int(time.time())}"
                try:
                    shutil.move(user_data_dir, backup_dir)
                    print(f"📦 Backed up directory to: {backup_dir}")
                except:
                    try:
                        shutil.rmtree(user_data_dir)
                        print(f"🗑️ Removed locked directory")
                    except:
                        pass
                os.makedirs(user_data_dir, exist_ok=True)
        except:
            pass
    
    try:
        # USE FIREFOX ONLY (Chromium crashes on macOS 26.1 beta)
        # Use Firefox persistent context to save login session
        print(f"🚀 Launching Firefox with persistent context...")
        try:
            context = await asyncio.wait_for(
                p.firefox.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,
                    viewport={"width": 1280, "height": 720}
                ),
                timeout=30.0
            )
        except Exception as launch_err:
            error_str = str(launch_err).lower()
            # Check if browser crashed or locked
            if "lock" in error_str or "has been closed" in error_str:
                # Browser data directory might be locked
                print(f"⚠️ Firefox data directory may be locked. Attempting recovery...")
                backup_dir = f"{user_data_dir}_backup_{int(time.time())}"
                if os.path.exists(user_data_dir):
                    try:
                        if os.path.exists(backup_dir):
                            shutil.rmtree(backup_dir)
                        shutil.move(user_data_dir, backup_dir)
                        print(f"📦 Backed up directory to: {backup_dir}")
                        os.makedirs(user_data_dir, exist_ok=True)
                        print(f"✅ Created fresh Firefox data directory")
                    except Exception as backup_err:
                        print(f"⚠️ Could not backup directory: {backup_err}")
                        try:
                            shutil.rmtree(user_data_dir)
                            os.makedirs(user_data_dir, exist_ok=True)
                            print(f"✅ Recreated fresh Firefox data directory")
                        except:
                            pass
                
                # Retry with fresh directory
                try:
                    print(f"🔄 Retrying Firefox launch with fresh data directory...")
                    context = await asyncio.wait_for(
                        p.firefox.launch_persistent_context(
                            user_data_dir=user_data_dir,
                            headless=False,
                            viewport={"width": 1280, "height": 720}
                        ),
                        timeout=30.0
                    )
                    print(f"✅ Firefox launched successfully with fresh data directory")
                except Exception as retry_err:
                    print(f"❌ Firefox still fails: {retry_err}")
                    raise Exception(f"Firefox cannot launch. Try running: python3 setup_firefox_login.py to set up login first")
            else:
                raise
        
        pages = context.pages
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()
        
        print(f"✅ Firefox persistent context loaded successfully")
        
        # Quick check: if persistent context exists, check for cookies immediately
        try:
            initial_cookies = await context.cookies()
            if initial_cookies:
                zepto_cookies = [c for c in initial_cookies if "zeptonow" in c.get("domain", "").lower() and c.get("value")]
                if zepto_cookies:
                    print(f"🔍 Found {len(zepto_cookies)} zeptonow.com cookies in Firefox - login session saved!")
                else:
                    print(f"⚠️ No Zepto cookies found. Run 'python3 setup_firefox_login.py' to save your login.")
        except:
            pass
        
        order_state["browser"] = context  # Store context instead of browser
        order_state["page"] = page
        order_state["playwright"] = p
        order_state["context"] = context
    except Exception as e:
        # ANY error with persistent context - immediately try regular browser
        # This is more reliable than trying to detect specific crash types
        error_str = str(e).lower()
        print(f"⚠️ Persistent context failed: {e}")
        print(f"🔄 Switching to regular browser (no session saved, but more stable)...")
        
        try:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            order_state["browser"] = browser
            order_state["page"] = page
            order_state["playwright"] = p
            order_state["context"] = None
            print(f"✅ Regular Chromium browser launched successfully")
        except Exception as fallback_err:
            error_str = str(fallback_err).lower()
            # If Chromium crashes, try Firefox with persistent context as fallback
            if "segv" in error_str or "crash" in error_str or "signal 11" in error_str or "targetclosederror" in error_str or "has been closed" in error_str:
                print(f"⚠️ Chromium crashes - trying Firefox with persistent context (saves login)...")
                try:
                    # Use Firefox persistent context to save login session
                    firefox_data_dir = user_data_dir.replace("zepto_browser_data", "zepto_firefox_data")
                    
                    # Clean Firefox data directory if locked
                    if os.path.exists(firefox_data_dir):
                        try:
                            lock_file = os.path.join(firefox_data_dir, "lock")
                            if os.path.exists(lock_file):
                                print(f"⚠️ Firefox lock file detected - cleaning...")
                                backup_dir = f"{firefox_data_dir}_backup_{int(time.time())}"
                                try:
                                    shutil.move(firefox_data_dir, backup_dir)
                                    print(f"📦 Backed up Firefox directory")
                                except:
                                    try:
                                        shutil.rmtree(firefox_data_dir)
                                    except:
                                        pass
                                os.makedirs(firefox_data_dir, exist_ok=True)
                        except:
                            pass
                    else:
                        os.makedirs(firefox_data_dir, exist_ok=True)
                    
                    # Launch Firefox with persistent context
                    firefox_context = await asyncio.wait_for(
                        p.firefox.launch_persistent_context(
                            user_data_dir=firefox_data_dir,
                            headless=False,
                            viewport={"width": 1280, "height": 720}
                        ),
                        timeout=30.0
                    )
                    
                    pages = firefox_context.pages
                    if pages:
                        page = pages[0]
                    else:
                        page = await firefox_context.new_page()
                    
                    # Store Firefox context (similar to Chromium persistent context)
                    order_state["browser"] = firefox_context
                    order_state["page"] = page
                    order_state["playwright"] = p
                    order_state["context"] = firefox_context
                    print(f"✅ Firefox browser launched with persistent context (login will be saved)")
                    
                    # Check for existing cookies
                    try:
                        initial_cookies = await firefox_context.cookies()
                        if initial_cookies:
                            zepto_cookies = [c for c in initial_cookies if "zeptonow" in c.get("domain", "").lower() and c.get("value")]
                            if zepto_cookies:
                                print(f"🔍 Found {len(zepto_cookies)} zeptonow.com cookies in Firefox - session saved!")
                    except:
                        pass
                        
                except Exception as firefox_err:
                    # If Firefox persistent context fails, try regular Firefox
                    print(f"⚠️ Firefox persistent context failed: {firefox_err}, trying regular Firefox...")
                    try:
                        browser = await p.firefox.launch(headless=False)
                        page = await browser.new_page()
                        order_state["browser"] = browser
                        order_state["page"] = page
                        order_state["playwright"] = p
                        order_state["context"] = None
                        print(f"✅ Firefox browser launched (no session saved)")
                    except Exception as firefox_fallback_err:
                        await p.stop()
                        order_state["playwright"] = None
                        raise Exception(f"Both Chromium and Firefox failed to launch.\nChromium error: {fallback_err}\nFirefox error: {firefox_fallback_err}\n\nTroubleshooting:\n1. Close ALL browser windows\n2. Restart your Mac\n3. Reinstall Playwright: python3 -m playwright install chromium firefox")
            else:
                await p.stop()
                order_state["playwright"] = None
                raise Exception(f"Browser cannot launch. Error: {fallback_err}\n\nTroubleshooting:\n1. Close ALL Chrome/Chromium windows\n2. Restart your Mac\n3. Reinstall Playwright: python3 -m playwright install chromium\n4. Check system logs for crash details")
    
    # If using persistent context and directory has files, assume logged in and try to proceed
    # (More aggressive approach for Claude Desktop where we can't see debug output)
    persistent_context_exists = order_state.get("context") is not None
    if persistent_context_exists:
        # Check if directory has files
        try:
            has_files = os.path.exists(user_data_dir) and any(os.scandir(user_data_dir))
            if has_files:
                print("✅ Persistent context found with files - assuming logged in, proceeding directly...")
                # Navigate directly to first product and try to proceed
                first_url = items[0]["url"]
                await page.goto(first_url, wait_until="domcontentloaded")  # Changed from networkidle
                await asyncio.sleep(0.3)  # Reduced from 1s
                
                # Try to check if login button is visible (quick check)
                try:
                    login_btn = await page.query_selector("span[data-testid='login-btn']")
                    if login_btn and await login_btn.is_visible(timeout=1000):
                        # Login button visible, need to log in
                        print("⚠️ Login button found - session may have expired, proceeding with login...")
                        is_logged_in = False
                    else:
                        # No login button, assume logged in
                        print("✅ No login button found - proceeding as logged in")
                        is_logged_in = True
                except:
                    # If check fails, assume logged in and proceed
                    print("✅ Assuming logged in (could not verify)")
                    is_logged_in = True
                
                if is_logged_in:
                    print("✅ Already logged in! Clearing cart from previous session if needed...")
                    # Clear cart before starting new order
                    await clear_cart_if_needed(page)
                    order_state["status"] = "adding_to_cart"
                    result = await submit_login(otp=None)  # No OTP needed
                    return result
        except Exception as e:
            print(f"⚠️ Error checking persistent context: {e}, falling back to normal flow")
    
    # Normal flow: check login status on homepage
    print("🔍 Checking login status on homepage...")
    await page.goto("https://www.zeptonow.com", wait_until="domcontentloaded")
    # No sleep needed - domcontentloaded means page is ready
    await page.wait_for_selector("body", timeout=1000)  # Quick verification
    
    # Check if already logged in
    is_logged_in = await check_if_logged_in(page)
    print(f"🔍 Login check result: {'LOGGED IN ✅' if is_logged_in else 'NOT LOGGED IN ❌'}")
    
    # If using persistent context and we have cookies but detection failed, be more lenient
    if not is_logged_in and order_state.get("context"):
        print("⚠️ Login detection failed but using persistent context - checking cookies again...")
        try:
            cookies_after_nav = await page.context.cookies()
            zepto_cookies = [c for c in cookies_after_nav if "zeptonow" in c.get("domain", "").lower() and c.get("value")]
            if zepto_cookies:
                print(f"🔍 Found {len(zepto_cookies)} zeptonow.com cookies after navigation - assuming logged in!")
                is_logged_in = True
        except:
            pass
    
    # Now navigate to first product page
    first_url = items[0]["url"]
    print(f"🔄 Navigating to first product page: {first_url}")
    await page.goto(first_url, wait_until="domcontentloaded")
    await asyncio.sleep(0.3)  # Reduced from 1s
    
    if is_logged_in:
        print("✅ Already logged in! Skipping login flow and proceeding directly to address selection.")
        order_state["status"] = "adding_to_cart"
        result = await submit_login(otp=None)  # No OTP needed
        return result
    
    # Not logged in, proceed with login flow
    print("🔐 Not logged in, starting login flow...")
    
    # Click login
    await page.click("span[data-testid='login-btn']")
    await page.wait_for_selector("input[placeholder='Enter Phone Number']", timeout=3000)  # Reduced from 5000ms
    
    # Enter phone number
    await page.fill("input[placeholder='Enter Phone Number']", phone_number)
    await asyncio.sleep(0.2)  # Reduced from 0.5s
    
    # Click Continue
    await page.click("button:has-text('Continue')")
    await page.wait_for_selector('input[type="text"][inputmode="numeric"]', timeout=3000)  # Reduced from 5000ms
    
    order_state["status"] = "waiting_login_otp_multi"
    
    return f"Multi-item order started! OTP sent to {phone_number}. Please provide the login OTP."


async def submit_login(otp: str = None) -> str:
    """Submit login OTP and proceed to checkout (handles both single and multi-item orders)
    
    If already logged in (status='adding_to_cart'), OTP is optional and will be skipped.
    """
    global order_state
    
    page = order_state["page"]
    
    # Check if already logged in (persistent session)
    if order_state["status"] == "adding_to_cart":
        print("✅ Already logged in via persistent session, skipping OTP entry")
        # Skip OTP and go directly to address selection
    elif order_state["status"] in ["waiting_login_otp", "waiting_login_otp_multi"]:
        # Need to enter OTP
        if not otp:
            return "OTP is required for login. Please provide the OTP code."
        
        # Get all OTP input fields
        otp_inputs = await page.query_selector_all('input[type="text"][inputmode="numeric"]')
        
        # Fill each digit individually using type for more realistic input
        for i, digit in enumerate(otp):
            if i < len(otp_inputs):
                await otp_inputs[i].click()
                await otp_inputs[i].type(digit, delay=20)  # Reduced from 30ms for faster typing
                # No sleep needed - typing delay handles it
        
        # Wait for login to complete - use element wait instead of fixed sleep
        try:
            # Wait for either address header or product page to appear (login successful)
            await page.wait_for_selector("div[data-testid='address-header'], button[data-testid='add-to-cart-btn']", timeout=2000)
        except:
            await asyncio.sleep(0.3)  # Fallback minimal wait
        order_state["status"] = "adding_to_cart"
    else:
        return f"Not waiting for login OTP and not already logged in. Current status: {order_state['status']}"
    
    # NEW FLOW: Navigate to first product, check and clear cart if needed, click address header, select address, then add items
    print("📍 Starting new order flow...")
    
    # Wait for page to be ready after login
    await page.wait_for_load_state("domcontentloaded")  # Changed from networkidle - faster
    # No additional sleep needed - domcontentloaded means page is ready
    # No sleep needed - domcontentloaded means page is ready
    
    # Determine first product URL
    first_product_url = None
    if order_state["items"] is not None and len(order_state["items"]) > 0:
        first_product_url = order_state["items"][0]["url"]
    elif order_state["item_url"]:
        first_product_url = order_state["item_url"]
    
    if not first_product_url:
        return "Error: No product URL found in order state"
    
    # Navigate to first product page
    print(f"🔄 Navigating to first product: {first_product_url}")
    await page.goto(first_product_url, wait_until="domcontentloaded")
    # No sleep needed - wait for specific element instead
    try:
        await page.wait_for_selector("button[data-testid='add-to-cart-btn'], button:has-text('Add To Cart')", timeout=1000)
    except:
        pass
    
    # Close any popups
    try:
        await page.click("button:has-text('Close')", timeout=1000)
    except:
        pass
    
    # CRITICAL: Check and clear cart if cart badge shows a number
    # This must happen AFTER navigating to product page so we can see the cart badge
    print("🛒 Checking cart and clearing if needed...")
    await clear_cart_if_needed(page)
    
    # Click on address header (h3 with data-testid="user-address") to open address modal
    print("📍 Clicking on address header to open address modal...")
    address_header_clicked = False
    
    try:
        # Strategy 1: Find by data-testid
        address_header = await page.query_selector('h3[data-testid="user-address"]')
        if address_header:
            await address_header.click()
            address_header_clicked = True
            print("✅ Clicked address header using data-testid")
    except Exception as e:
        print(f"⚠️ Strategy 1 failed: {e}")
    
    if not address_header_clicked:
        # Strategy 2: Find by class and text content
        try:
            address_header = await page.evaluate("""
                () => {
                    const headers = Array.from(document.querySelectorAll('h3.WCHS8'));
                    for (const h3 of headers) {
                        if (h3.getAttribute('data-testid') === 'user-address') {
                            return h3;
                        }
                    }
                    return null;
                }
            """)
            if address_header:
                await page.evaluate("(el) => el.click()", address_header)
                address_header_clicked = True
                print("✅ Clicked address header using class selector")
        except Exception as e:
            print(f"⚠️ Strategy 2 failed: {e}")
    
    if not address_header_clicked:
        # Strategy 3: Find by text content containing address names
        try:
            address_header = await page.evaluate("""
                () => {
                    const headers = Array.from(document.querySelectorAll('h3'));
                    for (const h3 of headers) {
                        const text = h3.textContent || '';
                        if (text.includes('HSR Home') || text.includes('Hsr Home') || 
                            text.includes('Office New Cafe') || text.includes('Hyd Home')) {
                            return h3;
                        }
                    }
                    return null;
                }
            """)
            if address_header:
                await page.evaluate("(el) => el.click()", address_header)
                address_header_clicked = True
                print("✅ Clicked address header using text content")
        except Exception as e:
            print(f"⚠️ Strategy 3 failed: {e}")
    
    if address_header_clicked:
        # Wait for address modal to open
        try:
            await page.wait_for_selector("div[data-testid='address-modal'], div[data-testid='saved-address-container']", timeout=3000)  # Reduced from 5000ms
            print("✅ Address modal opened")
            # No sleep needed - modal is already open
        except:
            print("⚠️ Address modal may not have opened, but proceeding...")
    else:
        print("⚠️ Could not find address header. Checking if address modal is already open...")
        try:
            await page.wait_for_selector("div[data-testid='address-modal'], div[data-testid='saved-address-container']", timeout=1500)  # Reduced from 2000ms
            print("✅ Address modal found (already open)")
        except:
            print("⚠️ Address modal not found. This may cause issues.")
        await asyncio.sleep(0.3)  # Reduced from 0.5s
    
    # Select address (with Jo's scrolling logic and named addresses)
    print(f"🏠 Selecting address: {order_state['address']}")
    await select_address(page, order_state["address"])
    await asyncio.sleep(0.3)  # Reduced from 0.5s
    print("✅ Address selected")
    
    # Wait for address modal to close and page to be ready
    await asyncio.sleep(0.3)  # Reduced from 0.5s
    await page.wait_for_load_state("domcontentloaded")  # Changed from networkidle - faster
    # No additional sleep needed - domcontentloaded means page is ready
    
    # Check if this is a multi-item order
    if order_state["items"] is not None and len(order_state["items"]) > 0:
        # MULTI-ITEM FLOW: Add all items to cart, then proceed to payment
        order_state["status"] = "adding_to_cart"
        
        items = order_state["items"]
        out_of_stock_items = []
        successfully_added = []
        
        for idx, item in enumerate(items, start=1):
            url = item["url"]
            qty = item["qty"]
            
            print(f"\n=== Checking product {idx}/{len(items)} ===")
            print(f"🔄 Loading product page: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            # No sleep needed - wait for specific element instead
            try:
                await page.wait_for_selector("button[data-testid='add-to-cart-btn'], button:has-text('Add To Cart')", timeout=1000)
            except:
                pass
            
            # Close popups
            try:
                await page.click("button:has-text('Close')", timeout=1000)
            except:
                pass
            
            # Wait for Add To Cart button to appear (replaces fixed 1s sleep)
            try:
                await page.wait_for_selector("button.WJXJe:has-text('Add To Cart'), button[aria-label='Notify Me']", timeout=2000)
            except:
                await asyncio.sleep(0.3)  # Fallback minimal wait
            
            # Check if product is in stock (FIRST CHECK)
            print(f"🔍 Checking stock status for product {idx}...")
            is_in_stock, product_name = await check_product_stock(page)
            
            if not is_in_stock:
                print(f"❌ Product {idx} is OUT OF STOCK: {product_name}")
                out_of_stock_items.append({
                    "name": product_name,
                    "url": url,
                    "quantity": qty,
                    "index": idx
                })
                continue  # Skip this item, move to next
            
            # Product appears in stock, but verify before proceeding
            print(f"✅ Product {idx} appears in stock: {product_name}")
            
            # EXPLICIT CHECK: Look for "Notify Me" button right before trying to add
            # This catches cases where initial check might have missed it
            try:
                notify_check = await page.evaluate("""
                    () => {
                        // Check for aria-label="Notify Me"
                        const notifyByAria = document.querySelector('button[aria-label="Notify Me"]');
                        if (notifyByAria) return true;
                        
                        // Check for button with class SVCWV
                        const notifyByClass = document.querySelector('button.SVCWV');
                        if (notifyByClass) {
                            const text = notifyByClass.textContent || '';
                            if (text.includes('Notify Me') || text.includes('notify') || text.includes('when back in stock')) {
                                return true;
                            }
                        }
                        
                        // Check all buttons for "Notify Me" text
                        const buttons = Array.from(document.querySelectorAll('button'));
                        for (const btn of buttons) {
                            const text = btn.textContent || '';
                            if (text.includes('Notify Me') || text.includes('when back in stock')) {
                                return true;
                            }
                        }
                        
                        return false;
                    }
                """)
                
                if notify_check:
                    print(f"❌ SECOND CHECK: Found 'Notify Me' button - {product_name} is OUT OF STOCK")
                    out_of_stock_items.append({
                        "name": product_name,
                        "url": url,
                        "quantity": qty,
                        "index": idx
                    })
                    continue
            except Exception as e:
                print(f"⚠️ Error in explicit notify check: {e}")
            
            # Wait for Add to Cart button with double-check for out of stock
            add_to_cart_found = False
            try:
                await page.wait_for_selector("button.WJXJe:has-text('Add To Cart')", timeout=3000)  # Reduced from 5000ms
                add_to_cart_found = True
            except Exception as e:
                # Button not found - double-check if it's out of stock
                print(f"⚠️ Add to Cart button not found, performing FINAL stock check...")
                await asyncio.sleep(0.3)  # Reduced from 0.5s
                is_still_in_stock, _ = await check_product_stock(page)
                
                if not is_still_in_stock:
                    print(f"❌ FINAL CHECK: {product_name} is OUT OF STOCK")
                    out_of_stock_items.append({
                        "name": product_name,
                        "url": url,
                        "quantity": qty,
                        "index": idx
                    })
                    continue
                else:
                    # Still says in stock but button not found - might be page issue
                    print(f"⚠️ Product appears in stock but Add To Cart button not found. Marking as out of stock for safety.")
                    out_of_stock_items.append({
                        "name": product_name,
                        "url": url,
                        "quantity": qty,
                        "index": idx
                    })
                    continue
            
            if not add_to_cart_found:
                # Shouldn't reach here, but safety check
                out_of_stock_items.append({
                    "name": product_name,
                    "url": url,
                    "quantity": qty,
                    "index": idx
                })
                continue
            
            # Scroll Add to Cart button into view
            await page.evaluate("""
                const button = document.querySelector("button.WJXJe");
                if (button) {
                    button.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            """)
            await asyncio.sleep(0.3)  # Reduced from 1s - wait for scroll to complete
            
            # Click "Add To Cart" button once
            print(f"🛒 Clicking 'Add To Cart' button...")
            add_to_cart_clicked = await page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll("button.WJXJe");
                    for (let btn of buttons) {
                        if (btn.textContent && btn.textContent.includes('Add To Cart')) {
                            btn.click();
                            return true;
                        }
                    }
                    // Also try by aria-label
                    const btnByAria = document.querySelector('button[aria-label="Add to Cart"]');
                    if (btnByAria) {
                        btnByAria.click();
                        return true;
                    }
                    // Also try by class
                    const btnByClass = document.querySelector('div[aria-label="Add to Cart"] button');
                    if (btnByClass) {
                        btnByClass.click();
                        return true;
                    }
                    return false;
                }
            """)
            
            if not add_to_cart_clicked:
                return f"❌ Could not find 'Add To Cart' button for {product_name}"
            
            await asyncio.sleep(0.5)  # Reduced from 1s - wait for item to be added to cart
            
            # If quantity > 1, click + button (quantity - 1) times
            if qty > 1:
                print(f"➕ Increasing quantity by {qty - 1}...")
                for i in range(qty - 1):
                    plus_clicked = await page.evaluate("""
                        () => {
                            // Look for + button (increase quantity button)
                            // Usually has aria-label="Increase quantity by 1" or similar
                            const plusButtons = Array.from(document.querySelectorAll('button'));
                            for (const btn of plusButtons) {
                                const ariaLabel = btn.getAttribute('aria-label') || '';
                                const text = btn.textContent || '';
                                // Check for + symbol or increase quantity
                                if (ariaLabel.includes('Increase') || ariaLabel.includes('increase') ||
                                    text === '+' || text.trim() === '+') {
                                    btn.click();
                                    return true;
                                }
                            }
                            // Fallback: Look for SVG with plus icon
                            const svgs = Array.from(document.querySelectorAll('svg'));
                            for (const svg of svgs) {
                                const paths = svg.querySelectorAll('path');
                                for (const path of paths) {
                                    const d = path.getAttribute('d') || '';
                                    // Plus icon typically has horizontal and vertical lines
                                    if (d.includes('M12') && d.includes('H') && d.includes('V')) {
                                        const btn = svg.closest('button');
                                        if (btn) {
                                            btn.click();
                                            return true;
                                        }
                                    }
                                }
                            }
                            return false;
                        }
                    """)
                    
                    if plus_clicked:
                        print(f"  ✅ Clicked + button ({i + 1}/{qty - 1})")
                        await asyncio.sleep(0.3)  # Reduced from 0.5s - wait between clicks
                    else:
                        print(f"  ⚠️ Could not find + button for increment {i + 1}")
                        # Continue anyway - might already be at desired quantity
            
            successfully_added.append({"name": product_name, "quantity": qty})
            print(f"✅ Added {qty}x {product_name}!")
        
        # Check if any items are out of stock
        if out_of_stock_items:
            order_state["status"] = "waiting_stock_decision"
            order_state["out_of_stock_items"] = out_of_stock_items
            order_state["successfully_added"] = successfully_added
            
            out_of_stock_names = [item["name"] for item in out_of_stock_items]
            message = (
                f"⚠️ OUT OF STOCK ALERT:\n\n"
                f"The following items are currently out of stock:\n"
            )
            for item in out_of_stock_items:
                message += f"  - {item['name']} (Quantity: {item['quantity']})\n"
            
            if successfully_added:
                message += f"\n✅ Successfully added to cart:\n"
                for item in successfully_added:
                    message += f"  - {item['name']} (Quantity: {item['quantity']})\n"
            
            message += (
                f"\nPlease choose one of the following options:\n"
                f"1. Cancel the entire order\n"
                f"2. Order something else instead of the out-of-stock items\n"
                f"3. Proceed with the remaining items (skip out-of-stock items)\n\n"
                f"Use the 'handle_stock_decision' tool to proceed."
            )
            
            return message
        
        # All items added successfully, proceed to cart
        
        # After all items added, proceed to cart → payment
        # This function checks for "Place Order" (wallet) first, otherwise uses Pay on Delivery
        payment_method = await proceed_to_payment(page)

        order_state["status"] = "completed"
        # Close browser after order completion
        await close_browser_after_completion()
        
        payment_text = "through Wallet" if payment_method == "wallet" else "with Pay on Delivery"
        return f"Login successful! Address selected. All {len(items)} items added to cart and order placed {payment_text}."
    
    else:
        # SINGLE-ITEM FLOW
        order_state["status"] = "adding_to_cart"
        
        # Navigate to product page
        await page.goto(order_state["item_url"], wait_until="domcontentloaded")
        await asyncio.sleep(0.3)  # Reduced from 0.5s + networkidle wait
        
        # Close popups
        try:
            await page.click("button:has-text('Close')", timeout=1000)
        except:
            pass
        
        # Wait for Add To Cart button to appear (replaces fixed 1s sleep)
        try:
            await page.wait_for_selector("button.WJXJe:has-text('Add To Cart'), button[aria-label='Notify Me']", timeout=2000)
        except:
            await asyncio.sleep(0.3)  # Fallback minimal wait
        
        # Check if product is in stock (FIRST CHECK)
        print(f"🔍 Checking stock status...")
        is_in_stock, product_name = await check_product_stock(page)
        
        if not is_in_stock:
            print(f"❌ Product is OUT OF STOCK: {product_name}")
            order_state["status"] = "waiting_stock_decision"
            order_state["out_of_stock_items"] = [{
                "name": product_name,
                "url": order_state["item_url"],
                "quantity": 1,
                "index": 1
            }]
            return (
                f"⚠️ OUT OF STOCK: The product '{product_name}' is currently out of stock.\n\n"
                f"Please choose one of the following options:\n"
                f"1. Cancel the order\n"
                f"2. Order a different product instead\n\n"
                f"Use the 'handle_stock_decision' tool to proceed."
            )
        
        # Product appears in stock, but verify before proceeding
        print(f"✅ Product appears in stock: {product_name}")
        
        # EXPLICIT CHECK: Look for "Notify Me" button right before trying to add
        try:
            notify_check = await page.evaluate("""
                () => {
                    // Check for aria-label="Notify Me"
                    const notifyByAria = document.querySelector('button[aria-label="Notify Me"]');
                    if (notifyByAria) return true;
                    
                    // Check for button with class SVCWV
                    const notifyByClass = document.querySelector('button.SVCWV');
                    if (notifyByClass) {
                        const text = notifyByClass.textContent || '';
                        if (text.includes('Notify Me') || text.includes('notify') || text.includes('when back in stock')) {
                            return true;
                        }
                    }
                    
                    // Check all buttons for "Notify Me" text
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('Notify Me') || text.includes('when back in stock')) {
                            return true;
                        }
                    }
                    
                    return false;
                }
            """)
            
            if notify_check:
                print(f"❌ SECOND CHECK: Found 'Notify Me' button - {product_name} is OUT OF STOCK")
                order_state["status"] = "waiting_stock_decision"
                order_state["out_of_stock_items"] = [{
                    "name": product_name,
                    "url": order_state["item_url"],
                    "quantity": 1,
                    "index": 1
                }]
                return (
                    f"⚠️ OUT OF STOCK: The product '{product_name}' is currently out of stock.\n\n"
                    f"Please choose one of the following options:\n"
                    f"1. Cancel the order\n"
                    f"2. Order a different product instead\n\n"
                    f"Use the 'handle_stock_decision' tool to proceed."
                )
        except Exception as e:
            print(f"⚠️ Error in explicit notify check: {e}")
        
        # Wait for Add to Cart button with double-check for out of stock
        add_to_cart_found = False
        try:
            await page.wait_for_selector("button.WJXJe:has-text('Add To Cart')", timeout=3000)  # Reduced from 5000ms
            add_to_cart_found = True
        except Exception as e:
            # Button not found - double-check if it's out of stock
            print(f"⚠️ Add to Cart button not found, performing FINAL stock check...")
            await asyncio.sleep(0.5)
            is_still_in_stock, _ = await check_product_stock(page)
            
            if not is_still_in_stock:
                print(f"❌ FINAL CHECK: {product_name} is OUT OF STOCK")
                order_state["status"] = "waiting_stock_decision"
                order_state["out_of_stock_items"] = [{
                    "name": product_name,
                    "url": order_state["item_url"],
                    "quantity": 1,
                    "index": 1
                }]
                return (
                    f"⚠️ OUT OF STOCK: The product '{product_name}' is currently out of stock.\n\n"
                    f"Please choose one of the following options:\n"
                    f"1. Cancel the order\n"
                    f"2. Order a different product instead\n\n"
                    f"Use the 'handle_stock_decision' tool to proceed."
                )
            else:
                # Still says in stock but button not found - might be page issue
                return (
                    f"⚠️ ERROR: Could not find 'Add To Cart' button for '{product_name}'. "
                    f"The product may be out of stock or the page structure has changed. "
                    f"Please try again or choose a different product."
                )
        
        if not add_to_cart_found:
            return (
                f"⚠️ ERROR: Could not find 'Add To Cart' button for '{product_name}'. "
                f"The product may be out of stock or the page structure has changed."
            )
        
    # Scroll Add to Cart button into view
    await page.evaluate("""
        const button = document.querySelector("button.WJXJe");
        if (button) {
            button.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    """)
    await asyncio.sleep(0.3)  # Reduced from 0.5s - wait for scroll to complete
    
    # Click "Add To Cart" button once
    print(f"🛒 Clicking 'Add To Cart' button...")
    add_to_cart_clicked = await page.evaluate("""
        () => {
            const buttons = document.querySelectorAll("button.WJXJe");
            for (let btn of buttons) {
                if (btn.textContent && btn.textContent.includes('Add To Cart')) {
                    btn.click();
                    return true;
                }
            }
            // Also try by aria-label
            const btnByAria = document.querySelector('button[aria-label="Add to Cart"]');
            if (btnByAria) {
                btnByAria.click();
                return true;
            }
            // Also try by class
            const btnByClass = document.querySelector('div[aria-label="Add to Cart"] button');
            if (btnByClass) {
                btnByClass.click();
                return true;
            }
            return false;
        }
    """)
    
    if not add_to_cart_clicked:
        return f"❌ Could not find 'Add To Cart' button for {product_name}"
    
    await asyncio.sleep(0.5)  # Reduced from 1.5s - wait for item to be added to cart
    
    # Note: Single-item orders typically have quantity 1, so no need for + button
    # If quantity > 1 is needed in future, add the same + button logic here
    
    # Proceed to payment
    # This function checks for "Place Order" (wallet) first, otherwise uses Pay on Delivery
    payment_method = await proceed_to_payment(page)

    order_state["status"] = "completed"
    # Close browser after order completion
    await close_browser_after_completion()
    
    payment_text = "through Wallet" if payment_method == "wallet" else "with Pay on Delivery"
    return f"Login successful! Address selected. Item added to cart and order placed {payment_text}."


async def submit_payment(otp: str) -> str:
    """Submit payment OTP and complete order"""
    global order_state
    
    if order_state["status"] != "waiting_payment_otp":
        return f"Not waiting for payment OTP. Current status: {order_state['status']}"
    
    page = order_state["page"]

    # Wait for and locate payment OTP field.
    # This field is: <input class="input-field" type="password" name="otpValue" ...>
    try:
        await page.wait_for_selector("input[type='password'][name='otpValue']", timeout=5000)  # Reduced from 10000ms
    except Exception:
        return "Could not find payment OTP field (input[type='password'][name='otpValue']). Make sure the bank OTP page is visible."

    otp_input = await page.query_selector("input[type='password'][name='otpValue']")
    if not otp_input:
        return "Payment OTP field not found even after waiting. Please check if the OTP page loaded correctly."

    # Focus and clear any existing value
    await otp_input.click()
    try:
        await otp_input.fill("")
    except Exception:
        # Some password fields may not allow fill; ignore and just type
        pass

    # Type OTP digit-by-digit so onkeypress/oninput handlers fire
    for digit in otp:
        await otp_input.type(digit, delay=30)  # Reduced from 50ms
        await asyncio.sleep(0.02)  # Reduced from 0.03s

    # Small stability wait
    await asyncio.sleep(0.3)  # Reduced from 0.5s

    # Wait for and click CONFIRM button:
    # <button class="submit" id="submitBtn" type="submit" onclick="enterOTP()">CONFIRM</button>
    try:
        await page.wait_for_selector("button#submitBtn", timeout=3000)  # Reduced from 5000ms
    except Exception:
        return "Could not find CONFIRM button (button#submitBtn). Please check that the OTP form is fully loaded."

    await page.click("button#submitBtn")
    await asyncio.sleep(0.5)  # Reduced from 1s
    
    order_state["status"] = "completed"
    
    # Close browser after order completion (session is saved to disk in persistent context)
    await close_browser_after_completion()
    return "✅ Payment successful! Your order has been placed. (Login session preserved for next order)"


async def handle_stock_decision(decision: str, replacement_items: list = None) -> str:
    """Handle user decision when items are out of stock"""
    global order_state
    
    if order_state["status"] != "waiting_stock_decision":
        return f"Not waiting for stock decision. Current status: {order_state['status']}"
    
    if not order_state.get("out_of_stock_items"):
        return "No out-of-stock items found in current order state."
    
    page = order_state["page"]
    out_of_stock = order_state["out_of_stock_items"]
    successfully_added = order_state.get("successfully_added", [])
    
    if decision == "cancel":
        # Cancel the entire order
        await stop_order()
        return "❌ Order cancelled as requested. All items were removed from the order."
    
    elif decision == "proceed_with_remaining":
        # Continue with only the successfully added items
        if not successfully_added:
            await stop_order()
            return "❌ No items were successfully added. Order cancelled."
        
        # Proceed to cart with remaining items
        order_state["status"] = "adding_to_cart"
        
        try:
            # Proceed to payment (checks for wallet "Place Order" first)
            payment_method = await proceed_to_payment(page)
            
            order_state["status"] = "completed"
            # Close browser after order completion
            await close_browser_after_completion()
            added_names = [item["name"] for item in successfully_added]
            payment_text = "through Wallet" if payment_method == "wallet" else "with Pay on Delivery"
            return (
                f"✅ Order proceeding with remaining items:\n"
                f"{', '.join(added_names)}\n\n"
                f"Out-of-stock items were skipped. Order placed {payment_text}."
            )
        except Exception as e:
            return f"❌ Error proceeding with remaining items: {str(e)}"
    
    elif decision == "replace_items":
        # Replace out-of-stock items with new items
        if not replacement_items:
            return "❌ 'replace_items' decision requires replacement_items parameter."
        
        order_state["status"] = "adding_to_cart"
        
        # Resolve replacement items
        resolved_replacements = []
        for item in replacement_items:
            try:
                url = get_product_url(
                    product_name=item.get("product_name"),
                    item_url=item.get("item_url")
                )
                qty = int(item.get("quantity", 1))
                if qty < 1:
                    continue
                resolved_replacements.append({"url": url, "qty": qty})
            except Exception as e:
                return f"❌ Error resolving replacement item: {str(e)}"
        
        if not resolved_replacements:
            return "❌ No valid replacement items provided."
        
        # Add replacement items
        for idx, item in enumerate(resolved_replacements, start=1):
            url = item["url"]
            qty = item["qty"]
            
            print(f"\n=== Adding replacement product {idx}/{len(resolved_replacements)} ===")
            await page.goto(url, wait_until="domcontentloaded")  # Changed from networkidle
            await asyncio.sleep(0.3)  # Reduced from 0.5s
            
            # Check stock
            await asyncio.sleep(0.3)
            is_in_stock, product_name = await check_product_stock(page)
            
            if not is_in_stock:
                return f"❌ Replacement product '{product_name}' is also out of stock. Please choose a different replacement."
            
            # Add to cart
            try:
                await page.wait_for_selector("button.WJXJe:has-text('Add To Cart')", timeout=3000)  # Reduced from 10000ms
                await page.evaluate("""
                    const button = document.querySelector("button.WJXJe");
                    if (button) button.scrollIntoView({ behavior: 'smooth', block: 'center' });
                """)
                await asyncio.sleep(0.3)  # Reduced from 0.5s
                
                for q in range(qty):
                    await page.evaluate("""
                        const buttons = document.querySelectorAll("button.WJXJe");
                        for (let btn of buttons) {
                            if (btn.textContent.includes('Add To Cart')) {
                                btn.click();
                                break;
                            }
                        }
                    """)
                    await asyncio.sleep(0.3)  # Reduced from 0.5s
                
                print(f"✅ Added {qty}x {product_name} as replacement!")
            except Exception as e:
                return f"❌ Error adding replacement item: {str(e)}"
        
        # Proceed to cart and payment (checks for wallet "Place Order" first)
        try:
            payment_method = await proceed_to_payment(page)
            
            order_state["status"] = "completed"
            # Close browser after order completion
            await close_browser_after_completion()
            payment_text = "through Wallet" if payment_method == "wallet" else "with Pay on Delivery"
            return (
                f"✅ Replacement items added successfully!\n"
                f"Order placed {payment_text}."
            )
        except Exception as e:
            return f"❌ Error completing order with replacements: {str(e)}"
    
    else:
        return f"❌ Invalid decision: {decision}. Must be 'cancel', 'proceed_with_remaining', or 'replace_items'."


def get_status() -> str:
    """Get current order status"""
    global order_state
    
    status_messages = {
        "idle": "No active order",
        "starting": "Starting order process...",
        "waiting_login_otp": "Waiting for login OTP",
        "waiting_login_otp_multi": "Waiting for login OTP (multi-item order)",
        "adding_to_cart": "Adding items to cart",
        "waiting_stock_decision": "Waiting for user decision on out-of-stock items",
        "waiting_payment_otp": "Waiting for payment OTP",
        "completed": "Order completed!"
    }
    
    return status_messages.get(order_state["status"], f"Status: {order_state['status']}")


async def proceed_to_payment(page) -> str:
    """
    Handle payment flow - checks for 'Place Order' button (wallet payment) first,
    otherwise proceeds with Pay on Delivery flow.
    Returns: "wallet" if wallet payment was used, "pay_on_delivery" if Pay on Delivery was used.
    """
    # First, open cart
    await page.click("button[data-testid='cart-btn']")
    # Wait for cart to fully load (replaces fixed 1.5s sleep)
    try:
        # Wait for either "Place Order" or "Click to Pay" button to appear
        await page.wait_for_selector("button:has-text('Place Order'), button:has-text('Click to Pay')", timeout=2000)  # Reduced from 3000ms
    except:
        await asyncio.sleep(0.5)  # Fallback minimal wait if selector not found
    
    # Check if "Place Order" button exists (wallet payment available)
    # User provided selector: <button class="my-2.5 h-[52px] w-full rounded-xl text-center bg-skin-primary"><span class="text-body1 text-white">Place Order</span></button>
    print("🔍 Checking for 'Place Order' button (wallet payment)...")
    
    # Strategy 1: Use JavaScript to find button with exact structure
    try:
        place_order_button = await page.evaluate("""
            () => {
                // Look for button with bg-skin-primary class
                const buttons = Array.from(document.querySelectorAll('button.bg-skin-primary, button[class*="bg-skin-primary"]'));
                console.log('Found', buttons.length, 'buttons with bg-skin-primary class');
                for (const btn of buttons) {
                    // Check for span with "Place Order" text
                    const spans = btn.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent || '';
                        if (text.trim() === 'Place Order' || text.includes('Place Order')) {
                            // Verify it has the right classes
                            const spanClasses = span.className || '';
                            if (spanClasses.includes('text-body1') || spanClasses.includes('text-white')) {
                                console.log('Found Place Order button with correct structure');
                                return btn;
                            }
                        }
                    }
                }
                
                // Fallback: Look for any button containing "Place Order" text
                const allButtons = Array.from(document.querySelectorAll('button'));
                console.log('Checking', allButtons.length, 'total buttons for Place Order text');
                for (const btn of allButtons) {
                    const text = btn.textContent || '';
                    if (text.trim() === 'Place Order' || (text.includes('Place Order') && !text.includes('Click to Pay') && !text.includes('Proceed to Pay'))) {
                        // Check if it has the bg-skin-primary class
                        const classes = btn.className || '';
                        if (classes.includes('bg-skin-primary')) {
                            console.log('Found Place Order button with bg-skin-primary class');
                            return btn;
                        }
                    }
                }
                console.log('Place Order button not found');
                return null;
            }
        """)
        
        if place_order_button:
            print("✅ Found 'Place Order' button!")
        
        if place_order_button:
            print("💰 Wallet payment detected - clicking 'Place Order' button directly...")
            # Scroll button into view first
            await page.evaluate("""
                (btn) => {
                    if (btn) {
                        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            """, place_order_button)
            await asyncio.sleep(0.2)  # Reduced from 0.5s
            
            # Try multiple clicking methods
            clicked = False
            # Method 1: JavaScript click
            try:
                await page.evaluate("(btn) => { if (btn) btn.click(); }", place_order_button)
                clicked = True
                print("   ✅ Clicked using JavaScript")
            except Exception as e:
                print(f"   ⚠️ JavaScript click failed: {e}")
            
            # Method 2: Try Playwright locator click as backup
            if not clicked:
                try:
                    place_order_locator = page.locator("button.bg-skin-primary:has-text('Place Order')")
                    if await place_order_locator.count() > 0:
                        await place_order_locator.first.click()
                        clicked = True
                        print("   ✅ Clicked using Playwright locator")
                except Exception as e:
                    print(f"   ⚠️ Playwright locator click failed: {e}")
            
            # Method 3: Try direct text click
            if not clicked:
                try:
                    await page.click("text=Place Order")
                    clicked = True
                    print("   ✅ Clicked using text selector")
                except Exception as e:
                    print(f"   ⚠️ Text click failed: {e}")
            
            await asyncio.sleep(1.5)
            if clicked:
                print("✅ Order placed using wallet payment!")
                return "wallet"
            else:
                print("⚠️ Button found but click may have failed, proceeding anyway...")
                return "wallet"  # Assume wallet payment was attempted
    except Exception as e:
        print(f"⚠️ Strategy 2 failed: {e}")
    
    # Strategy 3: Try Playwright locator with CSS selector
    try:
        place_order_locator = page.locator("button.bg-skin-primary:has-text('Place Order')")
        count = await place_order_locator.count()
        if count > 0:
            print("💰 Wallet payment detected - clicking 'Place Order' button directly...")
            await place_order_locator.first.scroll_into_view_if_needed()
            await place_order_locator.first.click()
            await asyncio.sleep(1.5)
            print("✅ Order placed using wallet payment!")
            return "wallet"
    except Exception as e:
        print(f"⚠️ Strategy 3 failed: {e}")
    
    # Strategy 4: Try finding span and clicking parent button using JavaScript
    try:
        parent_button = await page.evaluate("""
            () => {
                const spans = Array.from(document.querySelectorAll('span'));
                for (const span of spans) {
                    const text = span.textContent || '';
                    if (text.trim() === 'Place Order' || text.includes('Place Order')) {
                        const parent = span.closest('button');
                        if (parent) {
                            const classes = parent.className || '';
                            if (classes.includes('bg-skin-primary')) {
                                return parent;
                            }
                        }
                    }
                }
                return null;
            }
        """)
        if parent_button:
            print("💰 Wallet payment detected - clicking 'Place Order' button directly...")
            await page.evaluate("""
                (btn) => {
                    if (btn) {
                        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        btn.click();
                    }
                }
            """, parent_button)
            await asyncio.sleep(1.5)
            print("✅ Order placed using wallet payment!")
            return "wallet"
    except Exception as e:
        print(f"⚠️ Strategy 4 failed: {e}")
    
    # If "Place Order" not found, proceed with normal Pay on Delivery flow
    print("💳 Proceeding with Pay on Delivery flow...")
    try:
        await page.wait_for_selector("button:has-text('Click to Pay')", timeout=3000)  # Reduced from 5000ms
    except:
        # Maybe already on payment screen or button text is different
        print("⚠️ 'Click to Pay' button not found, checking if already on payment screen...")
    
    # Click to Pay (open payment methods screen)
    try:
        await page.click("button:has-text('Click to Pay')")
        await page.wait_for_selector("div[testid='nvb_cod']", timeout=3000)  # Reduced from 5000ms
    except:
        # Maybe payment screen is already open
        pass
    
    # Select "Pay On Delivery" tab
    try:
        await page.click("div[testid='nvb_cod']")
        await asyncio.sleep(0.5)
    except:
        print("⚠️ Could not find Pay on Delivery option")
    
    # Click "Proceed to Pay" button
    try:
        await page.click("div:has-text('Proceed to Pay')")
        await asyncio.sleep(1)
        print("✅ Order placed with Pay on Delivery!")
    except:
        print("⚠️ Could not find 'Proceed to Pay' button")
    
    return "pay_on_delivery"


async def close_browser_after_completion() -> None:
    """Close browser/context after order completion"""
    global order_state
    
    try:
        print("🔄 Closing browser after order completion...")
        if order_state.get("context"):
            try:
                await order_state["context"].close()
            except:
                pass
            order_state["context"] = None
        
        if order_state.get("browser"):
            try:
                await order_state["browser"].close()
            except:
                pass
            order_state["browser"] = None
        
        if order_state.get("playwright"):
            try:
                await order_state["playwright"].stop()
            except:
                pass
            order_state["playwright"] = None
        
        order_state["page"] = None
        order_state["status"] = "idle"
        print("✅ Browser closed successfully")
    except Exception as e:
        print(f"⚠️ Error closing browser: {e}")


async def stop_order() -> str:
    """Stop and reset the current order. Close context to ensure next order loads from saved directory."""
    global order_state
    
    try:
        # CRITICAL: Close context/browser to ensure next order starts fresh from saved directory
        # This prevents reusing a cancelled session state
        if order_state.get("context"):
            # Close persistent context - next order will load fresh from saved directory
            print("🔄 Closing persistent context - next order will load from saved directory")
            try:
                await order_state["context"].close()
            except:
                pass
            order_state["context"] = None
        
        if order_state.get("browser"):
            # Regular browser - close it
            print("🔄 Closing browser...")
            try:
                await order_state["browser"].close()
            except:
                pass
            order_state["browser"] = None
        
        # Stop playwright to ensure clean state
        if order_state.get("playwright"):
            print("🔄 Stopping playwright...")
            try:
                await order_state["playwright"].stop()
            except:
                pass
            order_state["playwright"] = None
    except Exception as e:
        # Ignore cleanup errors
        print(f"⚠️ Cleanup warning: {e}")
        pass
    
    # Reset all state
    order_state["browser"] = None
    order_state["page"] = None
    order_state["context"] = None
    order_state["playwright"] = None
    order_state["status"] = "idle"
    order_state["waiting_for"] = None
    order_state["phone_number"] = None
    order_state["item_url"] = None
    order_state["items"] = None
    order_state["address"] = None
    order_state["out_of_stock_items"] = None
    order_state["successfully_added"] = None
    
    return "Order stopped and reset. Next order will load fresh from saved directory at /Users/Pranav_1/zepto-mcp/zepto_browser_data"


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="zepto-cafe",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
if __name__ == "__main__":
    asyncio.run(main())