import asyncio
from playwright.async_api import async_playwright
import os
import requests

repo = "https://raw.githubusercontent.com/rawneko/discord-autoquest/refs/heads/main/script.js"

def update_script():
    try:
        response = requests.get(repo)
        if response.status_code == 200:
            with open("script.js", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Файл script.js успешно обновлен до последней версии с GitHub.")
        else:
            print(f"Не удалось обновить код. Статус: {response.status_code}")
    except Exception as e:
        print(f"Ошибка при обновлении: {e}")

async def run_quest_script():
    update_script()
    
    async with async_playwright() as p:
        try:
            response = requests.get("http://127.0.0.1:9222/json/version")
            cdp_url = response.json().get("webSocketDebuggerUrl")
            
            if not cdp_url:
                print("Ошибка: проверь флаг --remote-debugging-port=9222 в Discord.")
                return

            with open("script.js", "r", encoding="utf-8") as f:
                js_code = f.read()

            browser = await p.chromium.connect_over_cdp(cdp_url)
            page = browser.contexts[0].pages[0]

            await page.evaluate(js_code)
            print("Свежий код успешно внедрен.")
            
            await asyncio.sleep(1000) 

        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":

    asyncio.run(run_quest_script())
