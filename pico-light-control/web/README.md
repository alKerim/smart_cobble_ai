# Web Frontend

This folder is reserved for the public control UI.

## Responsibility

- Open from a QR code
- Resolve the device from the URL
- Show a minimal control interface
- Send commands to the backend API

## Planned Route Shape

- `/device/:deviceId`

## Deployment Target

- Vercel
- static frontend if possible
- custom domain such as `https://lights.example.com`

## Configuration Needs

- public API base URL
- optional admin key for private setup tools only

## Vercel Note

When deployed, set the Vercel project root to this `web/` folder.
