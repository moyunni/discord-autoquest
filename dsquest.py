import asyncio
from playwright.async_api import async_playwright
import os
import sys
import platform
import subprocess
import time
import glob
import requests

repo = "https://raw.githubusercontent.com/moyunni/discord-autoquest/refs/heads/main/script.js"


def update_script():
    try:
        response = requests.get(repo)
        if response.status_code == 200:
            with open("script.js", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("[+] script.js обновлён до последней версии с GitHub.")
        else:
            print(f"[!] Не удалось обновить скрипт. Статус: {response.status_code}")
    except Exception as e:
        print(f"[!] Ошибка при обновлении: {e}")


def detect_os():
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    return system


def kill_discord(os_type):
    print("[~] Закрываю Discord...")
    try:
        if os_type == "windows":
            subprocess.run(
                ["taskkill", "/F", "/IM", "Discord.exe"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif os_type == "linux":
            subprocess.run(
                ["pkill", "-f", "[Dd]iscord"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["flatpak", "kill", "com.discordapp.Discord"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif os_type == "macos":
            subprocess.run(
                ["pkill", "-f", "Discord"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        time.sleep(3)
        print("[+] Discord закрыт.")
    except Exception as e:
        print(f"[!] Ошибка при закрытии Discord: {e}")


def start_discord_debug(os_type):
    print("[~] Запускаю Discord с --remote-debugging-port=9222...")
    try:
        if os_type == "windows":
            local = os.environ.get("LOCALAPPDATA", "")
            pattern = os.path.join(local, "Discord", "app-*")
            app_dirs = sorted(glob.glob(pattern), reverse=True)

            discord_path = None
            for d in app_dirs:
                exe = os.path.join(d, "Discord.exe")
                if os.path.isfile(exe):
                    discord_path = exe
                    break

            if not discord_path:
                print("[!] Discord.exe не найден. Убедись, что Discord установлен.")
                return False

            subprocess.Popen(
                [discord_path, "--remote-debugging-port=9222"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        elif os_type == "linux":
            started = False
            for cmd in ("discord", "discord-canary", "discord-ptb"):
                try:
                    subprocess.Popen(
                        [cmd, "--remote-debugging-port=9222"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    started = True
                    break
                except FileNotFoundError:
                    continue

            if not started:
                try:
                    subprocess.Popen(
                        [
                            "flatpak",
                            "run",
                            "com.discordapp.Discord",
                            "--remote-debugging-port=9222",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    started = True
                except FileNotFoundError:
                    pass

            if not started:
                print("[!] Discord не найден. Убедись, что он установлен.")
                return False

        elif os_type == "macos":
            mac_exe = "/Applications/Discord.app/Contents/MacOS/Discord"
            if os.path.isfile(mac_exe):
                subprocess.Popen(
                    [mac_exe, "--remote-debugging-port=9222"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                print("[!] Discord не найден в /Applications/Discord.app")
                return False
        else:
            print(f"[!] Неизвестная ОС: {os_type}")
            return False

        print("[~] Жду запуска Discord...")
        for _ in range(30):
            time.sleep(1)
            try:
                r = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
                if r.status_code == 200:
                    print("[+] Discord запущен с debug-портом.")
                    return True
            except Exception:
                pass

        print("[!] Discord не запустился за 30 секунд.")
        return False

    except Exception as e:
        print(f"[!] Ошибка при запуске Discord: {e}")
        return False


async def run_quest_script():
    update_script()

    choice = input("\n[?] Использовать автоматический инжект? (y/n): ").strip().lower()

    if choice == "y":
        os_type = detect_os()
        print(f"[i] Обнаружена ОС: {os_type}")
        kill_discord(os_type)
        if not start_discord_debug(os_type):
            print("[!] Не удалось запустить Discord в debug-режиме. Выход.")
            return
    else:
        print("[i] Убедись, что Discord запущен с --remote-debugging-port=9222")

    async with async_playwright() as p:
        try:
            response = requests.get("http://127.0.0.1:9222/json/version")
            cdp_url = response.json().get("webSocketDebuggerUrl")

            if not cdp_url:
                print("[!] Не получен webSocketDebuggerUrl. Проверь debug-порт.")
                return

            with open("script.js", "r", encoding="utf-8") as f:
                js_code = f.read()

            browser = await p.chromium.connect_over_cdp(cdp_url)
            page = browser.contexts[0].pages[0]

            await page.evaluate(js_code)
            print("[+] Скрипт успешно внедрён.")

            await asyncio.sleep(1000)

        except Exception as e:
            print(f"[!] Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(run_quest_script())
