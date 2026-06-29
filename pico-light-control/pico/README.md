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
- device token

## Suggested Polling Model

- Poll every `0.5` to `1.0` seconds
- Request latest command for one device
- Apply command only if it is newer than the last applied command
