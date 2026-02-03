
🤖 VPN Shop Bot (Marzban Integration)
Telegram bot for automated VPN subscription sales based on Marzban panel. Handles user creation, VLESS (Reality) key issuance, payment verification, and plan management.

✨ Features
Auto-Provisioning: Creates Marzban users via API instantly.

Smart Config: Auto-detects Inbound Tag and protocol settings.

Plans: Flexible pricing (Trial, Monthly, Yearly).

Payments: User sends receipt -> Admin approves -> Access granted.

Admin Panel: Manage users, stats, and broadcasts via Telegram.

🛠 Setup
1. Clone
Bash

git clone [https://github.com/FrenkyCastilla/Marzh-repo-bot.git](https://github.com/FrenkyCastilla/Marzh-repo-bot.git)
cd Marzh-repo-bot
2. Configuration (.env)
Create .env file:

Ini, TOML

BOT_TOKEN=your_token
ADMIN_ID=your_id
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db

MARZBAN_HOST=https://your-domain/dashboard
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=password

# Fallback tag (bot auto-detects usually)
INBOUND_TAG=VLESS TCP REALITY
# Leave empty for auto-config
VLESS_FLOW=

PAYMENT_INFO=Transfer details here
3. Run
Bash

docker compose up -d --build
4. Initialize Plans
Bash

docker compose cp seed.py bot:/app/seed.py && docker compose exec bot python seed.py
