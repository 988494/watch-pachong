import os
import json
import requests
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

def scrape_product(url, brand, model, product_code):
    print(f"Scraping URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        try:
            page.wait_for_selector(".one_box_footer", timeout=15000)
        except Exception:
            page.wait_for_timeout(3000)
        
        html_content = page.content()
        browser.close()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    price_elem = soup.select_one(".one_box_right .f18")
    price = int(price_elem.get_text(strip=True)) if price_elem else 2500

    footer_elem = soup.select_one(".one_box_footer")
    description_text = footer_elem.get_text(separator="\n", strip=True) if footer_elem else ""

    img_elems = soup.select(".detail_index_img")
    img_urls = []
    for img in img_elems:
        src = img.get("src")
        if src and src not in img_urls:
            img_urls.append(src)

    if not img_urls:
        swiper_imgs = soup.select(".swiper_img_wra img")
        for img in swiper_imgs:
            src = img.get("src")
            if src and src not in img_urls:
                img_urls.append(src)

    print(f"Found {len(img_urls)} images.")

    slug = f"{brand}-{model}-{product_code}"
    folder_name = slug
    img_dir = os.path.join("images", folder_name)
    os.makedirs(img_dir, exist_ok=True)

    downloaded_image_paths = []
    for idx, img_url in enumerate(img_urls):
        ext = os.path.splitext(img_url.split("?")[0])[1]
        if not ext:
            ext = ".jpg"
        filename = f"{slug}-{idx}{ext}"
        dest_path = os.path.join(img_dir, filename)

        print(f"Downloading {img_url} -> {dest_path}")
        try:
            resp = requests.get(img_url, timeout=15)
            if resp.status_code == 200:
                with open(dest_path, "wb") as img_f:
                    img_f.write(resp.content)
            else:
                print(f"Failed to download {img_url}, status: {resp.status_code}")
        except Exception as e:
            print(f"Error downloading {img_url}: {e}")

        rel_path = f"/images/{folder_name}/{filename}"
        downloaded_image_paths.append(rel_path)

    cover_path = downloaded_image_paths[0] if downloaded_image_paths else f"/images/{folder_name}/{slug}-0.jpg"
    media_images_str = ",".join(downloaded_image_paths)

    title_zh = product_code
    if description_text:
        lines = description_text.split("\n")
        if lines:
            title_zh = lines[0].strip()

    product_data = {
        "slug": slug,
        "category": model,
        "price": price,
        "price_original": 0,
        "cover": cover_path,
        "media": {
            "images": media_images_str,
            "videos": ""
        },
        "title": {
            "zh": title_zh
        },
        "description": {
            "zh": description_text
        }
    }

    return product_data

def main():
    products_config = [
        ("https://gxhy1688.com/detailIndex?marketCode=gz&code=864406250", "rolex", "submariner", "864406250"),
        ("https://gxhy1688.com/detailIndex?marketCode=gz&code=864406255", "rolex", "submariner", "864406255")
    ]

    products = []
    for url, brand, model, product_code in products_config:
        prod = scrape_product(url, brand, model, product_code)
        if prod:
            products.append(prod)

    output_json = "products.json"
    with open(output_json, "w", encoding="utf-8") as jf:
        json.dump(products, jf, ensure_ascii=False, indent=2)

    print(f"Successfully scraped {len(products)} products and saved to {output_json}")

if __name__ == "__main__":
    main()