import asyncio
import os
import json
from openai import OpenAI
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client=OpenAI(api_key=api_key)

def check_seo_elements(soup):
    seo = {}

    # Title
    seo["title"] = soup.title.string.strip() if soup.title and soup.title.string else "Not found"

    # Meta Description
    meta_desc = soup.find("meta", attrs={"name": "description"}) or \
                soup.find("meta", attrs={"property": "og:description"}) or \
                soup.find("meta", attrs={"name": "twitter:description"})
    seo["meta_description"] = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else "Not found"

    # H1 Tags
    h1_tags = soup.find_all("h1")
    seo["h1_count"] = len(h1_tags)

    # Canonical link
    canonical = soup.find("link", rel="canonical")
    seo["canonical"] = canonical["href"] if canonical and canonical.get("href") else "Not found"

    return seo

def check_accessibility(soup):
    access = {}

    # Image alt text check
    images = soup.find_all("img")
    images_with_alt = [img for img in images if img.get("alt")]
    access["images_with_alt_percent"] = round((len(images_with_alt) / len(images)) * 100, 2) if images else 0

    # ARIA roles
    aria_roles = soup.find_all(attrs={"role": True})
    access["aria_roles_count"] = len(aria_roles)

    return access


async def audit_website(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)

        safe_name = url.replace("https://","").replace("http://","").replace("/","_")
        os.makedirs(safe_name,exist_ok=True)

        screenshot_path = os.path.join(safe_name, "screenshot.png")
        await page.screenshot(path=screenshot_path, full_page=True)      

        title = await page.title()
        desc_locator = page.locator('meta[name="description"]')
        description = await desc_locator.get_attribute("content") if await desc_locator.count() > 0 else "Not found"

        links = await page.locator("a").all()
        num_links = len(links)
          
        timing_json = await page.evaluate("JSON.stringify(window.performance.timing)")
        timing = json.loads(timing_json)
        speed = {
            "domContentLoaded": timing["domContentLoadedEventEnd"] - timing["navigationStart"],
            "loadEvent": timing["loadEventEnd"] - timing["navigationStart"]
        }

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        seo = check_seo_elements(soup)
        access = check_accessibility(soup)

        perf = await page.evaluate("JSON.stringify(window.performance.timing)")
        timing = json.loads(perf)
        speed = {
            "domContentLoaded": timing["domContentLoadedEventEnd"] - timing["navigationStart"],
            "loadEvent": timing["loadEventEnd"] - timing["navigationStart"]
        }

        result_path = os.path.join(safe_name, "audit_result.txt")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n")
            f.write(f"Title: {title}\n")
            f.write(f"Meta Description: {description}\n")
            f.write(f"Number of Links: {num_links}\n")
            f.write(f"DOMContentLoaded: {speed['domContentLoaded']} ms\n")
            f.write(f"Load Event: {speed['loadEvent']} ms\n")
            f.write("\nSEO Elements:\n")
            for k, v in seo.items():
                f.write(f"{k}: {v}\n")
            f.write("\nAccessibility:\n")
            for k, v in access.items():
                f.write(f"{k}: {v}\n")

        await browser.close()
        print(f"✅ Audit complete. Results saved in folder: {safe_name}")

        return {
            "title": title,
            "description": description,
            "num_links": num_links,
            "speed": speed,
            "seo": seo,
            "accessibility": access
        }


async def summarize_audit(title, description, num_links, speed, seo, access):
    prompt = (
        f"Website Title: {title}\n"
        f"Description: {description}\n"
        f"Number of Links: {num_links}\n\n"
        f"Speed - DOMContentLoaded: {speed['domContentLoaded']} ms, LoadEvent: {speed['loadEvent']} ms\n"
        f"SEO: {json.dumps(seo, indent=2)}\n"
        f"Accessibility: {json.dumps(access, indent=2)}\n\n"
        "Give me a brief and clear audit summary based on this info."
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful website auditor."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0.7,
        timeout=60
    )

    summary = response.choices[0].message.content
    return summary

if __name__ == "__main__":
    url = "https://google.com"
    result = asyncio.run(audit_website(url))
    
    print("\n--- Website Audit ---")
    print(f"Title: {result['title']}")
    print(f"Description: {result['description']}")
    print(f"Links Found: {result['num_links']}")
    print(f"DOMContentLoaded: {result['speed']['domContentLoaded']} ms")
    print(f"Load Event: {result['speed']['loadEvent']} ms")
    print(f"H1 Tags: {result['seo']['h1_count']}")
    print(f"Images with alt text: {result['accessibility']['images_with_alt_percent']}%")

    summary = asyncio.run(summarize_audit(result['title'], result['description'], result['num_links'],result['speed'],result['seo'],result['accessibility']))
    print("\n--- Summary ---")
    print(summary)
