#!/usr/bin/env python3
"""Poll the German consulate (RK-Termin 1.3.0.4) appointment system for open
slots and push a notification via ntfy when any appear.

Flow per run:
  1. GET choose_category.do        -> fresh JSESSIONID cookie
  2. GET appointment_showMonth.do  -> captcha page (inline base64 JPEG + token)
  3. solve captcha via 2captcha    -> captcha text
  4. POST appointment_showMonth.do -> month grid
  5. parse grid; if not the "no appointments" page, notify via ntfy

Detection is keyed off the reliable *negative* signal: a valid month page that
does NOT contain the "no appointments available" sentence is treated as a hit.
This cannot miss a real opening by guessing the available-slot markup wrong.

Config comes from environment variables (see config.env.example). A wrong
captcha simply means we skip this cycle and try again next time, so the script
never blocks or retries aggressively.
"""

from __future__ import annotations

import base64
import os
import re
import sys
import time
from dataclasses import dataclass

import requests

# --- Target -----------------------------------------------------------------
BASE = "https://service2.diplo.de/rktermin/extern"
LOCATION_CODE = os.environ.get("RK_LOCATION_CODE", "losa")
REALM_ID = os.environ.get("RK_REALM_ID", "1363")
CATEGORY_ID = os.environ.get("RK_CATEGORY_ID", "3301")

# Browser-like headers; the server is picky about looking like a real client.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)

# The sentence shown on a valid month page when nothing is available. Matched
# loosely (whitespace-insensitive) so minor markup changes don't break it.
NO_APPT_PATTERN = re.compile(
    r"there\s+are\s+no\s+appointments\s+available", re.IGNORECASE
)

# Presence of the captcha form means the captcha was wrong (or not yet solved)
# and the server re-rendered the gate. A real month grid never contains it.
# NB: we can't use the bare "appointment_showMonth.do" string as a month-grid
# marker because it also appears in the captcha form's action attribute.
CAPTCHA_FORM_PATTERN = re.compile(r"appointment_captcha_month", re.IGNORECASE)

# Captcha image is inlined as: background:white url('data:image/jpg;base64,....')
CAPTCHA_IMG_PATTERN = re.compile(
    r"data:image/(?:jpg|jpeg|png);base64,([A-Za-z0-9+/=]+)"
)

TWOCAPTCHA_IN = "https://2captcha.com/in.php"
TWOCAPTCHA_RES = "https://2captcha.com/res.php"


@dataclass
class Config:
    twocaptcha_key: str
    ntfy_topic: str
    ntfy_server: str = "https://ntfy.sh"
    request_locale: str = "en"

    @classmethod
    def from_env(cls) -> "Config":
        key = os.environ.get("TWOCAPTCHA_API_KEY", "").strip()
        topic = os.environ.get("NTFY_TOPIC", "").strip()
        missing = [
            name
            for name, val in (
                ("TWOCAPTCHA_API_KEY", key),
                ("NTFY_TOPIC", topic),
            )
            if not val
        ]
        if missing:
            sys.exit(f"Missing required env vars: {', '.join(missing)}")
        return cls(
            twocaptcha_key=key,
            ntfy_topic=topic,
            ntfy_server=os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/"),
            request_locale=os.environ.get("RK_LOCALE", "en"),
        )


def log(msg: str) -> None:
    """Timestamped line to stdout (captured by launchd into the log file)."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    return s


def _params() -> dict[str, str]:
    return {
        "locationCode": LOCATION_CODE,
        "realmId": REALM_ID,
        "categoryId": CATEGORY_ID,
    }


def fetch_captcha_page(s: requests.Session, cfg: Config) -> str:
    """Establish a session and load the captcha-gated month page."""
    # Step 1: choose_category establishes JSESSIONID + KEKS cookies.
    s.get(
        f"{BASE}/choose_category.do",
        params={**_params(), "request_locale": cfg.request_locale},
        timeout=30,
    )
    # Step 2: the month page, which returns the captcha form.
    r = s.get(
        f"{BASE}/appointment_showMonth.do",
        params={**_params(), "request_locale": cfg.request_locale},
        headers={
            "Referer": f"{BASE}/choose_category.do?"
            f"locationCode={LOCATION_CODE}&realmId={REALM_ID}"
            f"&categoryId={CATEGORY_ID}"
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.text


def extract_captcha_image(html: str) -> bytes | None:
    m = CAPTCHA_IMG_PATTERN.search(html)
    if not m:
        return None
    try:
        return base64.b64decode(m.group(1))
    except Exception:
        return None


def solve_captcha(cfg: Config, image: bytes) -> str | None:
    """Submit the captcha image to 2captcha and poll for the solution.

    Returns the solved text, or None on failure/timeout (we just skip a cycle).
    """
    try:
        submit = requests.post(
            TWOCAPTCHA_IN,
            data={
                "key": cfg.twocaptcha_key,
                "method": "base64",
                "json": "1",
                # RK-Termin captchas are short alphanumeric strings.
                "regsense": "1",  # case-sensitive
                # With method=base64 the image goes in the `body` field.
                "body": base64.b64encode(image).decode("ascii"),
            },
            timeout=30,
        ).json()
    except Exception as e:
        log(f"2captcha submit error: {e}")
        return None

    if submit.get("status") != 1:
        log(f"2captcha submit rejected: {submit.get('request')}")
        return None

    captcha_id = submit["request"]

    # Poll for the result. 2captcha typically solves in 10-20s.
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        time.sleep(5)
        try:
            res = requests.get(
                TWOCAPTCHA_RES,
                params={
                    "key": cfg.twocaptcha_key,
                    "action": "get",
                    "id": captcha_id,
                    "json": "1",
                },
                timeout=30,
            ).json()
        except Exception as e:
            log(f"2captcha poll error: {e}")
            continue

        if res.get("status") == 1:
            return res["request"].strip()
        if res.get("request") == "CAPCHA_NOT_READY":
            continue
        log(f"2captcha solve failed: {res.get('request')}")
        return None

    log("2captcha timed out")
    return None


def submit_month(s: requests.Session, cfg: Config, captcha_text: str) -> str:
    """POST the solved captcha and return the resulting month-page HTML."""
    data = {
        "captchaText": captcha_text,
        "rebooking": "",
        "token": "",
        "lastname": "",
        "firstname": "",
        "email": "",
        "locationCode": LOCATION_CODE,
        "realmId": REALM_ID,
        "categoryId": CATEGORY_ID,
        "openingPeriodId": "",
        "date": "",
        "dateStr": "",
        "action:appointment_showMonth": "Continue",
    }
    r = s.post(
        f"{BASE}/appointment_showMonth.do",
        data=data,
        headers={
            "Referer": f"{BASE}/appointment_showMonth.do?"
            f"locationCode={LOCATION_CODE}&realmId={REALM_ID}"
            f"&categoryId={CATEGORY_ID}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.text


@dataclass
class CheckResult:
    reached_month: bool  # True if we got a valid month grid (captcha accepted)
    available: bool  # True if slots appear to be open


def interpret(html: str) -> CheckResult:
    # If the captcha form is present, the solve was rejected — not a month grid.
    if CAPTCHA_FORM_PATTERN.search(html):
        return CheckResult(reached_month=False, available=False)
    no_appt = bool(NO_APPT_PATTERN.search(html))
    return CheckResult(reached_month=True, available=not no_appt)


def notify(cfg: Config, title: str, message: str, priority: str = "urgent") -> None:
    url = f"{cfg.ntfy_server}/{cfg.ntfy_topic}"
    booking_url = (
        f"{BASE}/appointment_showMonth.do?"
        f"locationCode={LOCATION_CODE}&realmId={REALM_ID}&categoryId={CATEGORY_ID}"
    )
    try:
        requests.post(
            url,
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "calendar,de",
                "Click": booking_url,
            },
            timeout=30,
        )
    except Exception as e:
        log(f"ntfy push error: {e}")


def run_once(cfg: Config) -> None:
    s = new_session()
    try:
        page = fetch_captcha_page(s, cfg)
    except Exception as e:
        log(f"failed to load captcha page: {e}")
        return

    image = extract_captcha_image(page)
    if image is None:
        log("no captcha image found on page (layout changed or blocked?)")
        return

    captcha_text = solve_captcha(cfg, image)
    if not captcha_text:
        log("captcha unsolved; skipping cycle")
        return

    try:
        month_html = submit_month(s, cfg, captcha_text)
    except Exception as e:
        log(f"month submit failed: {e}")
        return

    result = interpret(month_html)
    if not result.reached_month:
        # Almost always a wrong captcha -> bounced back to the captcha form.
        log("captcha likely rejected (no month grid); skipping cycle")
        return

    if result.available:
        log("!!! APPOINTMENTS APPEAR AVAILABLE -> notifying")
        notify(
            cfg,
            title="RK-Termin slot available!",
            message=(
                f"Possible appointment open for {LOCATION_CODE} "
                f"(realm {REALM_ID}, cat {CATEGORY_ID}). "
                "Open the booking page NOW to reserve."
            ),
        )
    else:
        log("no appointments available")


# --- Tiered polling schedule ------------------------------------------------
# Appointments tend to be released at the top of the hour, so poll fastest then
# and back off as the hour wears on. Each tier is (start_minute, interval_secs)
# and applies until the next tier's start_minute.
#   :00-:05  every 30s   (catch the drop)
#   :05-:35  every 60s
#   :35-:00  every 300s
SCHEDULE = [(0, 30), (5, 60), (35, 300)]


def interval_for_minute(minute: int) -> int:
    """Return the poll interval (seconds) for the given minute-of-hour."""
    chosen = SCHEDULE[0][1]
    for start_minute, secs in SCHEDULE:
        if minute >= start_minute:
            chosen = secs
    return chosen


def main() -> None:
    cfg = Config.from_env()
    log(
        f"starting poller for {LOCATION_CODE} "
        f"(realm {REALM_ID}, cat {CATEGORY_ID}); "
        f"schedule={SCHEDULE}"
    )
    while True:
        start = time.monotonic()
        try:
            run_once(cfg)
        except Exception as e:  # never let one bad cycle kill the daemon
            log(f"unexpected error in cycle: {e}")

        minute = time.localtime().tm_min
        interval = interval_for_minute(minute)
        # Subtract the time the cycle already took (captcha solve can be ~15s)
        # so the effective cadence matches the target interval.
        elapsed = time.monotonic() - start
        sleep_for = max(1.0, interval - elapsed)
        log(f"next poll in {sleep_for:.0f}s (tier={interval}s, minute=:{minute:02d})")
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
