import asyncio
from playwright.async_api import async_playwright
import os
import platform
import subprocess
import socket
import time
import glob
import shutil
import re
import signal
import requests

repo = "https://raw.githubusercontent.com/moyunni/discord-autoquest/refs/heads/main/script.js"
running = True


def update_script():
    try:
        response = requests.get(repo)
        if response.status_code == 200:
            with open("script.js", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("[+] script.js обновлён.")
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


def get_discord_pids():
    try:
        result = subprocess.run(
            ["pgrep", "-fi", "discord"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return [int(pid) for pid in result.stdout.strip().split("\n") if pid.strip()]
    except Exception:
        pass
    return []


def is_discord_running(os_type):
    try:
        if os_type == "windows":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Discord.exe"],
                capture_output=True, text=True
            )
            return "Discord.exe" in result.stdout
        else:
            return len(get_discord_pids()) > 0
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
            else:
                pids = get_discord_pids()
                for pid in pids:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        subprocess.run(
                            ["kill", "-9", str(pid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                subprocess.run(
                    ["flatpak", "kill", "com.discordapp.Discord"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            print(f"[!] Попытка {attempt}: ошибка — {e}")

        time.sleep(2)

        if not is_discord_running(os_type):
            print("[+] Discord закрыт.")
            return True

        print(f"[~] Discord ещё жив, попытка {attempt}/{max_attempts}...")

    if is_discord_running(os_type):
        print("[!] Не удалось полностью закрыть Discord.")
        pids = get_discord_pids()
        if pids:
            print(f"[i] Оставшиеся PID: {pids}")
        return False

    print("[+] Discord закрыт.")
    return True


def is_port_open(port=9222):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def is_cdp_ready():
    try:
        r = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
        return r.status_code == 200 and "webSocketDebuggerUrl" in r.json()
    except Exception:
        return False


def find_discord_binary_linux():
    for cmd in ("discord", "discord-canary", "discord-ptb"):
        path = shutil.which(cmd)
        if not path:
            continue

        try:
            file_result = subprocess.run(
                ["file", path], capture_output=True, text=True
            )
            is_script = any(x in file_result.stdout.lower() for x in ("script", "text"))

            if is_script:
                print(f"[i] {path} — обёртка-скрипт.")
                real_paths = [
                    "/usr/share/discord/Discord",
                    "/usr/share/discord-canary/DiscordCanary",
                    "/usr/share/discord-ptb/DiscordPTB",
                    "/opt/discord/Discord",
                    "/opt/Discord/Discord",
                ]
                for rp in real_paths:
                    if os.path.isfile(rp):
                        print(f"[i] Реальный бинарник: {rp}")
                        return rp

                with open(path, "r") as f:
                    content = f.read()
                matches = re.findall(r'["\s](/[^\s"]+/[Dd]iscord[^\s"]*)', content)
                for m in matches:
                    if os.path.isfile(m):
                        print(f"[i] Бинарник из обёртки: {m}")
                        return m

                return path
            else:
                print(f"[i] {path} — ELF бинарник.")
                return path
        except Exception:
            return path

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


def launch_discord_linux(binary):
    if binary == "flatpak":
        cmd = ["flatpak", "run", "com.discordapp.Discord", "--remote-debugging-port=9222"]
    elif binary == "snap":
        cmd = ["snap", "run", "discord", "--remote-debugging-port=9222"]
    else:
        cmd = [binary, "--remote-debugging-port=9222"]

    print(f"[~] Запускаю: {' '.join(cmd)}")
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def start_discord_debug_windows():
    local = os.environ.get("LOCALAPPDATA", "")
    for variant in ("Discord", "DiscordCanary", "DiscordPTB"):
        update_exe = os.path.join(local, variant, "Update.exe")
        if os.path.isfile(update_exe):
            print(f"[i] Через Update.exe: {update_exe}")
            subprocess.Popen(
                [
                    update_exe,
                    "--processStart", "Discord.exe",
                    "--process-start-args=--remote-debugging-port=9222",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

    for variant in ("Discord", "DiscordCanary", "DiscordPTB"):
        pattern = os.path.join(local, variant, "app-*")
        for d in sorted(glob.glob(pattern), reverse=True):
            for name in (f"{variant}.exe", "Discord.exe"):
                exe = os.path.join(d, name)
                if os.path.isfile(exe):
                    print(f"[i] Fallback: {exe}")
                    subprocess.Popen(
                        [exe, "--remote-debugging-port=9222"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
    return False


def start_discord_debug_macos():
    for p in (
        "/Applications/Discord.app/Contents/MacOS/Discord",
        "/Applications/Discord Canary.app/Contents/MacOS/Discord Canary",
        "/Applications/Discord PTB.app/Contents/MacOS/Discord PTB",
    ):
        if os.path.isfile(p):
            print(f"[i] Найден: {p}")
            subprocess.Popen(
                [p, "--remote-debugging-port=9222"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
    return False


def start_discord_debug(os_type):
    print("[~] Запускаю Discord с --remote-debugging-port=9222...")

    if os_type == "windows":
        if not start_discord_debug_windows():
            print("[!] Discord не найден.")
            return False

    elif os_type == "macos":
        if not start_discord_debug_macos():
            print("[!] Discord не найден.")
            return False

    elif os_type == "linux":
        binary = find_discord_binary_linux()
        if not binary:
            print("[!] Discord не найден.")
            return False

        launch_discord_linux(binary)

        print("[~] Попытка 1: ждём debug-порт...")
        for i in range(30):
            time.sleep(1)

            if is_cdp_ready():
                print(f"[+] Debug-порт готов (через {i + 1} сек).")
                return True

            if (i + 1) % 10 == 0:
                print(f"[~] {i + 1} сек...")

        if is_cdp_ready():
            return True

        if not is_discord_running(os_type):
            print("[!] Discord не запустился.")
            return False

        print("[~] Discord запущен, но порт не открыт. Вероятно, обновление.")
        print("[~] Жду завершения обновления...")

        for i in range(60):
            time.sleep(2)
            if is_cdp_ready():
                print("[+] Debug-порт появился после обновления.")
                return True
            if (i + 1) % 5 == 0:
                print(f"[~] {(i+1)*2} сек...")

        print("[~] Порт так и не открылся. Перезапускаю Discord...")
        kill_discord(os_type)
        time.sleep(3)

        print("[~] Попытка 2: запускаю Discord с debug-флагом...")
        launch_discord_linux(binary)

        for i in range(60):
            time.sleep(1)

            if is_cdp_ready():
                print(f"[+] Debug-порт готов (через {i + 1} сек).")
                return True

            if (i + 1) % 10 == 0:
                print(f"[~] {i + 1} сек... порт {'открыт' if is_port_open(9222) else 'закрыт'}")

        print("[!] Таймаут.")
        print(f"[!] Попробуй вручную: {binary} --remote-debugging-port=9222")
        return False
    else:
        print(f"[!] Неизвестная ОС: {os_type}")
        return False

    print(f"[~] Жду debug-порт (до 90 сек)...")
    for i in range(90):
        time.sleep(1)
        if is_cdp_ready():
            print(f"[+] Debug-порт готов (через {i + 1} сек).")
            return True
        if (i + 1) % 10 == 0:
            print(f"[~] {i + 1} сек... порт {'открыт' if is_port_open(9222) else 'закрыт'}")
    print("[!] Таймаут.")
    return False


async def find_discord_page(browser, timeout=120):
    print("[~] Ищу главную страницу Discord...")

    for ctx_i, ctx in enumerate(browser.contexts):
        for pg_i, pg in enumerate(ctx.pages):
            print(f"[i] Контекст {ctx_i}, страница {pg_i}: {pg.url}")

    for attempt in range(timeout):
        for ctx in browser.contexts:
            for pg in ctx.pages:
                try:
                    has_webpack = await pg.evaluate(
                        "typeof webpackChunkdiscord_app !== 'undefined' && webpackChunkdiscord_app.length > 0"
                    )
                    if has_webpack:
                        print(f"[+] Найдена страница с webpack: {pg.url}")
                        return pg
                except Exception:
                    pass

        if (attempt + 1) % 15 == 0:
            print(f"[~] {attempt + 1} сек... webpack не найден")
            for ctx_i, ctx in enumerate(browser.contexts):
                for pg_i, pg in enumerate(ctx.pages):
                    print(f"[i]   [{ctx_i}][{pg_i}] {pg.url}")

        await asyncio.sleep(1)

    print("[!] Страница с webpack не найдена за 120 секунд.")
    return None


async def wait_for_quests_loaded(page, timeout=120):
    print("[~] Жду загрузки квестов...")
    for i in range(timeout):
        try:
            result = await page.evaluate("""
                (() => {
                    try {
                        let wpRequire = webpackChunkdiscord_app.push([[Symbol()], {}, r => r]);
                        webpackChunkdiscord_app.pop();
                        let QuestsStore = Object.values(wpRequire.c).find(x => x?.exports?.A?.__proto__?.getQuest);
                        if (!QuestsStore) return {ready: false, reason: "QuestsStore not found"};
                        let store = QuestsStore.exports.A;
                        let size = store.quests ? store.quests.size : 0;
                        return {ready: size > 0, reason: "quests.size=" + size};
                    } catch(e) {
                        return {ready: false, reason: e.toString()};
                    }
                })()
            """)
            if result.get("ready"):
                print(f"[+] Квесты загружены (через {i + 1} сек).")
                return True

            if (i + 1) % 15 == 0:
                print(f"[~] {i + 1} сек... {result.get('reason', '?')}")

        except Exception as e:
            if (i + 1) % 15 == 0:
                print(f"[~] {i + 1} сек... ошибка: {e}")

        await asyncio.sleep(1)

    print("[!] Квесты не загрузились за 120 секунд.")
    print("[i] Возможно, у тебя реально нет активных квестов.")
    return False


CONSOLE_NOISE = [
    "report only",
    "content security policy",
    "refused to load",
    "refused to connect",
    "refused to execute",
    "refused to create",
    "font-weight: bold",
    "color: purple",
    "%c[",
    "was preloaded using link preload",
    "postmessagetransport",
    "recaptcha",
    "analyticstrackimpressioncontext",
    "failed to load resource",
]


def is_quest_message(text):
    keywords = [
        "quest",
        "spoofing",
        "spoofed",
        "progress",
        "completed",
        "minutes",
        "stream",
        "heartbeat",
    ]
    text_lower = text.lower()
    return any(k in text_lower for k in keywords)


def on_console(msg):
    text = msg.text
    text_lower = text.lower()

    if text_lower.strip() in ("", "undefined", "null", "true", "false"):
        return

    if any(noise in text_lower for noise in CONSOLE_NOISE):
        return

    msg_type = msg.type

    if is_quest_message(text):
        print(f"[QUEST] {text}")
        return

    if msg_type == "error":
        print(f"[JS ERROR] {text}")
    elif msg_type == "warning":
        return
    else:
        print(f"[JS] {text}")


async def run_quest_script():
    global running
    update_script()

    choice = input("\n[?] Использовать автоматический инжект? (y/n): ").strip().lower()

    if choice == "y":
        os_type = detect_os()
        print(f"[i] ОС: {os_type}")

        if not kill_discord(os_type):
            proceed = input("[?] Discord не закрылся. Продолжить? (y/n): ").strip().lower()
            if proceed != "y":
                return

        if not start_discord_debug(os_type):
            return
    else:
        print("[i] Убедись, что Discord запущен с --remote-debugging-port=9222")
        if not is_cdp_ready():
            print("[!] Debug-порт недоступен.")
            return

    browser = None
    async with async_playwright() as p:
        try:
            response = requests.get("http://127.0.0.1:9222/json/version")
            cdp_url = response.json().get("webSocketDebuggerUrl")

            if not cdp_url:
                print("[!] Не получен webSocketDebuggerUrl.")
                return

            browser = await p.chromium.connect_over_cdp(cdp_url)
            browser.on("disconnected", lambda: set_stopped())

            page = await find_discord_page(browser)

            if not page:
                print("[!] Не удалось найти страницу Discord с webpack.")
                if browser.contexts and browser.contexts[0].pages:
                    page = browser.contexts[0].pages[0]
                    print(f"[i] Использую первую страницу: {page.url}")
                else:
                    print("[!] Нет доступных страниц.")
                    return

            page.on("console", on_console)

            quests_loaded = await wait_for_quests_loaded(page)

            if not quests_loaded:
                proceed = input("[?] Квесты не обнаружены. Всё равно внедрить? (y/n): ").strip().lower()
                if proceed != "y":
                    return

            with open("script.js", "r", encoding="utf-8") as f:
                js_code = f.read()

            await page.evaluate(js_code)
            print("[+] Скрипт внедрён.")
            print("[~] Слушаю вывод скрипта... (Ctrl+C для выхода)")

            while running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ("disconnected", "closed", "target closed", "connection closed")):
                print("[i] Соединение с Discord закрыто.")
            else:
                print(f"[!] Ошибка: {e}")
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            print("[i] Готово.")


def set_stopped():
    global running
    running = False


def main():
    loop = asyncio.new_event_loop()

    def handle_signal():
        global running
        running = False

    if platform.system().lower() != "windows":
        loop.add_signal_handler(signal.SIGINT, handle_signal)
        loop.add_signal_handler(signal.SIGTERM, handle_signal)

    try:
        loop.run_until_complete(run_quest_script())
    except KeyboardInterrupt:
        pass
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()


if __name__ == "__main__":
    main()
