# Telegram VPN Shop Bot (Marzban Integration)

A production-ready Telegram bot for selling VPN access using the Marzban backend.

## Features
- **Automated User Creation**: Optimistic UI grants 24h access immediately upon receipt submission.
- **Admin Approval**: Manual verification of payments via Telegram with one-click approval/rejection.
- **Web Admin Panel**: Manage users, plans, and servers via a web interface (SQLAdmin).
- **Subscription Management**: Background tasks automatically disable expired accounts.
- **Marzban Integration**: Seamlessly connects to Marzban API for user management.

## Tech Stack
- **Python 3.11+**
- **Aiogram 3.x** (Telegram Bot)
- **FastAPI** (Web Server & Admin UI)
- **SQLAlchemy + SQLite** (Database)
- **SQLAdmin** (Admin Interface)
- **Docker** (Deployment)

## Setup
1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in your credentials:
   - `BOT_TOKEN`: Your Telegram Bot token.
   - `ADMIN_ID`: Your Telegram ID (get it from @userinfobot).
   - `MARZBAN_HOST`: URL of your Marzban panel.
   - `MARZBAN_USERNAME/PASSWORD`: Admin credentials for Marzban.
3. Run with Docker:
   ```bash
   docker-compose up -d
   ```

## Admin Panel
Access the web admin panel at `http://your-server-ip:8000/admin`.
From there, you can add **Plans** (tariffs) which will be displayed in the bot.

## Project Structure
- `app/core`: Configuration and Database models.
- `app/services`: Marzban API and Payment logic.
- `app/bot`: Telegram bot handlers and keyboards.
- `app/web`: Admin panel configuration.
- `main.py`: Application entry point.
