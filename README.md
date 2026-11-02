# Sportscast Studio — NBC / ESPN scoreboard quick switch

This update adds two large buttons at the top of the controller, **NBC** and **ESPN**.

- **NBC**: original rounded-wing scoreboard (Classic).
- **ESPN**: new compact black scoreboard with possession-colored down & distance in the middle; when no team has possession, it shows SPORTSCAST instead.
- Choose either button at any time. It updates the controller preview, saves the choice in that browser, and automatically synchronizes the design to the `/obs` display. The Settings design selector still works and stays synchronized.
- Team logos, scores, clock, FLAG, timeout controls, and editing remain available.

## Publish to your existing Render site

Unzip and upload `controller.html`, `overlay.html`, and `app.py` to the root of your existing GitHub repository, choosing to replace existing files. The `README.md` is optional. **Do not upload the zip itself.** Render auto-deploys the updated `main` branch.

Do not replace your existing `render.yaml` or change the private `SPORTSCAST_CONTROL_KEY` setting.

The ESPN label is a visual style choice, not an official ESPN asset or an ESPN-operated scoreboard.
