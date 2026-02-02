# 🛡️ VPN Shop Bot (Aiogram 3 + Marzban)

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/Aiogram-3.x-blue?logo=telegram)
![Marzban](https://img.shields.io/badge/Marzban-Integration-black)
![License](https://img.shields.io/badge/License-MIT-green)

A Telegram bot for automated VPN access sales and management. Fully integrated with the **Marzban** panel.
The bot implements a **"Trusted Shop"** concept: instant delivery immediately after receipt submission, with post-moderation by the administrator.

## ✨ Key Features

### ⚡ Instant Delivery (Trusted Flow)
* **Free Trial:** One-click access. The bot automatically creates a user in Marzban.
* **Purchase:** Upon sending a payment screenshot, the bot **instantly** extends the subscription and delivers the keys. The admin verifies the receipt later.

### 🔐 Smart Authorization
* Seamless integration with Telegram.
* Uses **Telegram Username** as the Marzban login.
* Falls back to **Telegram ID** (`user_123456`) if no username is set.
* Prevents duplicate accounts.

### 👤 User Dashboard
* View subscription status and expiration date.
* Retrieve access keys in two formats:
    * 🔗 **Subscription Link** (for auto-updates).
    * 🔑 **VLESS** (raw key for quick connection).

### 🛠 Admin Interface
* Payment notifications sent directly to the admin's DM.
* Inline buttons right under the receipt photo:
    * ✅ **Approve:** Logs success in the database.
    * ❌ **Reject:** Marks transaction as failed (access can be revoked manually via panel).

## 🚀 Installation

The project is Docker-ready.

### 1. Clone
```bash
git clone [https://github.com/YOUR_USERNAME/REPO_NAME.git](https://github.com/YOUR_USERNAME/REPO_NAME.git)
cd vpn-shop-bot
2. Configuration
Create .env file from example:

Bash

cp example.env .env
nano .env
Fill in the details:

BOT_TOKEN: From @BotFather.

ADMIN_ID: Your Telegram numeric ID.

MARZBAN_URL: Panel URL (e.g., https://vpn.example.com:8000).

MARZBAN_USERNAME / PASSWORD: Panel admin credentials.

3. Deploy
Bash

docker-compose up -d --build
🗄 Project Structure
app/bot: Bot logic (handlers, keyboards).

app/core: Database & Models (SQLAlchemy).

app/services: Marzban API & Payment service.

data/: SQLite storage.

Developed for private VPN administration.
