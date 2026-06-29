# Web Frontend

This folder now contains a minimal static frontend intended for GitHub Pages.

## Responsibility

- Open from a QR code
- Resolve the device from the URL
- Show a minimal control interface
- Send commands to the backend API

## Route Shape

- `/device/<device_id>`

GitHub Pages does not natively support arbitrary server-side routes, so this folder includes a `404.html` fallback that sends direct deep links back into the client-side app.

## Deployment Target

- GitHub Pages
- static HTML, CSS, and JavaScript
- no build step required

## Configuration Needs

- `apiBaseUrl` in `config.js`

Edit [config.js](/Users/kerimanater/MyMacData/UNI/Master/HCI/Semester%203/DW2/pico-light-control/web/config.js) to point the static frontend at the correct backend URL.

## GitHub Pages Setup

1. Push this repository to GitHub.
2. In the repository, go to `Settings` -> `Pages`.
3. Under `Build and deployment`, set `Source` to `GitHub Actions`.
4. The workflow in `.github/workflows/deploy-pages.yml` will publish this folder.

## URL Shapes

If you publish as a project site, the base URL will look like:

- `https://USERNAME.github.io/REPOSITORY_NAME/`

If you publish as a user site repo named exactly `USERNAME.github.io`, the base URL will look like:

- `https://USERNAME.github.io/`
