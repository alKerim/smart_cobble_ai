# Backend API

This folder is reserved for the API that will run on your Hetzner server.

## Responsibility

- Receive commands from the public frontend
- Store the latest command per device
- Return the latest command to the Pico
- Optionally track device heartbeats and online status

## Suggested Minimal API Shape

- `POST /api/devices/:deviceId/commands`
- `GET /api/devices/:deviceId/commands/latest`
- `POST /api/devices/:deviceId/heartbeat`
- `GET /api/devices/:deviceId/status`

## Suggested Minimal Data Model

- device
- latest command
- last seen timestamp
- optional ownership/access metadata

## Deployment Target

- Hetzner server
- behind Nginx or Caddy
- exposed as `https://api.example.com`
