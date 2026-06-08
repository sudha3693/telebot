# 🤖 Telegram Bot & FastAPI Integration

A professional, modular, and scalable boilerplate for building Telegram Bots integrated with a FastAPI backend. This project supports both **Long Polling** and **Webhooks**, providing a robust foundation for AI bots, notification systems, or complex automation tools.

---

## 🚀 Overview

This project bridges the gap between the **FastAPI** web framework and the **python-telegram-bot** library. It is designed with a clean architecture (Services, Models, Routes) to ensure your code remains maintainable as your bot grows.

### Key Capabilities:
- **Dual Mode**: Switch between `polling` (for local development) and `webhook` (for production) via `.env`.
- **Real-time Logging**: Every message sent to the bot is detailed and logged in your terminal.
- **Outbound API**: Dedicated REST endpoints to trigger bot messages from other services.
- **Database Ready**: Pre-configured with SQLAlchemy and SQLite.

---

## 📂 Project Structure

```text
├── src/
│   ├── routes/          # FastAPI APIRouter definitions
│   ├── models/          # SQLAlchemy Database Models
│   ├── schemas/         # Pydantic data validation schemas
│   ├── services/        # Core logic (Telegram Bot Service)
│   ├── utils/           # Shared utility functions
│   ├── helper/          # Reusable helper classes
│   ├── database.py      # Database engine and session setup
│   └── main.py          # FastAPI initialization & lifecycle hooks
├── static/              # Serve images, CSS, or JS files
├── .env                 # Environment secrets (Token, Mode, DB URL)
├── requirements.txt     # Python package dependencies
└── README.md            # Comprehensive documentation
```

---

## 🛠️ How It Works

### 1. Telegram Service (`src/services/telegram_service.py`)
This is the heart of the bot. It manages the `python-telegram-bot` Application instance.
- **Initialization**: Automatically starts on FastAPI startup.
- **Handlers**: Contains `CommandHandler` (like `/start`) and `MessageHandler` (for text processing).
- **Messaging**: Provides an `async` method to send messages to any `chat_id`.

### 2. Lifecyle Hooks
In `main.py`, we use FastAPI startup/shutdown events:
- **Startup**: The `telegram_service` initializes the bot and starts the Polling updater if configured.
- **Shutdown**: Gracefully stops the bot and closes database connections.

### 3. Polling vs. Webhook
- **Polling**: Your server "polls" Telegram for new messages. No public URL is needed.
- **Webhook**: Telegram "pushes" messages to your server's `/webhook` endpoint. Requires a public HTTPS URL (like ngrok).

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- **Python 3.10+** installed.
- **Telegram Bot Token**: Get one from [@BotFather](https://t.me/BotFather) on Telegram.

### 2. Installation
```bash
# 1. Navigate to project directory
cd "Telegram Bot"

# 2. (Optional) Create a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Rename or create a `.env` file in the root:
```env
TELEGRAM_BOT_TOKEN=your_7212411...token_here
DATABASE_URL=sqlite:///./sql_app.db
TELEGRAM_MODE=polling  # Set to 'webhook' for production
API_SECRET_KEY=generate_a_strong_secret_here
API_BASE_URL=http://10.138.25.47:8001
BACKEND_URL=http://10.138.25.47:8001
FRONTEND_URL=http://10.138.25.47:8001
WEBHOOK_URL=http://10.138.25.47:8001/webhook
WS_URL=ws://10.138.25.47:8001/ws
WEB_DASHBOARD_V1_URL=http://10.138.25.47:8001/dashboard
WEB_DASHBOARD_V2_URL=http://10.138.25.47:8001/dashboard-v2
CORS_ALLOW_ORIGINS=http://10.138.25.47:8001
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8001
```

### 🔒 API Security
The `/send-message` endpoint is protected. To call it, you must include the `X-API-Key` header.
- **Header**: `X-API-Key: your_secret_key_here`

---

## 🏃 Running the Application

Start the server with auto-reload enabled for development:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```
The server will start at `http://10.138.25.47:8001` when your server IP is reachable on the network.

### Testing the Bot:
1. Open Telegram and find your bot.
2. Send `/start`.
3. Send any text message.
4. **Check your Terminal**: You will see a detailed log of your message and user info!

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root message to verify the API is alive. |
| `GET` | `/health` | Returns `{"status": "healthy"}`. |
| `POST` | `/webhook` | Receives updates from Telegram (Webhook Mode). |
| `POST` | `/send-message` | Send a message to a user programmatically. |

**Example usage for `/send-message`**:
```bash
curl -X POST "http://10.138.25.47:8001/send-message?chat_id=123456&text=Hello+from+FastAPI" \
     -H "X-API-Key: generate_a_strong_secret_here"
```

---

## 🌐 Webhook Deployment (ngrok)

To use Webhook mode locally:
1. Install [ngrok](https://ngrok.com/).
2. Run `ngrok http 8000`.
3. Copy the `https` URL provided by ngrok.
4. Update Telegram:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=http://10.138.25.47:8001/webhook"
   ```
5. Set `TELEGRAM_MODE=webhook` and `WEBHOOK_URL=http://10.138.25.47:8001/webhook` in your `.env`.

## URL Configuration Summary

- Browser dashboards load centralized runtime config from `/config.js`.
- V1 dashboard uses `API_BASE_URL` for login, upload, user management, and dashboard APIs.
- V2 dashboard uses `API_BASE_URL` for stats, search, upload, access requests, and logs.
- Telegram dashboard buttons use `WEB_DASHBOARD_V1_URL` and `WEB_DASHBOARD_V2_URL`.
- Telegram webhook mode uses `WEBHOOK_URL`.
- `WS_URL` is reserved for future WebSocket support; no app WebSocket endpoint exists today.

## External Access Checks

- Ensure the app is started with `--host 0.0.0.0 --port 8001`.
- Ensure the server firewall allows inbound TCP `8001`.
- Ensure the host machine/network exposes `10.138.25.47:8001`.
- If using a reverse proxy, update proxy target and forwarded headers.
- If URLs still fail externally, verify local router/VPN/network policy is not blocking the private IP.

---

## 📜 License
This project is licensed under the MIT License.
