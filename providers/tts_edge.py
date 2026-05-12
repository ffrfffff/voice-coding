from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
import subprocess
import sys


class EdgeTTS:
    def __init__(self, config: dict, output_dir: Path, ui):
        self.enabled = bool(config.get("tts_enabled", True))
        self.voice = config.get("tts_voice", "zh-CN-XiaoxiaoNeural")
        self.rate = config.get("tts_rate", "+0%")
        self.output_dir = output_dir
        self.ui = ui
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._player: subprocess.Popen | None = None

    def speak(self, text: str) -> None:
        if not self.enabled or not text.strip():
            return
        try:
            asyncio.run(self._speak_async(text.strip()))
        except ImportError:
            self.ui.warning("\u7f3a\u5c11 edge-tts\uff0c\u5df2\u8df3\u8fc7\u8bed\u97f3\u64ad\u62a5\u3002")
        except Exception as exc:
            self.ui.warning(f"TTS \u64ad\u62a5\u5931\u8d25: {exc}")

    def stop(self) -> None:
        if self._player and self._player.poll() is None:
            self._player.terminate()
        self._player = None

    async def _speak_async(self, text: str) -> None:
        import edge_tts

        self.stop()
        media_path = self.output_dir / f"summary-{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3"
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(str(media_path))
        self._play(media_path)

    def _play(self, media_path: Path) -> None:
        if sys.platform.startswith("win"):
            command = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "Add-Type -AssemblyName PresentationCore;"
                    f"$p=New-Object System.Windows.Media.MediaPlayer;"
                    f"$p.Open([Uri]'{media_path.as_uri()}');"
                    "$p.Play();"
                    "while($p.NaturalDuration.HasTimeSpan -eq $false){Start-Sleep -Milliseconds 50};"
                    "Start-Sleep -Milliseconds ([int]$p.NaturalDuration.TimeSpan.TotalMilliseconds + 200)"
                ),
            ]
            self._player = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self.ui.status(f"TTS \u6587\u4ef6\u5df2\u751f\u6210: {media_path}")
