# rk-terminauto

Watches the German consulate **RK-Termin 1.3.0.4** appointment system for open
slots and pushes a phone notification (via [ntfy](https://ntfy.sh)) when any
appear. It only *notifies* — you reserve the slot yourself in the browser.

## How it works

Each cycle (`poll.py`):

1. `GET choose_category.do` → fresh session cookie
2. `GET appointment_showMonth.do` → captcha page (image is inline base64)
3. Solve the captcha via [2captcha](https://2captcha.com) (~$1 per 1000 solves)
4. `POST appointment_showMonth.do` with the solved text → month grid
5. If the grid is **not** the "no appointments available" page → push to ntfy

Detection keys off the *negative* signal (the "no appointments" sentence), so a
real opening can't be missed by mis-guessing the available-slot markup. A wrong
captcha just skips the cycle; there's no penalty and no aggressive retry.

## Setup

```bash
# 1. Dependencies (uv manages the venv)
uv sync

# 2. Secrets
cp config.env.example config.env
# edit config.env: add your TWOCAPTCHA_API_KEY, confirm NTFY_TOPIC
```

Then install the **ntfy** app on your phone and subscribe to the exact
`NTFY_TOPIC` value. Keep that topic name unguessable.

### Test a single run

```bash
set -a && source config.env && set +a
uv run python poll.py
```

Watch the output — you should see `no appointments available` (the normal case)
and, if 2captcha is funded, no errors. If you see `captcha likely rejected`
occasionally, that's expected; the next cycle retries.

## Run every 2 minutes (launchd)

```bash
cp com.rkterminauto.poll.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.rkterminauto.poll.plist
```

Logs stream to `poll.log`. To stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.rkterminauto.poll.plist
```

If you move the project directory, update the absolute paths inside the plist
and reload it.

## Tuning

- **Interval**: `StartInterval` in the plist (seconds).
- **Target** location/realm/category: env vars in `config.env`.
- **Notification loudness**: currently pushes every cycle while slots exist
  (see `run_once` in `poll.py`).
