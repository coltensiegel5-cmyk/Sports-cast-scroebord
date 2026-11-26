SPORTSCAST STUDIO — CBS NFL + SMALLER CONTROLLER SCOREBOARD PREVIEW

CHANGES IN THIS ONE UPDATE
1. New CBS design option for NFL, matching the College Football-style layout.
2. CBS center shows SPORTSCAST in a black box with No Possession. When Home or Away has the ball, it shows down & distance. REVIEW and FLAG status still take priority.
3. Website/controller-only scoreboard preview is smaller and centered again, like before the full-screen update:
   NBC and FOX: up to 960 pixels wide; ESPN: up to 1120 pixels;
   CBS and College Football: up to 1000 pixels.
4. The five-column full-width control panel remains full-width.
5. The Scoreboard Size slider remains functional at desktop and mobile sizes.
6. OBS source dimensions are NOT changed by this adjustment. The existing OBS sizing, styles, scoreboard controls, and synchronization remain intact.

TO PUBLISH
1. Unzip this file.
2. Open https://github.com/coltensiegel5-cmyk/Sports-cast-scroebord/upload/main
3. Upload ALL THREE files into the GitHub repo root, replacing the originals:
     controller.html
     overlay.html
     app.py
4. Click Commit changes. Your Render service automatically deploys main.
5. Open the Sportscast Studio control page and hard refresh with Command+Shift+R.
6. Select NFL → CBS → No Possession to confirm SPORTSCAST is displayed in the center.

NOTE: app.py is included because the server must recognize the new CBS design for OBS.
The OBS overlay.html is included for the new CBS layout, but its output dimensions have not been altered for the smaller controller preview.
Do not upload the preview PNG to GitHub.
This ZIP is ready to upload, not yet published to the live website.
