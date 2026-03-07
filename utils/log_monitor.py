import os
import threading
import time
import json
import ctypes
from datetime import datetime
from urllib import request, error


class LogMonitor:
    """
    Слежение за логом Neverwinter Nights.
    Ищет ключевые слова в новых строках и шлёт их в Discord Webhook.
    """

    def __init__(
        self,
        log_path: str,
        keywords: list[str],
        webhooks: list[str],
        on_error=None,
        on_match=None,
        on_line=None,
        slayer_mode: bool = False,
        spy_enabled: bool = False,
        mention_here: bool = False,
        mention_everyone: bool = False,
    ):
        self.log_path = log_path
        self.keywords = keywords or []
        self.webhooks = webhooks or []
        self.on_error = on_error
        self.on_match = on_match
        self.on_line = on_line  # Called for every new line
        self.slayer_mode = slayer_mode  # High-priority fast polling for Open Wounds
        self.spy_enabled = spy_enabled  # Keyword tracking + Discord webhook sending
        self.mention_here = mention_here
        self.mention_everyone = mention_everyone

        self._thread: threading.Thread | None = None
        self._running = False
        self._position = 0

    # --- управление потоком ---

    def start(self):
        if self._running:
            return

        # При запуске считаем, что ранее существующие записи нас не интересуют.
        # Устанавливаем позицию чтения в конец файла, чтобы обрабатывать только новые строки.
        try:
            if self.log_path and os.path.exists(self.log_path):
                self._position = os.path.getsize(self.log_path)
            else:
                self._position = 0
        except Exception as e:
            if self.on_error:
                self.on_error(e)

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_slayer_mode(self, enabled: bool):
        """Enable/disable high-priority slayer mode for instant Open Wounds response."""
        self.slayer_mode = enabled

    def set_spy_enabled(self, enabled: bool):
        """Enable/disable spy mode (keyword matching + Discord webhook sending)."""
        self.spy_enabled = enabled

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def update_config(
        self,
        log_path: str | None = None,
        keywords: list[str] | None = None,
        webhooks: list[str] | None = None,
        mention_here: bool | None = None,
        mention_everyone: bool | None = None,
    ):
        """
        Обновить настройки «на лету» (путь, ключевые слова, вебхуки).
        При смене пути сбрасываем позицию чтения.
        """
        if log_path is not None and log_path != self.log_path:
            self.log_path = log_path
            self._position = 0
        if keywords is not None:
            self.keywords = keywords
        if webhooks is not None:
            self.webhooks = webhooks
        if mention_here is not None:
            self.mention_here = mention_here
        if mention_everyone is not None:
            self.mention_everyone = mention_everyone

    # --- основная логика чтения файла ---

    def _run(self):
        print(f"LogMonitor: Start watching {self.log_path}")
        
        # Boost thread priority on Windows for faster response in slayer mode
        try:
            if self.slayer_mode:
                # THREAD_PRIORITY_HIGHEST = 2, THREAD_PRIORITY_TIME_CRITICAL = 15
                ctypes.windll.kernel32.SetThreadPriority(
                    ctypes.windll.kernel32.GetCurrentThread(), 2
                )
                print("LogMonitor: Thread priority boosted for slayer mode")
        except Exception:
            pass
        
        while self._running:
            try:
                if not self.log_path or not os.path.exists(self.log_path):
                    time.sleep(0.5 if self.slayer_mode else 1.0)
                    continue

                size = os.path.getsize(self.log_path)
                if size < self._position:
                    self._position = 0

                # ОБЯЗАТЕЛЬНО cp1251 для русских логов
                with open(self.log_path, "r", encoding="cp1251", errors="replace") as f:
                    f.seek(self._position)

                    # Читаем новые строки
                    while True:
                        line = f.readline()
                        if not line:
                            break
                        if not line.endswith('\n'):
                            # Incomplete line yet, revert position and wait
                            f.seek(self._position)
                            break
                        
                        try:
                            # Debug log for tracing keywords
                            from datetime import datetime
                            with open("1609_manager_monitor_debug.log", "a", encoding="utf-8") as d:
                                d.write(f"[{datetime.now()}] READ: {line.rstrip(chr(10))}\n")
                                d.write(f"  KEYWORDS: {self.keywords}\n")
                        except Exception:
                            pass
                            
                        self._handle_line(line.rstrip("\n"))
                        self._position = f.tell()
            except Exception as e:
                print(f"LogMonitor Error: {e}")
                if self.on_error:
                    self.on_error(e)

            # Slayer mode: poll every 50ms for instant reaction, otherwise 1 second
            time.sleep(0.05 if self.slayer_mode else 1.0)

    def _handle_line(self, line: str):
        if not line:
            return
        # Call on_line for every line (used for Open Wounds / Auto-Fog detection)
        if self.on_line:
            try:
                self.on_line(line)
            except Exception:
                pass
        # Keyword matching + Discord sending only when spy is enabled
        if not self.spy_enabled:
            return
        matched = None
        line_lower = line.lower()
        for k in self.keywords:
            if not k:
                continue
            try:
                if k.lower() in line_lower:
                    matched = k
                    break
            except Exception:
                # Fallback to original contains check if lower() fails for any reason
                if k in line:
                    matched = k
                    break

        if matched:
            if self.on_match:
                try:
                    self.on_match(line)
                except Exception:
                    pass
            self._send_to_discord(line, matched)

    # --- отправка в Discord ---

    def _send_to_discord(self, line: str, keyword: str | None = None):
        if not self.webhooks:
            return

        # Prepare message content once
        header = f"**{keyword}** найдено в логе!\n" if keyword else "Найдено в логе!\n"
        mentions = []
        if self.mention_everyone: mentions.append("@everyone")
        elif self.mention_here: mentions.append("@here")
        
        mention_str = " ".join(mentions) + " " if mentions else ""
        content = mention_str + header + f"```\n{line}\n```"

        payload = json.dumps({
            "username": "Spy Bot [БОТ]",
            "content": content,
            "allowed_mentions": {"parse": ["everyone"]},
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        for wh in self.webhooks:
            # Handle both old format (string) and new format (dict)
            if isinstance(wh, dict):
                if not wh.get("enabled", True): continue
                url = wh.get("url")
            else:
                url = wh

            if not url or not url.startswith("http"): continue

            try:
                req = request.Request(url, data=payload, headers=headers, method="POST")
                with request.urlopen(req, timeout=5):
                    pass
            except Exception as e:
                if self.on_error:
                    name = wh.get('name', 'Webhook') if isinstance(wh, dict) else 'Webhook'
                    self.on_error(Exception(f"[{name}] Send failed: {e}"))
