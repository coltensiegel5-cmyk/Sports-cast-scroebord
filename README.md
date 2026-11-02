# Sportscast Studio — live scoreboard and OBS overlay

This is the same NFL Scoreboard Studio with an additional **Connect to OBS** tab. The controller and OBS-only page stay synchronized via a small Python web server.

## Run it on your Mac (works without publishing)

1. Unzip the project and keep the folder together.
2. Double-click **Run Sportscast.command** (Mac may request permission to open it), or open Terminal in the unzipped folder and run `python3 app.py`.
3. The server prints and opens a private **Controller** link, for example `http://127.0.0.1:8765/control?key=...`.
4. Open **Connect to OBS** in the controller and copy the OBS overlay link.
5. In OBS select **Sources → + → Browser**. Paste the link; set **Width 1280** and **Height 220**. Position the browser source where you want the scoreboard to be.
6. Keep the Terminal and controller open while streaming. Your OBS scoreboard will mirror changes in the controller, usually within a fraction of a second.

**OBS-only local URL:** `http://127.0.0.1:8765/obs` (works while the Python server is running). This URL shows only the transparent scoreboard, not buttons or panels. `localhost`/`127.0.0.1` works only on the same Mac that runs the server.

## Deploy on the public internet

The included `render.yaml` is a starter for a **Render Web Service**. A public hosted app needs a Render account and your code uploaded to a connected Git repository. The server is Python standard-library only, no packages to install.

1. Put the files in a repository you control.
2. On Render, create a new **Web Service** linked to that repository, or use the supplied Blueprint. Use `python3 app.py` as the start command. Set `HOST=0.0.0.0`, `PORT` is normally supplied by Render.
3. In the service environment variables set **`SPORTSCAST_CONTROL_KEY`** to a strong private code you generate (use 24+ unpredictable characters). Never commit this code to a repository.
4. Once deployed, Render provides a genuine `https://<your-service>.onrender.com` URL. Open that URL and enter your controller code. The OBS URL is the same host plus `/obs`.
5. To use **sportscast.com**, you must own and control that domain, then attach it to Render under **Custom Domains** and update DNS. The name shown inside the app is not a domain registration.

**Important for reliability:** The included relay uses one server process and stores scoreboard state in memory. Restarting the host resets it, and platforms that sleep idle instances may interrupt streams. Choose an always-on host for long broadcasts. Do not scale to multiple independent server instances unless you add shared state storage. Never disclose your private controller key on stream; the OBS-only link is safe to share.
