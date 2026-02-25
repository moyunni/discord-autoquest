# Discord Autoquest

A high-performance Python script that automates Discord quests by injecting a custom JavaScript engine directly into the Discord client via Chrome DevTools Protocol (CDP).

## 📋 Prerequisites

* Python 3.8+
* [Git](https://git-scm.com/downloads)
* Discord Desktop app

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://gitverse.ru/rawnekoo/discord-autoquest
   cd discord-autoquest
   ```

2. **Install dependencies:**
    ```bash
    pip install playwright requests
    playwright install chromium
    ```

## Usage

### Windows

1. **Close Discord completely** (check the system tray).

2. Open **CMD**(WIN + R > cmd > OK) and run this command to start Discord in debug mode:
    ```DOS
    for /d %i in ("%localappdata%\Discord\app-*") do "%i\Discord.exe" --remote-debugging-port=9222
    ```

3. In a **new** CMD window, navigate to the project folder and run:
    ```DOS
    python dsquest.py
    ```

### Linux

1. **Close Discord completely.**

2. Launch Discord via terminal with the debugging flag:
    ```bash

    discord --remote-debugging-port=9222
    ```
(Note: If you use Flatpak, use ```flatpak run com.discordapp.Discord --remote-debugging-port=9222```)

3. In a **new** terminal window, navigate to the project folder and run:
    ```bash
    python3 dsquest.py
    ```

## How it works

The script fetches the latest script.js from the GitHub repository and injects it into your running Discord instance. This method is significantly safer than traditional self-bots as it operates within the official client's environment.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

-------

- script.js was written by the Aprel Team
