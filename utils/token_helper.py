import asyncio
import os
import json
import time
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

# Target URL - Baidu Image Search Home
TARGET_URL = "https://image.baidu.com/"
# Target URL - Baidu Image Search PC Page
TARGET_URL = "https://graph.baidu.com/pcpage/index?tpl_from=pc"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "acs_token.json")

def _ensure_dummy_image():
    """Create a dummy image for upload simulation if not exists."""
    dummy_path = os.path.join(os.getcwd(), "dummy.jpg")
    if not os.path.exists(dummy_path):
        with open(dummy_path, "wb") as f:
            f.write(b"fake image content")
    return dummy_path

def _remove_dummy_image(path):
    """Remove the dummy image."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def _save_token_to_disk(token):
    """Save token to disk with timestamp."""
    data = {
        "token": token,
        "updated_at": time.time()
    }
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(data, f)
        print(f"Token saved to {TOKEN_FILE}")
    except Exception as e:
        print(f"Failed to save token: {e}")

def _load_token_from_disk():
    """Load token from disk."""
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data.get("token")
    except Exception as e:
        print(f"Failed to load token: {e}")
        return None

def get_acs_token_sync(force_refresh=False):
    """
    Synchronously get acs-token using Playwright.
    If force_refresh is False, tries to load from disk first.
    """
    if not force_refresh:
        token = _load_token_from_disk()
        if token:
            return token

    token = None
    dummy_path = _ensure_dummy_image()
    
    with sync_playwright() as p:
        # Launch browser with stealth args
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        def handle_request(request):
            nonlocal token
            # Check headers for acs-token
            headers = request.headers
            if "acs-token" in headers:
                print(f"Found token in request to: {request.url}")
                token = headers["acs-token"]
        
        # Listen to all requests
        page.on("request", handle_request)
        
        try:
            print(f"Navigating to {TARGET_URL}...")
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
            
            # Simulate file upload to trigger request
            try:
                print("Looking for file input...")
                # The file input might be hidden, so we look for it by selector
                file_input = page.wait_for_selector('input[type="file"]', state="attached", timeout=5000)
                if file_input:
                    print("Uploading dummy file...")
                    # Must provide absolute path
                    file_input.set_input_files(dummy_path)
                    
                    # Wait for upload request to be sent
                    page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Error during upload simulation: {e}")

            # If still no token, wait a bit more
            if not token:
                print("Token not found immediately, waiting a bit more...")
                page.wait_for_timeout(2000)
                
        except Exception as e:
            print(f"Error occurred while fetching token: {e}")
        finally:
            browser.close()
            _remove_dummy_image(dummy_path)
    
    if token:
        _save_token_to_disk(token)
            
    return token

async def get_acs_token_async(force_refresh=False):
    """
    Asynchronously get acs-token using Playwright.
    If force_refresh is False, tries to load from disk first.
    """
    if not force_refresh:
        token = _load_token_from_disk()
        if token:
            return token

    token = None
    dummy_path = _ensure_dummy_image()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        async def handle_request(request):
            nonlocal token
            headers = await request.all_headers()
            if "acs-token" in headers:
                # print(f"Found token in request to: {request.url}")
                token = headers["acs-token"]
        
        page.on("request", handle_request)
        
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
            
            try:
                file_input = await page.wait_for_selector('input[type="file"]', state="attached", timeout=5000)
                if file_input:
                    await file_input.set_input_files(dummy_path)
                    await page.wait_for_timeout(5000)
            except Exception:
                pass
            
            if not token:
                 await page.wait_for_timeout(2000)
                 
        except Exception as e:
            print(f"Error occurred while fetching token: {e}")
        finally:
            await browser.close()
            _remove_dummy_image(dummy_path)
    
    if token:
        _save_token_to_disk(token)
            
    return token

if __name__ == "__main__":
    print("Testing sync token fetch (force_refresh=True)...")
    t = get_acs_token_sync(force_refresh=True)
    print(f"Token: {t}")
