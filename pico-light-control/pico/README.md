# Pico App

This folder will contain the MicroPython code that runs on the Pico W.

## Responsibility

- Connect to local Wi-Fi
- Poll the backend for commands
- Apply LED modes and brightness
- Optionally send heartbeat/status updates

## Expected Files Later

- `main.py`: entry point on the Pico
- `secrets.py`: local credentials copied from `secrets.example.py`

## Planned Runtime Inputs

- Wi-Fi SSID
- Wi-Fi password
- backend base URL
- device ID

## Current Model

- Poll every `0.5` to `1.0` seconds
- Request latest command for one device
- Apply command only if it is newer than the last applied command
- Send heartbeat updates periodically

## Setup

1. Copy `secrets.example.py` to `secrets.py`.
2. Fill in your real Wi-Fi credentials.
3. Keep `BACKEND_BASE_URL` pointed at the live backend.
4. Copy both files to the Pico.

## Runtime Behavior

- `solid` and `off` are applied immediately after polling
- `siri` keeps animating locally between polls
- Wi-Fi reconnect is handled automatically
