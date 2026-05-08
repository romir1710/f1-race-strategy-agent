# 🏎️ F1 Race Strategy Agent

> An AI-powered F1 race engineer agent built with LangChain, Google Gemini, and LangSmith. Analyses live race situations and recommends pit strategies, just like a real race engineer on the radio.


---

## ⭐ Features

- **4 Custom Agent Tools** — race situation snapshot, tyre degradation assessment, pit window calculator, and live DuckDuckGo F1 data search
- **Google Gemini 2.5 Flash** — fast, accurate LLM reasoning (no OpenAI dependency)
- **ReAct Agent** — step-by-step reasoning with tool calls via LangChain Hub prompt
- **LangSmith Tracing** — full observability: every agent thought, tool call, and token logged
- **Telegram Bot** — public bot powered by python-telegram-bot v20 (async)
- **Rate Limiting** — 10 strategy calls per user per calendar day; resets automatically at midnight
- **Terminal Mode** — run and test fully without Telegram via `python agent.py`
- **Bono Personality** — calm, data-driven F1 race engineer persona baked into every response

---

## 🛠️ Prerequisites

Before you start, you need:

1. **Python 3.12** — [Download here](https://www.python.org/downloads/)
2. **Google AI Studio API Key** — [Get it free here](https://aistudio.google.com/app/apikey) (Gemini access)
3. **Telegram Bot Token** — from [@BotFather](https://t.me/BotFather) on Telegram (see below)
4. **LangSmith API Key** — [Sign up free at smith.langchain.com](https://smith.langchain.com)

---

## 🚀 Setup

### Step 1: Clone the repository

```bash
git clone https://github.com/romir1710/f1-race-strategy-agent.git
cd f1-race-strategy-agent
```

### Step 2: Create your `.env` file

```bash
cp .env.example .env
```

Now open `.env` in any text editor and add your own API keys:

```
GOOGLE_API_KEY=your-google-ai-studio-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-from-botfather
LANGSMITH_API_KEY=your-langsmith-key-here
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=f1-race-strategy-agent
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the agent

See the **Running** sections below.

---

## 🤖 Getting a Telegram Bot Token from BotFather

1. Open Telegram and search for **@BotFather**
2. Send the command `/newbot`
3. BotFather will ask for a name (e.g. `F1 Strategy Agent`) and a username (e.g. `f1strategybot`)
4. Once created, BotFather will send you a token that looks like: `1234567890:ABCdef...`
5. Copy that token into your `.env` file as `TELEGRAM_BOT_TOKEN`

---

## 🖥️ Running in Terminal Mode

Test the agent without Telegram — pure command-line Q&A:

```bash
python agent.py
```

You will see:
```
🏎️  F1 Race Strategy Agent — Terminal Mode
Type your race situation and press Enter. Type 'quit' to exit.

You: Should I pit now? I'm on lap 28 of 53 on mediums aged 22 laps.

Adrian: [agent reasoning and recommendation here]
```

Type `quit` to exit.

---

## 📱 Running the Telegram Bot

Start the bot so it is live and responding to Telegram messages:

```bash
python bot.py
```

The bot will run indefinitely (until you press `Ctrl+C`). For 24/7 deployment on a server, use a process manager like `screen`, `tmux`, or `systemd`:

```bash
# Using screen (recommended for beginners)
screen -S f1bot
python bot.py
# Press Ctrl+A then D to detach, bot keeps running
```

Once running, go to your bot on Telegram and:
- Send `/start` to see the welcome message
- Send `/help` to see example questions
- Ask any race strategy question!

**Rate limit:** Each user gets 10 strategy calls per day. Resets at midnight.

---

## 🔍 Viewing Traces in LangSmith

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Sign in with your account
3. Click on **Projects** in the left sidebar
4. Select the project named **`f1-race-strategy-agent`**
5. You will see every agent run: thoughts, tool calls, token counts, latency, and the final answer

LangSmith tracing is enabled automatically when `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set in your `.env`.

---

## 📁 Project Structure

```
f1-race-strategy-agent/
├── agent.py          # Core LangChain ReAct agent logic
├── tools.py          # 4 @tool decorated functions
├── bot.py            # Telegram bot wrapper (async, python-telegram-bot v20)
├── requirements.txt  # All Python dependencies
├── .env.example      # Template for API keys (copy to .env)
├── .gitignore        # Prevents .env from being committed
└── README.md         # This file
```

---

## 🛡️ Security

- `.env` file is listed in `.gitignore` and will not be pushed
- The `.env.example` file contains only placeholder values 
- API keys are always to be loaded from the environment

---

## 📚 Tech Stack

| Component | Library / Service |
|---|---|
| Language | Python 3.12 |
| LLM | Google Gemini 2.5 Flash |
| Agent Framework | LangChain (ReAct) |
| Gemini Integration | langchain-google-genai |
| Web Search Tool | DuckDuckGoSearchRun (langchain-community) |
| Observability | LangSmith |
| Telegram Bot | python-telegram-bot 20.7 |
| Config | python-dotenv |

---

*Built with ❤️ for F1 fans and AI engineers.*
