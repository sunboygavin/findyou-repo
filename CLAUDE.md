# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Findyou is an AI digital employee (数字员工) deployment and maintenance platform. It's a marketing/demo site for a SaaS product that lets companies deploy AI-powered digital workers for accounting, data analysis, security, content creation, HR, and sales functions. The UI follows a Notion-inspired design system.

## Tech Stack

- **Backend:** Python 3.12 + Flask 3.0+
- **Frontend:** Vanilla HTML/CSS/JS (no build step, no frameworks)
- **Auth:** Session-based with hardcoded credentials

## Running the App

```bash
./start.sh    # Creates venv, installs deps, starts on http://0.0.0.0:5001
./stop.sh     # Kills the running process
```

Dev credentials: `admin` / `findyou2026` or `demo` / `demo123`

## Architecture

**Backend (`app.py`):** Single Flask file with routes:
- `GET /` — serves `index.html` (marketing page) or redirects to dashboard if logged in
- `POST /api/login` — JSON login, sets session
- `GET /logout` — clears session
- `POST /api/contact` — receives contact form (logs only, no persistence)

**Frontend pages:**
- `index.html` — marketing landing page (served directly, not via templates)
- `templates/index.html` — authenticated dashboard
- `templates/login.html` — login form page

**Key frontend features:** Chat modals for 6 AI employee personas, soul/personality customization sliders, pricing calculator (SaaS vs private deployment), contact form.

## Conventions

- API endpoints live under `/api/` and use JSON request/response
- CSS uses custom properties for theming (defined at top of each HTML file)
- The app is Chinese-language (UI text, business docs in `docs/`)
- Process management uses PID files (`app.pid`) and shell scripts
- Business/planning documentation lives in `docs/`
