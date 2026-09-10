# Personio Hacking

This labraries objective is to fill the worked hours automatically inside personio.

## How to use

You need to add a few arguments to make it work.
* Your chrome user folder.
  * Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\`
  * Mac: `~/Library/Application Support/Google/Chrome`
  * Linux: `~/.config/google-chrome/`
* The profile you use to login with Okta.
    * This usually is called `Profile 1` with increasing numbers if you have more than one profile


# Upgrade plan for usin Playwright 
1. Open Personio with a persistent browser profile.
2. Let you log in manually the first time if the Okta screen appears.
3. Navigate to the attendance page.
4. Check whether today or any past day already has an entry.
5. Fill only the missing entries.
6. Show a confirmation screen or require Enter before saving.