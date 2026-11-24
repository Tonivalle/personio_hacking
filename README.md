# Personio Tracker (`ptrack`)

Automate your daily Personio time tracking and backfilling without the hassle of repeating logins or doing tedious data entry.

`ptrack` gives you two core functions:
1. **Daily check**: checks whether today is a scheduled workday and shows a friendly system alert with your work hours. With one click, your hours are logged.
2. **Backfill**: scans the current month and fills all missing past workdays in bulk.

It also supports attaching to an already-open Chrome browser window, so you never have to redo Okta single sign-on authentication every time the tool runs.

---

## Quickstart

### 1. Install `ptrack`

Install [uv](https://docs.astral.sh/uv/), then choose one of the following options.

#### Option A: Install the release

Install the wheel from the GitHub release:

```bash
uv tool install --with-executables-from playwright https://github.com/Tonivalle/personio_hacking/releases/download/v0.2.0/personio_hacking-0.2.0-py3-none-any.whl
```

This installs `ptrack`, `personio-track`, and the matching `playwright` command. If the commands are not on your PATH, run `uv tool update-shell` and restart your shell.

If you plan to use standalone browser sessions, install Chromium:

```bash
playwright install chromium
```

#### Option B: Clone the repository

```bash
git clone https://github.com/Tonivalle/personio_hacking.git
cd personio_hacking
uv sync
```

For standalone browser sessions, install Chromium:

```bash
uv run playwright install chromium
```

Run the examples below from the checkout with `uv run` before each command, for example `uv run ptrack daily`.

### 2. Configure your schedule
Create a configuration directory:

```bash
mkdir -p ~/.config/ptrack
```

Create `~/.config/ptrack/config.yml` with your company domain and hours:

```yaml
# Your company Personio URL
personio_url: https://yourcompany.personio.de

# Daily prompt time in 24-hour format (HH:MM)
daily_prompt_time: "17:30"

# Prompt style: "auto" (native dialog on macOS), "dialog", or "terminal"
prompt_type: "auto"

# Define your work intervals for each day (1 = Monday, 5 = Friday)
schedules:
  - days: [1, 2, 3, 4]  # Monday to Thursday
    intervals:
      - {start: "09:00", end: "13:00"}
      - {start: "14:00", end: "18:00"}

  - days: [5]  # Friday
    intervals:
      - {start: "09:00", end: "15:30"}
```

`ptrack` also accepts `config.yml` in the current directory or an explicit `--config` path. Keep your configuration and browser profile private; the repository's `.gitignore` only protects files inside a Git checkout.

---

## How to Avoid Logging in with Okta Every Time (Reusing Chrome)

If your company uses Okta or single sign-on, authenticating every time a script starts can get annoying. You can let `ptrack` connect directly to your existing, already-logged-in Google Chrome window through the Chrome DevTools Protocol (CDP).

### Step 1: Start Chrome with remote debugging enabled
Close Chrome completely (press `Cmd + Q` on macOS). Then start Chrome from your terminal with the debugging port flag:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 &
```

**Tip for convenience:** You can create an alias in your `~/.zshrc` file:
```bash
alias chrome-debug='/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 &'
```

### Step 2: Enable CDP in `config.yml`
In your `config.yml`, uncomment or add:
```yaml
cdp_port: 9222
```

Whenever `cdp_port` is set:
- `ptrack` connects to your open Chrome window without launching a separate browser.
- It finds your existing Personio tab (or opens a new one if not already open).
- Since you are already signed in to Okta in your everyday browser, it fills your attendance with zero login prompts.
- When finished, it disconnects cleanly and leaves your Chrome window open.

If `cdp_port` is omitted or commented out, `ptrack` automatically falls back to a standalone persistent profile saved in `playwright_profile` next to the configuration file.

---

## CLI Usage

You can run commands using `ptrack` (or `personio-track`):

### 1. Daily tracking
Checks today's date against your schedule. If today is a working day, a system dialog pops up showing your hours:

```bash
ptrack daily
```

To run non-interactively (for automated scripts or headless workflows):
```bash
ptrack daily --yes
```

### 2. Backfill missing days
Scans all working days of the current month and fills any unfilled days in bulk:

```bash
ptrack backfill
```

### 3. Automatic Daily Scheduling on macOS (`launchd`)
You can set up macOS to automatically trigger the daily reminder at your configured `daily_prompt_time` (e.g. 17:30):

- **Install the schedule**:
  ```bash
  ptrack schedule install
  ```
  This creates a background launch agent in `~/Library/LaunchAgents/com.ptrack.daily.plist` that triggers every workday at the time defined in `config.yml`. When the time comes, a dialog appears asking if you want to track today. Click **Track Now** and you are done.

- **Check schedule status**:
  ```bash
  ptrack schedule status
  ```

- **Remove the schedule**:
  ```bash
  ptrack schedule uninstall
  ```

---

## Development and Testing

In a repository checkout, install development dependencies with `uv sync`.

Run test suite:
```bash
make test
```

Check formatting, linting, and types:
```bash
make check
```

Autoformat code:
```bash
make format
```
