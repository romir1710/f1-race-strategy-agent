# 🏎️ F1 Race Strategy Agent

An AI-powered F1 race engineer agent built with LangChain, Google Gemini, and LangSmith. Analyses live race situations and recommends pit strategies, just like a real race engineer on the radio.

---

## ⭐ Features

- **5 Custom Agent Tools** — race situation snapshot, tyre degradation assessment, pit window calculator, live DuckDuckGo F1 data search, and **tire telemetry status** (`check_tire_status`)
- **Tire Telemetry Engine** — dummy telemetry service with realistic pressure, temperature, and life % metrics using revolution-based lifecycle tracking
- **Exponential Degradation Prediction** — estimates next-bank impact and remaining tire laps using an exponential degradation curve
- **Terminal Progress Bar** — colored ASCII bar: 🟩 consumed / 🟦 remaining / 🟧 next-bank prediction
- **Google Gemini 2.5 Flash** — fast, accurate LLM reasoning (no OpenAI dependency)
- **ReAct Agent** — step-by-step reasoning with tool calls via LangChain Hub prompt
- **LangSmith Tracing** — full observability: every agent thought, tool call, and token logged
- **Telegram Bot** — public bot powered by python-telegram-bot v20 (async)
- **Rate Limiting** — 10 strategy calls per user per calendar day; resets automatically at midnight
- **Terminal Mode** — run and test fully without Telegram via `python agent.py`
- **Adrian Personality** — calm, data-driven F1 race engineer persona baked into every response

---

## 🔧 How It Works

### Tire Status Tool (`check_tire_status`)

1. Agent receives a tire status query → calls `check_tire_status(compound, lap_age, circuit)`
2. **Dummy telemetry service** (`tire_service.py`) generates realistic telemetry data:
   - Pressure (PSI), temperature (°C)
   - Life % = `current_revolutions / total_lifecycle_revolutions` (factoring in turns per lap at the given circuit)
3. **Prediction engine** uses an exponential degradation curve to estimate:
   - Next-bank impact (additional degradation %)
   - Life remaining after next banking event
   - Estimated tire laps left
   - Risk level (LOW / MEDIUM / HIGH)
4. **Progress bar** renders to terminal with colour-coded zones:
   - 🟩 Green — consumed life
   - ⬜ Grey — remaining life
   - 🟧 Orange — next-bank prediction impact

### Sample Terminal Output

<pre>
🏎️  F1 Race Strategy Agent — Terminal Mode
Type your race situation and press Enter. Type 'quit' to exit.

<b>You:</b> What is our current situation?

<b>Adrian:</b> We are on lap 28 of 53, in P3. We are on medium tyres, 22 laps old.
Gap to Verstappen in P2 is +4.2s. Sainz in P4 is 1.8s behind and closing.
Weather is dry, track temperature 38 degrees C.

<b>You:</b> What is the status of my 22 lap old mediums, here in silverstone?

<b>Adrian:</b>
  🏎️  TIRE STATUS — Medium | Lap Age: 22
  ─────────────────────────────────────────────
  Pressure:       20.4 PSI
  Temperature:    111.1°C
  Life Used:      <b>89.5%</b>
  Revolutions:    64,801 / 72,393

  0%      25%      50%      75%     100%    125%
  |--------|--------|--------|--------|--------|
  <span style="background-color:#2d7a2d;color:#fff;padding:0 2px">█████████████████████████</span><span style="background-color:#555;color:#ccc;padding:0 2px">█████████████</span><span style="background-color:#c87000;color:#fff;padding:0 2px">█</span>|

  <span style="color:#4caf50">■ consumed</span>    <span style="color:#9e9e9e">■ remaining</span>    <span style="color:#ff9800">■ next bank impact</span>

  🔮 <b>PREDICTION — Next Bank Impact:</b>
  Additional degradation:  <span style="color:#ff9800"><b>+0.08%</b></span>
  Life after next bank:    89.6%
  Est. tire laps left:     <b>2.3 laps</b>
  Risk level:              <span style="color:#ff5722"><b>HIGH</b></span>

Your 22-lap old mediums at Silverstone show 89.5% life used. Pressure is 20.4 PSI,
temperature 111.1°C. Risk is HIGH. You have approximately 2.3 laps remaining.

<b>You:</b> Is the pit window open? Can i box and stay ahead of sainz?

<b>Adrian:</b> The pit window is tight. You are 25.2 seconds short of a safe margin
to Sainz. Risk of undercut is high.
</pre>

---

## 🛠️ Prerequisites

Before you start, you need:

1. **Python 3.12** — [Download here](https://www.python.org/downloads/)
2. **Google AI Studio API Key** — [Get here](https://aistudio.google.com/app/apikey) (Gemini access)
3. **Telegram Bot Token** — from [@BotFather](https://t.me/BotFather) on Telegram (see below)
4. **LangSmith API Key** — [Sign up at smith.langchain.com](https://smith.langchain.com)

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

You will see (incl. sample prompt and response):
```
🏎️  F1 Race Strategy Agent — Terminal Mode
Type your race situation and press Enter. Type 'quit' to exit.

You: I am on 17 lap old softs, verstappen behind, closing in on me, despite being on similarly old tyres, this is lap 17/54, do i box?

Adrian: Your soft tyres are critically degraded. They are 17 laps old, past their cliff at 15 laps. There is a high risk of blowout or 2+ seconds lap time loss. Box this lap or risk an undercut to Verstappen who shall most likely also be coming in soon.
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
├── tools.py          # 5 @tool decorated functions (incl. check_tire_status)
├── tire_service.py   # Dummy telemetry service + exponential degradation engine
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
| Tire Telemetry | Custom dummy service (`tire_service.py`) |
| Observability | LangSmith |
| Telegram Bot | python-telegram-bot 20.7 |
| Config | python-dotenv |

---

*Built with ❤️ for F1 fans and AI engineers.*
