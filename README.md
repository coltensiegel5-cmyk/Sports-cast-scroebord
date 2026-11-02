# Sportscast Studio — NBC + ESPN, Flag + Timeout Broadcast Edition

Includes: team-logo and record improvements, team-highlighted penalty flags, near-down yardage +/- buttons, resized OBS overlay, and new team timeout calls.

## Timeout controls

- **+ / −** adjust each team's remaining timeouts (0–3). The scoreboard shows only the remaining marks — used marks disappear.
- Press **TIMEOUT · TEAM** directly below that team's +/- controls to use one timeout and show a team-colored **TIMEOUT** where down-and-distance normally appears, plus a strip reading `TIMEOUT · TEAM NAME · 2 REMAINING`.
- Press **Hide Timeout Strip** in Game Information when the timeout ends. This does not restore any used timeout.
- Selecting a penalty flag clears the timeout announcement; calling a timeout clears the penalty graphic.

## Publishing

Upload `controller.html`, `overlay.html`, `app.py`, and `README.md` to your existing `Sports-cast-scroebord` GitHub repository, replacing the existing files. Keep `index.html` unchanged. Render automatically deploys the new commit.

## OBS

Browser Source URL: `https://sportscast-studio-colten.onrender.com/obs`
Recommended width **1280** and height **220**. The layout also scales down for other sizes.

Your controller remains private and access-protected. Never upload or share your controller password.
