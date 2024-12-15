from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS to handle cross-origin requests
from playwright.sync_api import sync_playwright

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# Function to search images on Yandex and then DuckDuckGo using Playwright
def search_images(query):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Launch browser in headless mode
        page = browser.new_page()

        # Step 1: Scrape images from Yandex
        page.goto(f"https://yandex.com/images/search?text={query}")
        page.wait_for_selector('div.ContentImage')  # Wait for Yandex images to load

        yandex_images = []
        for img in page.query_selector_all('div.ContentImage img'):
            img_url = img.get_attribute('src')
            if img_url and img_url.startswith('//'):
                img_url = 'https:' + img_url  # Fix the URL by adding the protocol
            yandex_images.append(img_url)

        # Step 2: Navigate to DuckDuckGo and search for images
        page.goto(f"https://duckduckgo.com/?t=h_&q={query}&iax=images&ia=images")
        
        # Scroll to the bottom to trigger lazy-loaded images
        for _ in range(3):  # Scroll 3 times to trigger loading more images
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # Scroll down to load images
            page.wait_for_timeout(2000)  # Wait for 2 seconds to ensure images load

        # Wait for the first <img> tag to appear on the page (no specific class or ID)
        page.wait_for_selector('img', timeout=60000)  # Increased wait time

        # Extract DuckDuckGo images
        duckduckgo_images = []
        for img in page.query_selector_all('img'):
            img_url = img.get_attribute('src')
            if img_url:
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url  # Fix the URL by adding the protocol
                # If src attribute is not available, try 'data-src' or 'srcset'
                if not img_url:
                    img_url = img.get_attribute('data-src') or img.get_attribute('srcset')
                if img_url and img_url.startswith('//'):
                    img_url = 'https:' + img_url  # Fix URL if necessary
                duckduckgo_images.append(img_url)

        browser.close()

        # Return both Yandex and DuckDuckGo images
        return {'yandex_images': yandex_images, 'duckduckgo_images': duckduckgo_images}



@app.route('/search', methods=['POST'])
def search():
    # Ensure the request is JSON
    if request.is_json:
        # Parse JSON data
        query = request.json.get('query')
        if query:
            images = search_images(query)
            return jsonify(images)
        return jsonify({'error': 'No query provided'}), 400
    else:
        return jsonify({'error': 'Invalid content type, must be application/json'}), 415

if __name__ == '__main__':
    app.run(debug=True, port=3000)  # Run Flask on localhost:3000
