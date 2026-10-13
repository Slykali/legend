import type { Reminder } from "../types";
import { formatDue } from "./dates";

export function notificationsSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function getPermission(): NotificationPermission | "unsupported" {
  if (!notificationsSupported()) return "unsupported";
  try {
    return Notification.permission;
  } catch {
    return "unsupported";
  }
}

export async function requestPermission(): Promise<NotificationPermission | "unsupported"> {
  if (!notificationsSupported()) return "unsupported";
  try {
    // Older Safari only supports the callback form; handle both.
    const result = await new Promise<NotificationPermission>((resolve, reject) => {
      try {
        const maybePromise = Notification.requestPermission((p) => resolve(p));
        if (maybePromise && typeof maybePromise.then === "function") {
          maybePromise.then(resolve, reject);
        }
      } catch (err) {
        reject(err);
      }
    });
    return result;
  } catch {
    return getPermission();
  }
}

export function showNotification(r: Reminder): void {
  if (getPermission() !== "granted") return;
  try {
    const notes = r.notes.trim();
    const body = notes || formatDue(r.dueAt);
    const notification = new Notification(r.title, {
      body,
      tag: r.id,
      icon: "/icon.svg",
    });
    notification.onclick = () => {
      try {
        window.focus();
      } catch {
        /* ignore */
      }
      notification.close();
    };
  } catch {
    /* Notification constructor can throw (e.g. Android Chrome requires a service worker). */
  }
}

type AudioContextCtor = typeof AudioContext;

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (audioCtx) return audioCtx;
  if (typeof window === "undefined") return null;
  const Ctor: AudioContextCtor | undefined =
    window.AudioContext ??
    (window as unknown as { webkitAudioContext?: AudioContextCtor }).webkitAudioContext;
  if (!Ctor) return null;
  audioCtx = new Ctor();
  return audioCtx;
}

function playTone(ctx: AudioContext, frequency: number, start: number, duration: number): void {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(frequency, start);

  // Soft attack, exponential decay for a bell-like tone.
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(0.18, start + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);

  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(start);
  osc.stop(start + duration + 0.05);
}

export function playChime(): void {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const play = () => {
      try {
        const t = ctx.currentTime + 0.01;
        playTone(ctx, 880, t, 0.45); // A5
        playTone(ctx, 1318.51, t + 0.16, 0.6); // E6
      } catch {
        /* ignore */
      }
    };
    if (ctx.state === "suspended") {
      ctx.resume().then(play, () => {
        /* autoplay blocked; ignore */
      });
    } else {
      play();
    }
  } catch {
    /* Web Audio unsupported or blocked */
  }
}
