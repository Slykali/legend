"""Local voice: text-to-speech with the OS's built-in voices and speech-to-text
with faster-whisper (runs fully offline after the model is downloaded once).

Speech-to-text needs the optional extras: ``pip install faster-whisper sounddevice numpy``.
"""
from __future__ import annotations

import difflib
import queue
import re
import shutil
import subprocess
import threading
from collections import deque

from . import platform_utils as pu


def clean_for_speech(text: str) -> str:
    text = re.sub(r"```.*?```", " (code omitted) ", text, flags=re.S)
    text = re.sub(r"https?://\S+", "a link", text)
    text = re.sub(r"[*_#`>|]+", "", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.M)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


class Speaker:
    """Speaks text using macOS `say`, Windows SAPI (PowerShell) or espeak on Linux."""

    def __init__(self, rate: int = 185, voice: str = ""):
        self.rate = rate
        self.voice = voice
        self._proc: subprocess.Popen | None = None
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._idle = threading.Event()
        self._idle.set()
        threading.Thread(target=self._worker, name="jarvis-tts", daemon=True).start()

    def _command(self, text: str) -> tuple[list[str], dict]:
        if pu.IS_MAC:
            cmd = ["say", "-r", str(self.rate)]
            if self.voice:
                cmd += ["-v", self.voice]
            return cmd + [text], {}
        if pu.IS_WINDOWS:
            # SAPI rate is -10..10; map words-per-minute around 0 at ~180 wpm.
            sapi_rate = max(-10, min(10, round((self.rate - 180) / 18)))
            script = ("Add-Type -AssemblyName System.Speech; "
                      "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                      f"$s.Rate = {sapi_rate}; "
                      "if ($env:J_VOICE) { try { $s.SelectVoice($env:J_VOICE) } catch {} } "
                      "$s.Speak($env:J_TTS)")
            exe = shutil.which("powershell") or "powershell"
            return [exe, "-NoProfile", "-Command", script], {"J_TTS": text, "J_VOICE": self.voice}
        for exe in ("espeak-ng", "espeak"):
            if shutil.which(exe):
                return [exe, "-s", str(self.rate), text], {}
        if shutil.which("spd-say"):
            return ["spd-say", "-w", text], {}
        return [], {}

    def _worker(self) -> None:
        import os
        while True:
            text = self._queue.get()
            if text is None:
                return
            cmd, env = self._command(text)
            if cmd:
                try:
                    self._proc = subprocess.Popen(cmd, env={**os.environ, **env},
                                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                  creationflags=pu.NO_WINDOW)
                    self._proc.wait()
                except OSError:
                    pass
                finally:
                    self._proc = None
            if self._queue.empty():
                self._idle.set()

    def say(self, text: str, block: bool = False) -> None:
        text = clean_for_speech(text)
        if not text:
            return
        self._idle.clear()
        self._queue.put(text)
        if block:
            self._idle.wait()

    def wait(self) -> None:
        self._idle.wait()

    def stop(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._idle.set()


def match_wake_word(transcript: str, wake_word: str = "jarvis") -> tuple[bool, str]:
    """Return (heard, rest_of_command). Tolerates mis-hearings like 'Jarvice'."""
    words = re.findall(r"[\w']+", transcript.lower())
    for i, word in enumerate(words[:4]):
        if difflib.SequenceMatcher(None, word, wake_word.lower()).ratio() >= 0.72:
            # Keep the original casing/punctuation of the remainder.
            parts = re.split(r"[\w']+", transcript, maxsplit=i + 1)
            rest = parts[-1] if len(parts) > i + 1 else ""
            return True, rest.lstrip(" ,.!?:;-").strip()
    return False, ""


class Listener:
    """Records from the microphone until you stop talking, then transcribes locally."""

    RATE = 16000
    BLOCK = 480  # 30 ms

    def __init__(self, model: str = "base.en", device: str = "auto"):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("Voice input needs: pip install faster-whisper sounddevice numpy") from exc
        self.model_name = model
        self.whisper = WhisperModel(model, device=device, compute_type="int8")
        self._lock = threading.Lock()

    def record(self, start_timeout: float | None = None, max_seconds: float = 20,
               silence_seconds: float = 0.9) -> "object | None":
        import numpy as np
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("Microphone input needs: pip install sounddevice") from exc

        blocks_per_sec = self.RATE / self.BLOCK
        preroll: deque = deque(maxlen=int(0.3 * blocks_per_sec))
        recorded: list = []
        noise: list[float] = []
        speaking, silent_blocks, waited = False, 0, 0
        with sd.InputStream(samplerate=self.RATE, channels=1, dtype="float32",
                            blocksize=self.BLOCK) as stream:
            while True:
                block, _ = stream.read(self.BLOCK)
                block = block[:, 0].copy()
                rms = float(np.sqrt(np.mean(block ** 2)))
                if len(noise) < 10:
                    noise.append(rms)
                    continue
                threshold = max(float(np.median(noise)) * 3.0, 0.012)
                if not speaking:
                    preroll.append(block)
                    waited += 1
                    if rms > threshold:
                        speaking = True
                        recorded.extend(preroll)
                    elif start_timeout is not None and waited > start_timeout * blocks_per_sec:
                        return None
                    else:
                        noise.append(rms)
                        noise[:] = noise[-50:]
                    continue
                recorded.append(block)
                silent_blocks = silent_blocks + 1 if rms < threshold * 0.8 else 0
                if silent_blocks > silence_seconds * blocks_per_sec:
                    break
                if len(recorded) > max_seconds * blocks_per_sec:
                    break
        if len(recorded) < 0.35 * blocks_per_sec:
            return None
        return np.concatenate(recorded)

    def transcribe(self, audio) -> str:
        """Transcribe a numpy array (16 kHz mono) or an audio file path."""
        lang = "en" if self.model_name.endswith(".en") else None
        with self._lock:
            segments, _ = self.whisper.transcribe(audio, beam_size=1, language=lang, vad_filter=True)
            return " ".join(s.text.strip() for s in segments).strip()

    def listen(self, start_timeout: float | None = None) -> str:
        audio = self.record(start_timeout=start_timeout)
        return self.transcribe(audio) if audio is not None else ""


_shared_listener: Listener | None = None
_listener_lock = threading.Lock()


def shared_listener(model: str = "base.en", device: str = "auto") -> Listener:
    global _shared_listener
    with _listener_lock:
        if _shared_listener is None:
            _shared_listener = Listener(model, device)
        return _shared_listener
