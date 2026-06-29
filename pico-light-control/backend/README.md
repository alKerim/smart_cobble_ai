# Backend API

This folder now contains the minimal backend for the public light-control flow.

## Stack

- Python standard library only
- `sqlite3` for storage
- `http.server` for the API

No third-party packages are required for the first deployment.

## Responsibility

- Receive commands from the public frontend
- Store the latest command per device
- Return the latest command to the Pico
- Track device heartbeats and online status

## API Shape

- `POST /api/devices/:deviceId/commands`
- `GET /api/devices/:deviceId/commands/latest`
- `POST /api/devices/:deviceId/heartbeat`
- `GET /api/devices/:deviceId/status`

## Authentication Model

- No authentication for the prototype
- One frontend controls one device
- One Pico polls one public backend

## Environment Variables

- `HOST`
- `PORT`
- `API_BASE_URL`
- `DATABASE_PATH`
- `ALLOWED_ORIGIN`

## Run Locally

```bash
cd pico-light-control/backend
python3 server.py
```

## Suggested Hetzner Layout

- app code: `/opt/smart-cobble-ai/backend`
- database: `/opt/smart-cobble-ai/shared/data.sqlite`
- env file: `/etc/smart-cobble-ai/backend.env`
- local port: `127.0.0.1:8788`
- public host: `https://smartcobble-api.example.com`

## systemd Example

```ini
[Unit]
Description=Smart Cobble backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=smartcobble
Group=smartcobble
WorkingDirectory=/opt/smart-cobble-ai/backend
EnvironmentFile=/etc/smart-cobble-ai/backend.env
ExecStart=/usr/bin/python3 server.py
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```
