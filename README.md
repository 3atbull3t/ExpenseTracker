# Telegram Expense Tracker Bot

A Telegram bot that helps track expenses, set budgets, and monitor spending habits. The bot uses Google Sheets as a backend database for storing expense data and budget information.

## Features

- 📝 Easy expense tracking with categories
- 💰 Set and monitor budget limits per category
- 📊 Daily expense summaries
- 🔍 View expenses by different time periods
- 📈 Track spending patterns
- 🔔 Daily reminders and budget alerts

## Setup Instructions

1. **Create a Telegram Bot**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot using `/newbot` command
   - Save the API token provided

2. **Set up Google Sheets API**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable Google Sheets API
   - Create credentials (OAuth 2.0 Client ID)
   - Download the credentials and save as `credentials.json`
   - Create a new Google Sheet and copy its ID from the URL
   

3. **Environment Setup**
   - Create a `.env` file with the following variables:
     ```
     TELEGRAM_TOKEN=your_telegram_bot_token
     SPREADSHEET_ID=your_google_sheet_id
     ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Bot**
   ```bash
   python bot.py
   ```

## Bot Commands

- `/start` - Start the bot and see available commands
- `/add <amount> <category>` - Add a new expense
- `/view` - View your expenses
- `/budget <category> <amount>` - Set budget for a category
- `/summary` - Get daily expense summary
- `/help` - Show help message

## Categories

- 🍔 Food
- 🚗 Transport
- 🛍️ Shopping
- 🎮 Entertainment
- 📝 Bills
- 📦 Other

## Contributing

Feel free to submit issues and enhancement requests! 