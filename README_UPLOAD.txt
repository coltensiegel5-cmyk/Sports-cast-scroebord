SPORTSCAST STUDIO — ABC / ESPN COLLEGE FOOTBALL — CLASSIC GLOSSY UPDATE

Based on the November 27 Prime Video and Settings Fix ZIP.
Refined the existing ABC / ESPN college-only design with classic glossy broadcast gradients, curved metallic shoulders, compact proportions and revised typography. Other designs unchanged.
Rank next to the school name. Center down & distance uses possession team's custom color.
No possession shows SPORTS CAST. Existing controls are reused. College design is saved locally and sent to OBS in the server state.

INSTALL
1. Open https://github.com/coltensiegel5-cmyk/Sports-cast-scroebord/upload/main
2. Upload controller.html, overlay.html and app.py from this ZIP to the repository root.
3. Commit changes and allow Render to deploy.
4. Refresh controller and OBS browser source. Select College Football > ABC / ESPN.
Controller: https://sportscast-studio-colten.onrender.com/control
OBS: https://sportscast-studio-colten.onrender.com/obs
Keep controller open during broadcasts. Use Command+Shift+R if cached.

Local tests: controller design switching, rank, possession colors, no possession, NFL selection independence, and OBS state updates passed. Official broadcast font was approximated with system fonts. Production deployment and external logo/record feeds not tested.

FONT UPDATE: custom vector score and clock numerals, wider team labels. No external font files. Only ABC / ESPN CFB design is affected.

TRANSLUCENT UPDATE: ABC / ESPN team-color gradient stops use 76% opacity, preserving opaque lettering and logos. Gloss and shadows vary the effective transparency. Other designs and server unchanged.

ABC/ESPN: when neither team has possession, the down strip displays SPORTSCAST (one word). Review, flag and timeout announcements retain priority.
