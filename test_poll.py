"""Tests for the detection logic — the highest-stakes part of the poller.

Run with:  uv run python -m pytest -q   (or: uv run python test_poll.py)

The fixtures in the repo root are real captures:
  response.html / elements.txt  -> a valid month grid with no slots
  (the wrong-captcha rerender and open-grid cases are synthesized here)
"""

from __future__ import annotations

import pathlib

import poll

ROOT = pathlib.Path(__file__).parent
EMPTY_GRID = (ROOT / "response.html").read_text()

# A genuinely-open grid: the real empty grid with the "no appointments" line
# removed. We've never observed a real open grid, so this is our best proxy.
OPEN_GRID = EMPTY_GRID.replace(
    "Unfortunately, there are no appointments available at this time.", ""
)

# The captcha page (what a wrong/absent solve returns). Minimal but faithful:
# it contains the captcha form id and no month-nav links.
CAPTCHA_PAGE = """
<form id="appointment_captcha_month" name="appointment_captcha_month">
  <input name="captchaText"/>
</form>
"""


def test_empty_grid_reached_but_not_available():
    r = poll.interpret(EMPTY_GRID)
    assert r.reached_month is True
    assert r.available is False


def test_open_grid_is_available():
    r = poll.interpret(OPEN_GRID)
    assert r.reached_month is True
    assert r.available is True


def test_captcha_rerender_is_not_a_grid():
    r = poll.interpret(CAPTCHA_PAGE)
    assert r.reached_month is False
    assert r.available is False


def test_unexpected_pages_are_never_available():
    # The critical regression guard: error/maintenance/expired/blank pages must
    # NOT be misread as "available" (which would page the user with a false alarm).
    for html in (
        "<html>Service temporarily unavailable</html>",
        "<html>Too many requests, try later</html>",
        "<html>Your session has expired. Please start again.</html>",
        "",
    ):
        r = poll.interpret(html)
        assert r.reached_month is False, html[:40]
        assert r.available is False, html[:40]


def test_captcha_image_extraction_roundtrip():
    raw = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")
    import base64

    b64 = base64.b64encode(raw).decode()
    html = (
        "<div style=\"background:white url('data:image/jpg;base64,"
        + b64
        + "') no-repeat\">&nbsp;</div>"
    )
    assert poll.extract_captcha_image(html) == raw
    assert poll.extract_captcha_image("<div>nothing</div>") is None


def test_schedule_tiers():
    assert poll.interval_for_minute(0) == 30
    assert poll.interval_for_minute(4) == 30
    assert poll.interval_for_minute(5) == 60
    assert poll.interval_for_minute(34) == 60
    assert poll.interval_for_minute(35) == 300
    assert poll.interval_for_minute(59) == 300


if __name__ == "__main__":
    # Allow running without pytest installed.
    import traceback

    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    raise SystemExit(1 if failed else 0)
