# Pico Light Control Monorepo

This subproject is the minimal foundation for controlling a Pico-powered light device from a public website.

## Goal

- `pico/`: the MicroPython script that runs on the Pico W
- `backend/`: the API running on your Hetzner server
- `web/`: the public frontend, intended for GitHub Pages hosting

## Planned Flow

1. A QR code opens a public page like `https://lights.example.com/device/cobble-001`.
2. The web frontend sends a command to the backend API.
3. The Pico polls the backend for the latest command.
4. The Pico updates the LEDs.

## Architecture

```text
            +----------------------+
            |  User scans QR code  |
            +----------+-----------+
                       |
                       v
          +---------------------------+
          | Public frontend on        |
          | GitHub Pages              |
          | /device/<device_id>       |
          +-------------+-------------+
                        |
                        | HTTPS
                        v
          +---------------------------+
          | Backend on Hetzner        |
          | API + device registry     |
          | command storage + status  |
          +-------------+-------------+
                        ^
                        |
                        | HTTPS polling
                        |
          +-------------+-------------+
          | Pico W on local Wi-Fi     |
          | polls for latest command  |
          +-------------+-------------+
                        |
                        v
                 +-------------+
                 |  LED strip  |
                 +-------------+
```

## Proposed Repository Layout

```text
pico-light-control/
  README.md
  .gitignore
  pico/
    README.md
    secrets.example.py
  backend/
    README.md
    .env.example
  web/
    README.md
    .env.example
```

## Secrets And Placeholders

These values are expected later and are intentionally not filled in yet:

- `PICO_WIFI_SSID`
- `PICO_WIFI_PASSWORD`
- `PICO_DEVICE_ID`
- `PICO_DEVICE_TOKEN`
- `BACKEND_BASE_URL`
- `API_ADMIN_SECRET`
- `PUBLIC_API_BASE_URL`
- `VERCEL_PROJECT_NAME`
- `VERCEL_DEPLOY_HOOK_URL`

## Notes

- The frontend stays static so GitHub Pages deployment is easy.
- The backend should be the only component the Pico talks to over the internet.
- The Pico should never be exposed directly to the public internet.
