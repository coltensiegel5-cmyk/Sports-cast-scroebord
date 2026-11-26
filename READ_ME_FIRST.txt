SPORTSCAST STUDIO — OBS BLANK SCREEN FIX
=========================================
Release: OBS scoreboard recovery after refresh or Render restart.

CHANGED FILES:
  overlay.html  — restore last valid scoreboard from OBS browser storage;
                  display a neutral SPORTSCAST preview if no game has synced.
  app.py        — save sanitized current game state on server local disk and
                  recover it after an app process restart (while disk persists).

UNCHANGED FILE:
  controller.html — already includes the current CBS, NFL, College Football,
                    five-column controls, touchdown and all prior fixes.
                    DO NOT replace this file for this update.

UPLOAD INSTRUCTIONS:
1. Open your GitHub repo's main branch upload page:
   https://github.com/coltensiegel5-cmyk/Sports-cast-scroebord/upload/main
2. Upload ONLY overlay.html and app.py from this ZIP.
3. Click Commit changes. Render automatically deploys the new code.
4. Open https://sportscast-studio-colten.onrender.com/control
   in your trusted browser and leave the controller open while using OBS.
5. Open/refresh https://sportscast-studio-colten.onrender.com/obs
   in OBS Browser Source. Use Ctrl+F5 in browser if an old page is cached.

WHAT TO EXPECT:
- If OBS previously saw a game in the same browser profile, refreshing
  restores that last scoreboard even if Render currently has no state.
- If OBS has never seen a game, a clearly labeled neutral preview shows
  until the controller sends a real game. It never pretends to show a live game.
- Server local state survives Python process restarts while its filesystem
  remains available. Free Render instances may replace the filesystem on
  deploys, so server-side persistence is NOT guaranteed across deployments.
- Keep your controller open during a live broadcast for continuous live sync.
- No changes to CBS/NBC/FOX/ESPN/College scoreboard designs or OBS dimensions.
