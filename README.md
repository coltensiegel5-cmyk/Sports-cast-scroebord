# Sportscast Studio — scoreboard readability and OBS timeout fix

This is an update to your existing GitHub repository and Render site, not a new website.

## Improvements

- Logos are constrained to their allotted area with `object-fit: contain` on both NBC and ESPN layouts. They no longer spill over scores or labels.
- Team abbreviations and win–loss records have larger, bolder, high-contrast lettering.
- **Down** changes only the ordinal (1ST, 2ND, 3RD, 4TH); the existing **Distance** +/- and GOAL/INCHES controls remain.
- Timeout announcements get a higher visible stacking layer and a reliable client-to-OBS sync retry every 2.5 seconds, plus an immediate push when timeout is called or hidden.
- The announcement is still manually cleared by **Hide Timeout Strip** and remains within a 1280×220 OBS browser source.

## Publish

Upload `controller.html`, `overlay.html`, `app.py`, and `index.html` to the root of your existing `Sports-cast-scroebord` GitHub repository, replacing the existing files. Render should auto-deploy the main branch. `app.py` and `index.html` are included unchanged so the four-file upload is easy.

For OBS: Browser Source URL ending `/obs`, Width=1280, Height=220. Click **Refresh cache of current page** in Browser Source properties after Render deploys. Keep your controller tab open while streaming.
