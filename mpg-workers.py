#!/usr/bin/env python3
"""
Control media-preview-generator workers and processing state.

Examples:
    mpg-workers.py --gpu 1 --cpu 0
    mpg-workers.py --gpu 0 --cpu 1
    mpg-workers.py --pause
    mpg-workers.py --resume

Recommended Tautulli Setup:
    - Go to Settings → Notification Agents → Add a new Script agent
    - For "Transcode Decision Change" (transcode starts): --gpu 0 --cpu 1
    - For "Transcode Decision Change" (transcode ends):   --gpu 1 --cpu 0
"""

import sys
import argparse
import requests

# ── Configuration ─────────────────────────────────
BASE_URL   = "http://media-preview-generator:8080"
AUTH_TOKEN = ""
TIMEOUT    = 5
# ──────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({
    "Content-Type": "application/json",
    "X-Auth-Token":  AUTH_TOKEN,
})


def api_get(path: str) -> dict:
    response = SESSION.get(BASE_URL + path, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict | None = None) -> dict:
    response = SESSION.post(BASE_URL + path, json=payload or {}, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def set_gpu_workers(count: int) -> None:
    settings   = api_get("/api/settings")
    gpu_config = settings.get("gpu_config", [])

    for gpu in gpu_config:
        gpu["workers"] = count
        gpu["enabled"] = count > 0

    api_post("/api/settings", {"gpu_config": gpu_config})
    print(f"[mpg-workers] GPU workers set to {count}.")


def set_cpu_threads(count: int) -> None:
    api_post("/api/settings", {"cpu_threads": count})
    print(f"[mpg-workers] CPU threads set to {count}.")


def pause_processing() -> None:
    result = api_post("/api/processing/pause")
    print(f"[mpg-workers] Processing paused → {result}")


def resume_processing() -> None:
    result = api_post("/api/processing/resume")
    print(f"[mpg-workers] Processing resumed → {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="mpg-workers",
        description="Control media-preview-generator workers and processing state.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Transcode started — offload to CPU and pause preview generation
  mpg-workers.py --gpu 0 --cpu 1 --pause
 
  # Transcode ended — restore GPU, disable CPU, resume preview generation
  mpg-workers.py --gpu 1 --cpu 0 --resume
 
  # Change workers only, without affecting processing state
  mpg-workers.py --gpu 0 --cpu 1
  mpg-workers.py --gpu 1 --cpu 0
 
  # Pause or resume processing without changing workers
  mpg-workers.py --pause
  mpg-workers.py --resume
        """
    )
    parser.add_argument("--gpu",    type=int, metavar="INT", help="Number of GPU workers")
    parser.add_argument("--cpu",    type=int, metavar="INT", help="Number of CPU threads")

    state = parser.add_mutually_exclusive_group()
    state.add_argument("--pause",  action="store_true", help="Pause processing")
    state.add_argument("--resume", action="store_true", help="Resume processing")

    args = parser.parse_args()

    if args.gpu is None and args.cpu is None and not args.pause and not args.resume:
        parser.print_help()
        sys.exit(1)

    try:
        if args.gpu is not None:
            set_gpu_workers(args.gpu)
        if args.cpu is not None:
            set_cpu_threads(args.cpu)
        if args.pause:
            pause_processing()
        if args.resume:
            resume_processing()
    except requests.exceptions.ConnectionError:
        print(f"[mpg-workers] ERROR: Could not connect to {BASE_URL}. Is media-preview-generator running?")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"[mpg-workers] ERROR: Request timed out after {TIMEOUT}s.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"[mpg-workers] ERROR: HTTP {e.response.status_code} - {e.response.text}")
        sys.exit(1)