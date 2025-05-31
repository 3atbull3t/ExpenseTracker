import os
import logging
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google_sheets import GoogleSheetsManager
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import random

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Google Sheets manager
sheets_manager = GoogleSheetsManager()

# Store chat IDs for scheduled messages (optional, as we are now saving to Sheets)
# In a production environment, rely on the data from your persistent storage (Google Sheets)
# user_chat_ids = {}

# Predefined categories
CATEGORIES = {
    'food': '🍔 Food',
    'transport': '🚗 Transport',
    'shopping': '🛍️ Shopping',
    'entertainment': '🎮 Entertainment',
    'bills': '📝 Bills',
    'other': '📦 Other',
    'tithe': '🙏 Tithe/Offering'
}

# Bible Verses and Encouragement
TITHING_VERSES = [
    {"ref": "Malachi 3:10 (NIV)", "text": "Bring the whole tithe into the storehouse, that there may be food in my house. Test me in this,” says the Lord Almighty, “and see if I will not throw open the floodgates of heaven and pour out so much blessing that there will not be room enough to store it.", "emoji": "🪙"},
    {"ref": "Proverbs 3:9–10 (NIV)", "text": "Honor the Lord with your wealth, with the firstfruits of all your crops; then your barns will be filled to overflowing, and your vats will brim over with new wine.", "emoji": "🌾"},
    {"ref": "Luke 6:38 (NIV)", "text": "Give, and it will be given to you. A good measure, pressed down, shaken together and running over, will be poured into your lap. For with the measure you use, it will be measured to you.", "emoji": "🎁"},
    {"ref": "2 Corinthians 9:7–8 (NIV)", "text": "Each of you should give what you have decided in your heart to give, not reluctantly or under compulsion, for God loves a cheerful giver. And God is able to bless you abundantly, so that in all things at all times, having all that you need, you will abound in every good work.", "emoji": "💖"},
    {"ref": "Deuteronomy 16:17 (NIV)", "text": "Each of you must bring a gift in proportion to the way the Lord your God has blessed you.", "emoji": "💰"},
    {"ref": "Acts 20:35 (NIV)", "text": "In everything I did, I showed you that by this kind of hard work we must help the weak, remembering the words the Lord Jesus himself said: ‘It is more blessed to give than to receive.’", "emoji": "👐"},
]

OVERSPENDING_VERSES = [
    {"ref": "Matthew 6:19–21 (NIV)", "text": "Do not store up for yourselves treasures on earth, where moths and vermin destroy, and where thieves break in and steal. But store up for yourselves treasures in heaven... For where your treasure is, there your heart will be also.", "emoji": "📦"},
    {"ref": "Hebrews 13:5 (NIV)", "text": "Keep your lives free from the love of money and be content with what you have, because God has said, ‘Never will I leave you; never will I forsake you.’", "emoji": "💸"},
    {"ref": "1 Timothy 6:9–10 (NIV)", "text": "Those who want to get rich fall into temptation and a trap... For the love of money is a root of all kinds of evil.", "emoji": "⚠️"},
    {"ref": "Luke 12:15 (NIV)", "text": "Watch out! Be on your guard against all kinds of greed; life does not consist in an abundance of possessions.", "emoji": "⚖️"},
    {"ref": "Ecclesiastes 5:10 (NIV)", "text": "Whoever loves money never has enough; whoever loves wealth is never satisfied with their income. This too is meaningless.", "emoji": "🕳"},
    {"ref": "Proverbs 23:4–5 (NIV)", "text": "Do not wear yourself out to get rich; do not trust your own cleverness. Cast but a glance at riches, and they are gone…", "emoji": "💼"},
]

FOOD_MODERATION_VERSES = [
    {"ref": "Proverbs 25:16 (NIV)", "text": "If you find honey, eat just enough—too much of it, and you will vomit.", "emoji": "🧁"},
    {"ref": "Proverbs 23:20–21 (NIV)", "text": "Do not join those who drink too much wine or gorge themselves on meat, for drunkards and gluttons become poor, and drowsiness clothes them in rags.", "emoji": "🍷"},
    {"ref": "1 Corinthians 6:19–20 (NIV)", "text": "Do you not know that your bodies are temples of the Holy Spirit... Therefore honor God with your bodies.", "emoji": "🕊"},
    {"ref": "Philippians 4:5 (NIV)", "text": "Let your gentleness be evident to all. The Lord is near.", "emoji": "🧠"},
    {"ref": "Galatians 5:22–23 (NIV)", "text": "But the fruit of the Spirit is... self-control. Against such things there is no law.", "emoji": "🌿"},
    {"ref": "1 Corinthians 10:31 (NIV)", "text": "So whether you eat or drink or whatever you do, do it all for the glory of God.", "emoji": "🙏"},
]

DAILY_SUMMARY_VERSES = [
    {"ref": "Matthew 6:24 (NIV)", "text": "No one can serve two masters. Either you will hate the one and love the other, or you will be devoted to the one and despise the other. You cannot serve both God and money.", "emoji": "🔀", "explanation": "It's impossible to prioritize both God and worldly wealth simultaneously."},
    {"ref": "Ecclesiastes 5:10 (NIV)", "text": "Whoever loves money never has enough; whoever loves wealth is never satisfied with their income. This too is meaningless.", "emoji": "♻️", "explanation": "Chasing wealth alone leads to dissatisfaction and emptiness."},
    {"ref": "Proverbs 11:4 (NIV)", "text": "Wealth is worthless in the day of wrath, but righteousness delivers from death.", "emoji": "⚖️", "explanation": "Material possessions offer no protection in times of judgment; spiritual standing is what truly matters."},
    {"ref": "1 Timothy 6:7-10 (NIV)", "text": "For we brought nothing into the world, and we can take nothing out of it. But if we have food and clothing, we will be content with that. Those who want to get rich fall into temptation and a trap and into many foolish and harmful desires that plunge people into ruin and destruction. For the love of money is a root of all kinds of evil. Some people, eager for money, have wandered from the faith and pierced themselves with many griefs.", "emoji": "🪙", "explanation": "Excessive desire for money is dangerous and can lead to spiritual and emotional harm."},
    {"ref": "Luke 12:15 (NIV)", "text": "Watch out! Be on your guard against all kinds of greed; life does not consist in an abundance of possessions.", "emoji": "💼", "explanation": "True life is not measured by how much you own, but by something more valuable."},
    {"ref": "Mark 8:36 (NIV)", "text": "What good is it for someone to gain the whole world, yet forfeit their soul?", "emoji": "❓", "explanation": "No earthly gain is worth losing your eternal soul."},
    {"ref": "Hebrews 13:5 (NIV)", "text": "Keep your lives free from the love of money and be content with what you have, because God has said, ‘Never will I leave you; never will I forsake you.’", "emoji": "🕊", "explanation": "Be content with what you have and trust in God's provision rather than the pursuit of wealth."},
]

# Encouragement and Bible Verses (Add more as needed)
ENCOURAGEMENT_NOTES = [
    "You're doing great! Keep tracking those expenses.",
    "Every step counts towards your financial goals.",
    "Stay disciplined, and you'll see the results.",
    "Believe in yourself and your ability to manage your money.",
    "Small efforts today lead to big rewards tomorrow."
]

BIBLE_VERSES = [
    "'For where your treasure is, there your heart will be also.' - Matthew 6:21",
    "'The plans of the diligent lead surely to abundance, but everyone who is hasty comes only to poverty.' - Proverbs 21:5",
    "'Honor the Lord with your wealth and with the firstfruits of all your produce;' - Proverbs 3:9",
    "'The rich rules over the poor, and the borrower is the slave of the lender.' - Proverbs 22:7",
    "'Know well the prosperity of your flocks, and pay attention to your herds, for riches do not last forever; and does a crown endure to all generations?' - Proverbs 27:23-24"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    # Save user's chat ID
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    print(f"[start] User ID: {user_id}, Chat ID: {chat_id}")
    sheets_manager.save_user_chat_id(user_id, chat_id)

    print("[start] Calling sheets_manager.save_user_chat_id")

    welcome_message = (
        "👋 Welcome to your Expense Tracker Bot!\n\n"
        "\"<i>For the love of money is a root of all kinds of evil. Some people, eager for money, have wandered from the faith and pierced themselves with many griefs.</i>\"\n\n- <b>1 Timothy 6:10 (NIV)</b>\n\n"
        "Here are the available commands:\n"
        "/add &lt;amount&gt; &lt;category&gt; - Add an expense\n"
        "/view - View your expenses\n"
        "/budget - Set or view budget limits\n"
        "/set_daily &lt;amount&gt; - Set the total daily budget\n"
        "/summary - Get daily expense summary\n"
        "/reset_today [category] - Reset today's expenses (all or by category)\n"
        "/undo - Undo your latest expense entry\n"
        "/help - Show this help message\n\n"
        "Available categories:\n"
    )
    for category in CATEGORIES.values():
        welcome_message += f"- {category}\n"
    
    await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new expense."""
    try:
        # Parse command arguments
        if len(context.args) < 2:
            await update.message.reply_text(
                "Please provide amount and category.\n"
                "Example: /add 50 food"
            )
            return

        amount = float(context.args[0])
        category = context.args[1].lower()
        description = " ".join(context.args[2:]) if len(context.args) > 2 else ""

        if category not in CATEGORIES:
            await update.message.reply_text(
                f"Invalid category. Available categories:\n" + 
                "\n".join([f"- {cat}" for cat in CATEGORIES.values()])
            )
            return

        # Add expense to Google Sheets
        user_id = update.effective_user.id
        date = datetime.now().strftime("%Y-%m-%d")
        sheets_manager.add_expense(user_id, date, amount, category, description)

        await update.message.reply_text(
            f"✅ Expense added successfully!\n"
            f"Amount: ${amount:.2f}\n"
            f"Category: {CATEGORIES[category]}"
            + (f"\nDescription: {description}" if description else "")
        )

        # Check category budget and provide feedback
        user_id = update.effective_user.id # Redundant but good for clarity in this block
        category_budget = sheets_manager.get_budget(user_id, category)

        if category_budget is not None:
            today_summary = sheets_manager.get_daily_summary(user_id)
            spent_in_category_today = today_summary.get(category, 0)
            remaining_category_budget = category_budget - spent_in_category_today

            category_feedback_message = f"\n\n{CATEGORIES.get(category, category).capitalize()} Spending Today: ${spent_in_category_today:.2f} / ${category_budget:.2f}\n"
            if remaining_category_budget > 0:
                category_feedback_message += f"Remaining {CATEGORIES.get(category, category).capitalize()} Budget: ${remaining_category_budget:.2f}"
            elif remaining_category_budget < 0:
                category_feedback_message += f"⚠️ You are over your {CATEGORIES.get(category, category).capitalize()} budget by ${abs(remaining_category_budget):.2f}!"
            else:
                category_feedback_message += f"✅ You have spent exactly your {CATEGORIES.get(category, category).capitalize()} budget today."

            await update.message.reply_text(category_feedback_message)

        # Add relevant Bible verse based on category and budget status
        verse_message = "\n\n"

        if category == 'tithe':
            selected_verse = random.choice(TITHING_VERSES)
            verse_message += f"{selected_verse['emoji']} *{selected_verse['ref']}*\n{selected_verse['text']}"
            await update.message.reply_text(verse_message, parse_mode='Markdown')
        else:
            # Check category budget threshold for verses
            # Check category budget threshold
            category_budget = sheets_manager.get_budget(user_id, category)
            if category_budget is not None:
                 today_summary = sheets_manager.get_daily_summary(user_id)
                 spent_in_category_today = today_summary.get(category, 0)
                 if spent_in_category_today > category_budget * 0.8: # 80% threshold for category
                     if category in ['shopping', 'other']:
                         print("[add_expense] Category in ['shopping', 'other'] and budget exceeded.")
                         selected_verse = random.choice(OVERSPENDING_VERSES)
                         verse_message += f"{selected_verse['emoji']} *{selected_verse['ref']}*\n{selected_verse['text']}"
                         await update.message.reply_text(verse_message, parse_mode='Markdown')
                     elif category == 'food':
                        print("[add_expense] Food category budget exceeded, selecting food moderation verse.")
                        selected_verse = random.choice(FOOD_MODERATION_VERSES)
                        verse_message += f"{selected_verse['emoji']} *{selected_verse['ref']}*\n{selected_verse['text']}"
                        await update.message.reply_text(verse_message, parse_mode='Markdown')
                     # Add more category specific verse lists here if needed

    except ValueError:
        await update.message.reply_text("Please provide a valid amount.")

async def view_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View expenses with filtering options."""
    user_id = update.effective_user.id

    # Create inline keyboard for filtering
    keyboard = [
        [InlineKeyboardButton("Daily", callback_data="summary_daily")],
        [InlineKeyboardButton("Weekly", callback_data="summary_weekly")],
        [InlineKeyboardButton("Monthly", callback_data="summary_monthly")],
        [InlineKeyboardButton("Last Month", callback_data="summary_last_month")],
        [InlineKeyboardButton("Yearly", callback_data="summary_yearly")],
        [InlineKeyboardButton("All-Time", callback_data="summary_all_time")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Select a summary period:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data
    summary = {}
    title = ""

    if data == "summary_daily":
        summary = sheets_manager.get_daily_summary(user_id)
        title = "Daily Expense Summary"
    elif data == "summary_weekly":
        summary = sheets_manager.get_weekly_summary(user_id)
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        title = f"Weekly Expense Summary (Week of {start_of_week.strftime('%Y-%m-%d')})"
    elif data == "summary_monthly":
        summary = sheets_manager.get_monthly_summary(user_id)
        today = datetime.now().date()
        month_name = today.strftime('%B %Y')
        title = f"Monthly Expense Summary ({month_name})"
    elif data == "summary_last_month":
        summary = sheets_manager.get_last_month_summary(user_id)
        today = datetime.now().date()
        first_day_of_this_month = today.replace(day=1)
        last_day_of_last_month = first_day_of_this_month - timedelta(days=1)
        last_month_name = last_day_of_last_month.strftime('%B %Y')
        title = f"Last Month Expense Summary ({last_month_name})"
    elif data == "summary_yearly":
        summary = sheets_manager.get_yearly_summary(user_id)
        year = datetime.now().year
        title = f"Yearly Expense Summary ({year})"
    elif data == "summary_all_time":
        summary = sheets_manager.get_all_time_summary(user_id)
        title = "All-Time Expense Summary"

    if not summary:
        await query.edit_message_text(f"No expenses found for the selected period.")
        return

    message = f"📊 {title}:\n\n"

    if data == "summary_monthly":
        # Handle detailed monthly summary
        message += "📅 This Month:\n"
        if summary.get("this_month"):
            for category, amount in summary["this_month"].items():
                budget = sheets_manager.get_budget(user_id, category)
                if budget:
                    percentage = (amount / budget) * 100
                    status = "✅" if percentage <= budget else "⚠️"
                    message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f} / ${budget:.2f} ({percentage:.1f}%) {status}\n"
                else:
                    message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f}\n"
        else:
            message += "No expenses this month.\n"

        message += "\n🗓 Last 31 Days:\n"
        if summary.get("last_31_days"):
            for category, amount in summary["last_31_days"].items():
                budget = sheets_manager.get_budget(user_id, category)
                if budget:
                    percentage = (amount / budget) * 100
                    status = "✅" if percentage <= budget else "⚠️"
                    message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f} / ${budget:.2f} ({percentage:.1f}%) {status}\n"
                else:
                    message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f}\n"
        else:
            message += "No expenses in the last 31 days.\n"

    else:
        # Handle daily, weekly, and all-time summaries (existing format)
        for category, amount in summary.items():
            budget = sheets_manager.get_budget(user_id, category)
            if budget:
                percentage = (amount / budget) * 100
                status = "✅" if percentage <= budget else "⚠️"
                message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f} / ${budget:.2f} ({percentage:.1f}%) {status}\n"
            else:
                message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f}\n"

    await query.edit_message_text(message)

async def set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set budget limits for categories."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Please provide category and amount.\n"
            "Example: /budget food 200"
        )
        return

    category = context.args[0].lower()
    try:
        amount = float(context.args[1])
        if category not in CATEGORIES:
            await update.message.reply_text(
                f"Invalid category. Available categories:\n" + 
                "\n".join([f"- {cat}" for cat in CATEGORIES.values()])
            )
            return

        user_id = update.effective_user.id
        sheets_manager.set_budget(user_id, category, amount)
        await update.message.reply_text(
            f"✅ Budget set for {CATEGORIES[category]}: ${amount:.2f}"
        )

    except ValueError:
        await update.message.reply_text("Please provide a valid amount.")

async def get_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get daily expense summary and budget status."""
    user_id = update.effective_user.id
    daily_summary = sheets_manager.get_daily_summary(user_id)

    message = "📊 Daily Summary:\n\n"

    daily_budget = sheets_manager.get_budget(user_id, 'daily_total')
    if daily_budget is not None:
        total_spent_today = sum(daily_summary.values())
        remaining_budget = daily_budget - total_spent_today

        message += f"Today's Total Spending: ${total_spent_today:.2f} / ${daily_budget:.2f}\n"
        if remaining_budget > 0:
            message += f"Remaining Daily Budget: ${remaining_budget:.2f}\n\n"
        elif remaining_budget < 0:
            message += f"⚠️ You are over your daily budget by ${abs(remaining_budget):.2f}!\n\n"
        else:
            message += "✅ You have spent exactly your daily budget for today.\n\n"

    if not daily_summary:
        message += "No expenses recorded for today."
    else:
        message += "Breakdown by Category:\n"
        for category, amount in daily_summary.items():
            budget = sheets_manager.get_budget(user_id, category)
            if budget:
                percentage = (amount / budget) * 100
                status = "✅" if percentage <= budget else "⚠️"
                message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f} / ${budget:.2f} ({percentage:.1f}%) {status}\n"
            else:
                message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f}\n"

    await update.message.reply_text(message)

async def set_daily_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the total daily budget."""
    if len(context.args) < 1:
        await update.message.reply_text(
            "Please provide the daily budget amount.\n"
            "Example: /set_daily 100"
        )
        return

    try:
        amount = float(context.args[0])
        user_id = update.effective_user.id
        # We'll store the daily budget in the Budgets sheet under a special category, e.g., 'daily_total'
        sheets_manager.set_budget(user_id, 'daily_total', amount)
        await update.message.reply_text(
            f"✅ Daily budget set to: ${amount:.2f}"
        )

    except ValueError:
        await update.message.reply_text("Please provide a valid amount.")

async def reset_today_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets today's expenses for the user, optionally by category."""
    user_id = update.effective_user.id
    category = context.args[0].lower() if context.args else None

    if category and category not in CATEGORIES:
         await update.message.reply_text(
             f"Invalid category. Available categories:\n" + 
             "\n".join([f"- {cat}" for cat in CATEGORIES.values()])
         )
         return

    if sheets_manager.delete_expenses_today(user_id, category):
        if category:
            await update.message.reply_text(f"✅ Reset today's expenses for category '{CATEGORIES.get(category, category)}'.")
        else:
            await update.message.reply_text("✅ Reset all of today's expenses.")
    else:
        if category:
            await update.message.reply_text(f"No expenses found for category '{CATEGORIES.get(category, category)}' today to reset.")
        else:
            await update.message.reply_text("No expenses found today to reset.")

async def undo_last_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Undoes the user's latest expense entry."""
    user_id = update.effective_user.id

    latest_expense = sheets_manager.get_latest_expense(user_id)

    if latest_expense:
        row_index = latest_expense['row_index']
        if sheets_manager.delete_row(row_index):
            message = (
                f"✅ Successfully undid your latest expense:\n"
                f"Amount: ${latest_expense['amount']:.2f}\n"
                f"Category: {CATEGORIES.get(latest_expense['category'], latest_expense['category']).capitalize()}"
                + (f"\nDescription: {latest_expense['description']}" if latest_expense.get('description') else '')
            )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Failed to undo the latest expense. Please try again.")
    else:
        await update.message.reply_text("🤷‍♀️ No recent expense found to undo.")

async def send_daily_summary_job(context: ContextTypes.DEFAULT_TYPE):
    """Sends the daily summary and encouragement to all users with a recorded chat ID and expenses/budget."""
    users_data = sheets_manager.get_all_users_with_chat_id()

    if not users_data:
        logger.info("No users with saved chat IDs found for daily summary.")
        return

    for user_data in users_data:
        user_id = user_data['user_id']
        chat_id = user_data['chat_id']
        try:
            daily_summary = sheets_manager.get_daily_summary(user_id)
            daily_budget = sheets_manager.get_budget(user_id, 'daily_total')

            # Only send summary if there are expenses today or a daily budget is set
            if not daily_summary and daily_budget is None:
                continue

            message = "📊 Your Daily Expense Summary:\n\n"

            if daily_budget is not None:
                total_spent_today = sum(daily_summary.values())
                remaining_budget = daily_budget - total_spent_today

                message += f"Today's Total Spending: ${total_spent_today:.2f} / ${daily_budget:.2f}\n"
                if remaining_budget > 0:
                    message += f"Remaining Daily Budget: ${remaining_budget:.2f}\n\n"
                elif remaining_budget < 0:
                    message += f"⚠️ You were over your daily budget by ${abs(remaining_budget):.2f}!\n\n"
                else:
                    message += "✅ You spent exactly your daily budget today.\n\n"

            if daily_summary:
                message += "Breakdown by Category:\n"
                for category, amount in daily_summary.items():
                    budget = sheets_manager.get_budget(user_id, category)
                    if budget:
                         # Adjusting percentage comparison to be against budget amount, not percentage
                        percentage = (amount / budget) * 100
                        status = "✅" if percentage <= 100 else "⚠️"
                        message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f} / ${budget:.2f} ({percentage:.1f}%) {status}\n"
                    else:
                        message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f}\n"
            else:
                message += "No expenses recorded for today."

            # Add encouragement and Bible verses with explanations
            message += "\n---\n"
            message += random.choice(ENCOURAGEMENT_NOTES) + "\n"

            # Select a few random verses from the daily summary list
            num_verses_to_include = 1 # Include 1 verse
            selected_verses = random.sample(DAILY_SUMMARY_VERSES, num_verses_to_include)

            for verse in selected_verses:
                message += f"\n{verse['emoji']} *{verse['ref']}*\n{verse['text']}\n_{verse['explanation']}_\n"

            # Send the message to the user's chat ID
            await context.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Sent daily summary to user_id {user_id}")

        except Exception as e:
             logger.error(f"Error sending daily summary for user {user_id} (chat_id: {chat_id}): {e}")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_expense))
    application.add_handler(CommandHandler("view", view_expenses))
    application.add_handler(CommandHandler("budget", set_budget))
    application.add_handler(CommandHandler("set_daily", set_daily_budget))
    application.add_handler(CommandHandler("reset_today", reset_today_expenses))
    application.add_handler(CommandHandler("undo", undo_last_expense))
    application.add_handler(CommandHandler("summary", get_summary))
    application.add_handler(CommandHandler("help", start))

    # Add the callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))

    # Schedule daily summary job using application.job_queue
    # Schedule the job to run every day at 11:59 PM
    application.job_queue.run_daily(
        send_daily_summary_job,
        time=time(hour=23, minute=59),
    )
    logger.info("Daily summary job scheduled for 23:59.")

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 