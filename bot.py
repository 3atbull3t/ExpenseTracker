import os
import logging
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from google_sheets import GoogleSheetsManager
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import random
from constants import CATEGORIES  # Import CATEGORIES from constants.py
from aiohttp import web
import asyncio

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
# CATEGORIES = {
#     'food': '🍔 Food',
#     'transport': '🚗 Transport',
#     'shopping': '🛍️ Shopping',
#     'entertainment': '🎮 Entertainment',
#     'bills': '📝 Bills',
#     'other': '📦 Other',
#     'tithe': '🙏 Tithe/Offering'
# }

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
    {"ref": "Proverbs 21:20 (NIV)", "text": "The wise store up choice food and olive oil, but fools gulp theirs down.", "emoji": "🫒", "explanation": "Wise financial management involves saving and planning, not impulsive spending."},
    {"ref": "Proverbs 13:11 (NIV)", "text": "Dishonest money dwindles away, but whoever gathers money little by little makes it grow.", "emoji": "🌱", "explanation": "Wealth built gradually through honest means is more sustainable than quick gains."},
    {"ref": "Proverbs 22:7 (NIV)", "text": "The rich rule over the poor, and the borrower is slave to the lender.", "emoji": "⛓️", "explanation": "Debt creates dependency and limits freedom; it's better to live within your means."},
    {"ref": "Luke 14:28-30 (NIV)", "text": "Suppose one of you wants to build a tower. Won't you first sit down and estimate the cost to see if you have enough money to complete it? For if you lay the foundation and are not able to finish it, everyone who sees it will ridicule you, saying, 'This person began to build and wasn't able to finish.'", "emoji": "🏗️", "explanation": "Planning and budgeting are essential before making financial commitments."},
    {"ref": "Proverbs 27:23-24 (NIV)", "text": "Be sure you know the condition of your flocks, give careful attention to your herds; for riches do not endure forever, and a crown is not secure for all generations.", "emoji": "👑", "explanation": "Regular monitoring of your finances is crucial for long-term stability."},
    # Verses from the old BIBLE_VERSES list
    {"ref": "Matthew 6:21", "text": "For where your treasure is, there your heart will be also.", "emoji": "📖", "explanation": "A relevant verse about finances."},
    {"ref": "Proverbs 21:5", "text": "The plans of the diligent lead surely to abundance, but everyone who is hasty comes only to poverty.", "emoji": "📖", "explanation": "A relevant verse about finances."},
    {"ref": "Proverbs 3:9", "text": "Honor the Lord with your wealth and with the firstfruits of all your produce;", "emoji": "📖", "explanation": "A relevant verse about finances."},
    {"ref": "Proverbs 22:7", "text": "The rich rules over the poor, and the borrower is the slave of the lender.", "emoji": "📖", "explanation": "A relevant verse about finances."},
    {"ref": "Proverbs 27:23-24", "text": "Know well the prosperity of your flocks, and pay attention to your herds, for riches do not last forever; and does a crown endure to all generations?", "emoji": "📖", "explanation": "A relevant verse about finances."},
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

# Conversation states
AMOUNT, CATEGORY, DESCRIPTION = range(3)
BUDGET_CATEGORY, BUDGET_AMOUNT = range(2)
RESET_CATEGORY = 0

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
        "/add - Add a new expense\n"
        "/view - View your expenses\n"
        "/budget - Set category budgets\n"
        "/set_daily - Set your daily budget\n"
        "/set_weekly - Set your weekly budget\n"
        "/set_monthly - Set your monthly budget\n"
        "/summary - Get daily expense summary\n"
        "/reset_today - Reset today's expenses\n"
        "/undo - Undo your latest expense\n"
        "/help - Show this help message\n\n"
        "Available categories:\n"
    )
    for category in CATEGORIES.values():
        welcome_message += f"- {category}\n"
    
    await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)

async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the add expense conversation."""
    await update.message.reply_text(
        "Please enter the amount and description (e.g., '10 milo' or '50 lunch at restaurant'):"
    )
    return AMOUNT

async def add_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the amount and description input and ask for category."""
    try:
        # Split the message into amount and description
        parts = update.message.text.split(maxsplit=1)
        amount = float(parts[0])
        description = parts[1] if len(parts) > 1 else ""
        
        context.user_data['amount'] = amount
        context.user_data['description'] = description
        
        # Create keyboard for categories
        keyboard = []
        for category in CATEGORIES.values():
            keyboard.append([InlineKeyboardButton(category, callback_data=f"category_{category}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Please select a category:",
            reply_markup=reply_markup
        )
        return CATEGORY
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number followed by an optional description (e.g., '10 milo' or '50 lunch at restaurant')."
        )
        return AMOUNT

async def add_expense_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the category selection and save the expense."""
    query = update.callback_query
    await query.answer()
    
    selected_category_value = query.data.replace("category_", "")
    amount = context.user_data['amount']
    description = context.user_data['description']
    
    # Find the category key based on the selected value
    category = None
    for key, value in CATEGORIES.items():
        if value == selected_category_value:
            category = key
            break
    
    if category is None:
        await query.edit_message_text("❌ Error: Could not determine category. Please try again.")
        return ConversationHandler.END
    
    # Add expense to Google Sheets using the category key
    user_id = update.effective_user.id
    date = datetime.now().strftime("%Y-%m-%d")
    sheets_manager.add_expense(user_id, date, amount, category, description)
    
    await query.edit_message_text(
        f"✅ Expense added successfully!\n"
        f"Amount: ${amount:.2f}\n"
        f"Category: {selected_category_value}"
        + (f"\nDescription: {description}" if description else "")
    )
    
    # Check budgets and provide feedback
    context.user_data['category'] = selected_category_value
    await check_budgets(update, context)
    
    return ConversationHandler.END

async def check_budgets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check all budget types and provide feedback."""
    user_id = update.effective_user.id
    selected_category_value = context.user_data['category']
    
    # Debug logging
    print(f"Selected category value: {selected_category_value}")
    
    # Find the category key based on the selected value
    category = None
    for key, value in CATEGORIES.items():
        if value == selected_category_value:
            category = key
            break
    
    # Debug logging
    print(f"Found category key: {category}")
    
    if category is None:
        # This should ideally not happen if category selection is from predefined buttons
        await send_message("❌ Error: Could not determine category.")
        return
    
    # Get all summaries at the start
    today_summary = sheets_manager.get_daily_summary(user_id)
    weekly_summary = sheets_manager.get_weekly_summary(user_id)
    monthly_summary = sheets_manager.get_monthly_summary(user_id)
    
    # Debug logging for summaries
    print(f"Today's summary: {today_summary}")
    
    # Get budget using the category key
    category_budget = sheets_manager.get_budget(user_id, category)
    daily_budget = sheets_manager.get_budget(user_id, 'daily_total')
    weekly_budget = sheets_manager.get_budget(user_id, 'weekly_total')
    monthly_budget = sheets_manager.get_budget(user_id, 'monthly_total')
    
    # Debug logging
    print(f"Category budget for {category}: {category_budget}")
    
    # Function to send messages based on update type
    async def send_message(text, parse_mode=None):
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=parse_mode)
        else:
            await update.message.reply_text(text, parse_mode=parse_mode)
    
    # Check category budget
    if category_budget is not None:
        # Use the category key for getting the spending amount
        spent_in_category_today = today_summary.get(category, 0)
        remaining_category_budget = category_budget - spent_in_category_today
        
        # Debug logging
        print(f"Category: {category}")
        print(f"Budget: {category_budget}")
        print(f"Spent today: {spent_in_category_today}")
        print(f"Remaining: {remaining_category_budget}")
        
        if remaining_category_budget < 0:
            print(f"Budget exceeded! Showing warning message for {category}")
            await send_message(
                f"⚠️ You are over your {selected_category_value} budget!\n"
                f"Spent: ${spent_in_category_today:.2f} / Budget: ${category_budget:.2f}\n"
                f"Over by: ${abs(remaining_category_budget):.2f}"
            )
            # Add relevant verse
            if category == 'food':
                print("Food category detected, showing food moderation verse")
                selected_verse = random.choice(FOOD_MODERATION_VERSES)
                verse_message = (
                    f"\n{selected_verse['emoji']} <b>{selected_verse['ref']}</b>\n"
                    f"<i>{selected_verse['text']}</i>"
                )
            else:
                print("Non-food category detected, showing overspending verse")
                selected_verse = random.choice(OVERSPENDING_VERSES)
                verse_message = (
                    f"\n{selected_verse['emoji']} <b>{selected_verse['ref']}</b>\n"
                    f"<i>{selected_verse['text']}</i>\n"
                    f"<i>{selected_verse['explanation']}</i>"
                )
            await send_message(verse_message, parse_mode=ParseMode.HTML)
        else:
            print(f"Budget not exceeded for {category}. Remaining: {remaining_category_budget}")
    
    # Check daily budget
    if daily_budget is not None:
        total_spent_today = sum(today_summary.values())
        remaining_daily_budget = daily_budget - total_spent_today
        
        if remaining_daily_budget < 0:
            await send_message(
                f"⚠️ You are over your daily budget!\n"
                f"Spent: ${total_spent_today:.2f} / Budget: ${daily_budget:.2f}\n"
                f"Over by: ${abs(remaining_daily_budget):.2f}"
            )
            # Add overspending verse
            selected_verse = random.choice(OVERSPENDING_VERSES)
            verse_message = (
                f"\n{selected_verse['emoji']} <b>{selected_verse['ref']}</b>\n"
                f"<i>{selected_verse['text']}</i>\n"
                f"<i>{selected_verse['explanation']}</i>"
            )
            await send_message(verse_message, parse_mode=ParseMode.HTML)
    
    # Check weekly budget
    if weekly_budget is not None:
        total_spent_week = sum(weekly_summary.values())
        remaining_weekly_budget = weekly_budget - total_spent_week
        
        if remaining_weekly_budget < 0:
            await send_message(
                f"⚠️ You are over your weekly budget!\n"
                f"Spent: ${total_spent_week:.2f} / Budget: ${weekly_budget:.2f}\n"
                f"Over by: ${abs(remaining_weekly_budget):.2f}"
            )
            # Add overspending verse
            selected_verse = random.choice(OVERSPENDING_VERSES)
            verse_message = (
                f"\n{selected_verse['emoji']} <b>{selected_verse['ref']}</b>\n"
                f"<i>{selected_verse['text']}</i>\n"
                f"<i>{selected_verse['explanation']}</i>"
            )
            await send_message(verse_message, parse_mode=ParseMode.HTML)
    
    # Check monthly budget
    if monthly_budget is not None:
        total_spent_month = sum(monthly_summary.get("this_month", {}).values())
        remaining_monthly_budget = monthly_budget - total_spent_month
        
        if remaining_monthly_budget < 0:
            await send_message(
                f"⚠️ You are over your monthly budget!\n"
                f"Spent: ${total_spent_month:.2f} / Budget: ${monthly_budget:.2f}\n"
                f"Over by: ${abs(remaining_monthly_budget):.2f}"
            )
            # Add overspending verse
            selected_verse = random.choice(OVERSPENDING_VERSES)
            verse_message = (
                f"\n{selected_verse['emoji']} <b>{selected_verse['ref']}</b>\n"
                f"<i>{selected_verse['text']}</i>\n"
                f"<i>{selected_verse['explanation']}</i>"
            )
            await send_message(verse_message, parse_mode=ParseMode.HTML)

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

    message = f" {title}:\n\n"

    # Get relevant budget
    budget = None
    if data == "summary_daily":
        budget = sheets_manager.get_budget(user_id, 'daily_total')
    elif data == "summary_weekly":
        budget = sheets_manager.get_budget(user_id, 'weekly_total')
    elif data == "summary_monthly":
        budget = sheets_manager.get_budget(user_id, 'monthly_total')

    if data == "summary_monthly":
        # Handle detailed monthly summary
        message += "📅 This Month:\n"
        if summary.get("this_month"):
            total_monthly = sum(summary["this_month"].values())
            if budget:
                percentage = (total_monthly / budget) * 100
                status = "✅" if percentage <= 100 else "⚠️"
                message += f"Total: ${total_monthly:.2f} / ${budget:.2f} ({percentage:.1f}%) {status}\n\n"
            
            for category, amount in summary["this_month"].items():
                category_budget = sheets_manager.get_budget(user_id, category)
                if category_budget:
                    percentage = (amount / category_budget) * 100
                    status = "✅" if percentage <= 100 else "⚠️"
                    message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f} / ${category_budget:.2f} ({percentage:.1f}%) {status}\n"
                else:
                    message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f}\n"
        else:
            message += "No expenses this month.\n"

        message += "\n🗓 Last 31 Days:\n"
        if summary.get("last_31_days"):
            total_31_days = sum(summary["last_31_days"].values())
            if budget:
                percentage = (total_31_days / budget) * 100
                status = "✅" if percentage <= 100 else "⚠️"
                message += f"Total: ${total_31_days:.2f} / ${budget:.2f} ({percentage:.1f}%) {status}\n\n"
            
            for category, amount in summary["last_31_days"].items():
                category_budget = sheets_manager.get_budget(user_id, category)
                if category_budget:
                    percentage = (amount / category_budget) * 100
                    status = "✅" if percentage <= 100 else "⚠️"
                    message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f} / ${category_budget:.2f} ({percentage:.1f}%) {status}\n"
                else:
                    message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f}\n"
        else:
            message += "No expenses in the last 31 days.\n"

    else:
        # Handle daily, weekly, and all-time summaries
        total = sum(summary.values())
        if budget:
            percentage = (total / budget) * 100
            status = "✅" if percentage <= 100 else "⚠️"
            message += f"Total: ${total:.2f} / ${budget:.2f} ({percentage:.1f}%) {status}\n\n"
        
        for category, amount in summary.items():
            category_budget = sheets_manager.get_budget(user_id, category)
            if category_budget:
                percentage = (amount / category_budget) * 100
                status = "✅" if percentage <= 100 else "⚠️"
                message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f} / ${category_budget:.2f} ({percentage:.1f}%) {status}\n"
            else:
                message += f"{CATEGORIES.get(category, category).capitalize()}: ${amount:.2f}\n"

    await query.edit_message_text(message)

async def set_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the set budget conversation."""
    # Create keyboard for categories
    keyboard = []
    for category in CATEGORIES.values():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"budget_{category}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Please select a category to set budget for:",
        reply_markup=reply_markup
    )
    return BUDGET_CATEGORY

async def set_budget_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the category selection and ask for amount."""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("budget_", "")
    context.user_data['budget_category'] = category
    
    await query.edit_message_text(
        f"Selected category: {category}\n\n"
        "Please enter the budget amount:"
    )
    return BUDGET_AMOUNT

async def set_budget_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the amount and save the budget."""
    try:
        amount = float(update.message.text)
        selected_category_value = context.user_data['budget_category']
        user_id = update.effective_user.id
        
        # Find the category key based on the selected value
        category = None
        for key, value in CATEGORIES.items():
            if value == selected_category_value:
                category = key
                break
        
        if category is None:
            await update.message.reply_text("❌ Error: Could not determine category. Please try again.")
            return ConversationHandler.END
        
        # Set the budget using the category key
        sheets_manager.set_budget(user_id, category, amount)
        await update.message.reply_text(
            f"✅ Budget set for {selected_category_value}: ${amount:.2f}"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for the amount."
        )
        return BUDGET_AMOUNT

async def set_daily_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the set daily budget conversation."""
    context.user_data['budget_type'] = 'daily_total'
    await update.message.reply_text(
        "Please enter your daily budget amount:"
    )
    return BUDGET_AMOUNT

async def set_weekly_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the set weekly budget conversation."""
    context.user_data['budget_type'] = 'weekly_total'
    await update.message.reply_text(
        "Please enter your weekly budget amount:"
    )
    return BUDGET_AMOUNT

async def set_monthly_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the set monthly budget conversation."""
    context.user_data['budget_type'] = 'monthly_total'
    await update.message.reply_text(
        "Please enter your monthly budget amount:"
    )
    return BUDGET_AMOUNT

async def set_total_budget_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the amount for total budgets (daily/weekly/monthly)."""
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        budget_type = context.user_data.get('budget_type')
        
        if not budget_type:
            await update.message.reply_text("❌ Error: Could not determine budget type. Please try again.")
            return ConversationHandler.END
        
        # Set the budget
        sheets_manager.set_budget(user_id, budget_type, amount)
        
        # Send confirmation message
        budget_name = {
            'daily_total': 'Daily',
            'weekly_total': 'Weekly',
            'monthly_total': 'Monthly'
        }.get(budget_type, budget_type)
        
        await update.message.reply_text(
            f"✅ {budget_name} budget set to: ${amount:.2f}"
        )
        
        # Clear the budget type from context
        context.user_data.pop('budget_type', None)
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for the amount."
        )
        return BUDGET_AMOUNT

async def reset_today_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the reset today conversation."""
    # Create keyboard for categories
    keyboard = [
        [InlineKeyboardButton("All Categories", callback_data="reset_all")],
    ]
    for category in CATEGORIES.values():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"reset_{category}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Please select a category to reset (or 'All Categories' to reset everything):",
        reply_markup=reply_markup
    )
    return RESET_CATEGORY

async def reset_today_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the category selection and reset expenses."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    category = query.data.replace("reset_", "")
    
    if category == "all":
        if sheets_manager.delete_expenses_today(user_id):
            await query.edit_message_text("✅ Reset all of today's expenses.")
        else:
            await query.edit_message_text("No expenses found today to reset.")
    else:
        if sheets_manager.delete_expenses_today(user_id, category):
            await query.edit_message_text(f"✅ Reset today's expenses for category '{category}'.")
        else:
            await query.edit_message_text(f"No expenses found for category '{category}' today to reset.")
    
    return ConversationHandler.END

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

# Create web application
app = web.Application()

async def health_check(request):
    """Handle health check requests."""
    return web.Response(text="Bot is running!")

app.router.add_get('/health', health_check)

async def start_web_server():
    """Start the web server."""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()
    logger.info("Web server started on port %s", os.getenv('PORT', 8080))

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Add conversation handlers
    add_expense_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_expense_start)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_amount)],
            CATEGORY: [CallbackQueryHandler(add_expense_category, pattern="^category_")],
        },
        fallbacks=[],
    )

    set_budget_handler = ConversationHandler(
        entry_points=[CommandHandler("budget", set_budget_start)],
        states={
            BUDGET_CATEGORY: [CallbackQueryHandler(set_budget_category, pattern="^budget_")],
            BUDGET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_budget_amount)],
        },
        fallbacks=[],
    )

    set_daily_budget_handler = ConversationHandler(
        entry_points=[CommandHandler("set_daily", set_daily_budget_start)],
        states={
            BUDGET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_total_budget_amount)],
        },
        fallbacks=[],
    )

    set_weekly_budget_handler = ConversationHandler(
        entry_points=[CommandHandler("set_weekly", set_weekly_budget_start)],
        states={
            BUDGET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_total_budget_amount)],
        },
        fallbacks=[],
    )

    set_monthly_budget_handler = ConversationHandler(
        entry_points=[CommandHandler("set_monthly", set_monthly_budget_start)],
        states={
            BUDGET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_total_budget_amount)],
        },
        fallbacks=[],
    )

    reset_today_handler = ConversationHandler(
        entry_points=[CommandHandler("reset_today", reset_today_start)],
        states={
            RESET_CATEGORY: [CallbackQueryHandler(reset_today_category, pattern="^reset_")],
        },
        fallbacks=[],
    )

    # Add handlers
    application.add_handler(add_expense_handler)
    application.add_handler(set_budget_handler)
    application.add_handler(set_daily_budget_handler)
    application.add_handler(set_weekly_budget_handler)
    application.add_handler(set_monthly_budget_handler)
    application.add_handler(reset_today_handler)
    application.add_handler(CommandHandler("view", view_expenses))
    application.add_handler(CommandHandler("undo", undo_last_expense))
    application.add_handler(CommandHandler("summary", get_summary))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("start", start))

    # Add the callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))

    # Schedule daily summary job
    application.job_queue.run_daily(
        send_daily_summary_job,
        time=time(hour=23, minute=59),
    )
    logger.info("Daily summary job scheduled for 23:59.")

    # Start both the bot and web server
    async def start_services():
        await start_web_server()
        await application.initialize()
        await application.start()
        await application.run_polling(allowed_updates=Update.ALL_TYPES)

    asyncio.run(start_services())

if __name__ == '__main__':
    main() 
