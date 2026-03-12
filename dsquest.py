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


def is_discord_running(os_type):
    try:
        if os_type == "windows":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Discord.exe"],
                capture_output=True, text=True
            )
            return "Discord.exe" in result.stdout
        else:
            result = subprocess.run(
                ["pgrep", "-fi", "discord"],
                capture_output=True, text=True
            )
            return result.returncode == 0
    except Exception:
        return False


def kill_discord(os_type):
    print("[~] Закрываю Discord...")
    max_attempts = 5

    for attempt in range(1, max_attempts + 1):
        try:
            if os_type == "windows":
                for proc in ("Discord.exe", "Update.exe"):
                    subprocess.run(
                        ["taskkill", "/F", "/IM", proc],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            elif os_type == "linux":
                subprocess.run(
                    ["pkill", "-9", "-fi", "discord"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["flatpak", "kill", "com.discordapp.Discord"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["snap", "run", "--command=stop", "discord"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif os_type == "macos":
                subprocess.run(
                    ["pkill", "-9", "-fi", "discord"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            print(f"[!] Попытка {attempt}: ошибка при закрытии — {e}")

        time.sleep(2)

        if not is_discord_running(os_type):
            print("[+] Discord закрыт.")
            return True

        print(f"[~] Discord ещё жив, попытка {attempt}/{max_attempts}...")

    if is_discord_running(os_type):
        print("[!] Не удалось полностью закрыть Discord.")
        return False

    print("[+] Discord закрыт.")
    return True


def find_discord_exe_windows():
    local = os.environ.get("LOCALAPPDATA", "")

    for variant in ("Discord", "DiscordCanary", "DiscordPTB"):
        pattern = os.path.join(local, variant, "app-*")
        app_dirs = sorted(glob.glob(pattern), reverse=True)

        for d in app_dirs:
            exe = os.path.join(d, f"{variant}.exe")
            if os.path.isfile(exe):
                return exe
            exe_alt = os.path.join(d, "Discord.exe")
            if os.path.isfile(exe_alt):
                return exe_alt

    return None


def find_discord_exe_linux():
    for cmd in ("discord", "discord-canary", "discord-ptb"):
        try:
            result = subprocess.run(
                ["which", cmd], capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return cmd
        except FileNotFoundError:
            continue

    try:
        result = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True
        )
        if "com.discordapp.Discord" in result.stdout:
            return "flatpak"
    except FileNotFoundError:
        pass

    try:
        result = subprocess.run(
            ["snap", "list", "discord"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return "snap"
    except FileNotFoundError:
        pass

    return None


def start_discord_debug(os_type):
    print("[~] Запускаю Discord с --remote-debugging-port=9222...")
    try:
        if os_type == "windows":
            exe = find_discord_exe_windows()
            if not exe:
                print("[!] Discord.exe не найден в стандартных путях.")
                print("[!] Убедись, что Discord установлен, или запусти вручную.")
                return False

            print(f"[i] Найден: {exe}")
            subprocess.Popen(
                [exe, "--remote-debugging-port=9222"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        elif os_type == "linux":
            exe = find_discord_exe_linux()
            if not exe:
                print("[!] Discord не найден.")
                return False

            print(f"[i] Найден: {exe}")
            if exe == "flatpak":
                subprocess.Popen(
                    ["flatpak", "run", "com.discordapp.Discord",
                     "--remote-debugging-port=9222"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif exe == "snap":
                subprocess.Popen(
                    ["snap", "run", "discord", "--remote-debugging-port=9222"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [exe, "--remote-debugging-port=9222"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        elif os_type == "macos":
            mac_paths = [
                "/Applications/Discord.app/Contents/MacOS/Discord",
                "/Applications/Discord Canary.app/Contents/MacOS/Discord Canary",
                "/Applications/Discord PTB.app/Contents/MacOS/Discord PTB",
            ]
            mac_exe = None
            for p in mac_paths:
                if os.path.isfile(p):
                    mac_exe = p
                    break

            if not mac_exe:
                print("[!] Discord не найден в /Applications/")
                return False

            print(f"[i] Найден: {mac_exe}")
            subprocess.Popen(
                [mac_exe, "--remote-debugging-port=9222"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            print(f"[!] Неизвестная ОС: {os_type}")
            return False

        print("[~] Жду запуска Discord (до 60 сек, может обновляться)...")
        for i in range(60):
            time.sleep(1)
            try:
                r = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
                if r.status_code == 200:
                    print(f"[+] Debug-порт доступен (через {i + 1} сек).")
                    return True
            except (requests.ConnectionError, requests.Timeout):
                pass

        print("[!] Discord не открыл debug-порт за 60 секунд.")
        print("[!] Возможно, он обновляется. Попробуй ещё раз.")
        return False

    except Exception as e:
        print(f"[!] Ошибка при запуске Discord: {e}")
        return False


def is_debug_port_available():
    try:
        r = requests.get("http://127.0.0.1:9222/json/version", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


async def wait_for_discord_load(page, timeout=60):
    """Ждём, пока Discord реально загрузится (не splash screen)."""
    print("[~] Жду загрузки Discord...")
    for i in range(timeout):
        try:
            ready = await page.evaluate(
                "typeof webpackChunkdiscord_app !== 'undefined' "
                "&& webpackChunkdiscord_app.length > 0"
            )
            if ready:
                print(f"[+] Discord загружен (через {i + 1} сек).")
                return True
        except Exception:
            pass
        await asyncio.sleep(1)

    print("[!] Discord не загрузился полностью за 60 секунд.")
    return False


async def run_quest_script():
    update_script()

    choice = input("\n[?] Использовать автоматический инжект? (y/n): ").strip().lower()

    if choice == "y":
        os_type = detect_os()
        print(f"[i] Обнаружена ОС: {os_type}")

        if not kill_discord(os_type):
            proceed = input("[?] Discord не закрылся полностью. Продолжить? (y/n): ").strip().lower()
            if proceed != "y":
                return

        if not start_discord_debug(os_type):
            print("[!] Не удалось запустить Discord в debug-режиме. Выход.")
            return
    else:
        print("[i] Убедись, что Discord запущен с --remote-debugging-port=9222")
        if not is_debug_port_available():
            print("[!] Debug-порт 9222 недоступен.")
            print("[!] Запусти Discord с флагом --remote-debugging-port=9222")
            return

    async with async_playwright() as p:
        try:
            response = requests.get("http://127.0.0.1:9222/json/version")
            data = response.json()
            cdp_url = data.get("webSocketDebuggerUrl")

            if not cdp_url:
                print("[!] Не получен webSocketDebuggerUrl.")
                return

            browser = await p.chromium.connect_over_cdp(cdp_url)

            page = None
            for ctx in browser.contexts:
                for pg in ctx.pages:
                    url = pg.url
                    if "discord" in url and "devtools" not in url:
                        page = pg
                        break
                if page:
                    break

            if not page:
                page = browser.contexts[0].pages[0]

            if not await wait_for_discord_load(page):
                proceed = input("[?] Discord не загрузился. Всё равно внедрить? (y/n): ").strip().lower()
                if proceed != "y":
                    return

            with open("script.js", "r", encoding="utf-8") as f:
                js_code = f.read()

            await page.evaluate(js_code)
            print("[+] Скрипт успешно внедрён!")

            await asyncio.sleep(1000)

        except Exception as e:
            print(f"[!] Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(run_quest_script())
