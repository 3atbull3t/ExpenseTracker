import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from constants import CATEGORIES  # Import CATEGORIES from constants.py

class GoogleSheetsManager:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
        self.creds = None
        self.service = None
        self._authenticate()
        self._initialize_sheets()

    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('sheets', 'v4', credentials=self.creds)

    def _initialize_sheets(self):
        """Initialize the spreadsheet with required sheets if they don't exist."""
        try:
            # Check if sheets exist
            print("Checking existing sheets...")
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=self.SPREADSHEET_ID).execute()
            sheets = sheet_metadata.get('sheets', [])
            existing_sheets = [sheet['properties']['title'] for sheet in sheets]
            print(f"Existing sheets: {existing_sheets}")

            # Create sheets if they don't exist
            if 'Expenses' not in existing_sheets:
                print("Creating 'Expenses' sheet...")
                self._create_sheet('Expenses', [
                    ['User ID', 'Date', 'Amount', 'Category', 'Description']
                ])
                print("'Expenses' sheet creation requested.")
            
            if 'Budgets' not in existing_sheets:
                print("Creating 'Budgets' sheet...")
                self._create_sheet('Budgets', [
                    ['User ID', 'Chat ID', 'Category', 'Amount']
                ])
                print("'Budgets' sheet creation requested.")

        except Exception as e:
            print(f"Error initializing sheets: {e}")

    def _create_sheet(self, sheet_name, headers):
        """Create a new sheet with headers."""
        try:
            print(f"Attempting to create sheet: {sheet_name}")
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.SPREADSHEET_ID,
                body={'requests': [request]}
            ).execute()
            print(f"Sheet '{sheet_name}' created successfully.")

            # Add headers
            range_name = f'{sheet_name}!A1'
            print(f"Adding headers to '{sheet_name}' at range {range_name}...")
            self.service.spreadsheets().values().update(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name,
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            print(f"Headers added to '{sheet_name}'.")

        except Exception as e:
            print(f"Error creating sheet {sheet_name}: {e}")

    def add_expense(self, user_id, date, amount, category, description=""):
        """Add a new expense to the spreadsheet."""
        try:
            values = [[user_id, date, amount, category, description]]
            range_name = 'Expenses!A:E'
            
            body = {
                'values': values
            }
            
            self.service.spreadsheets().values().append(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error adding expense: {e}")
            return False

    def get_expenses(self, user_id, start_date=None, end_date=None):
        """Get expenses for a user within a date range."""
        try:
            print(f"get_expenses called for user {user_id} with range: {start_date} to {end_date}")
            range_name = 'Expenses!A:E'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return []

            # Filter expenses for the user
            expenses = []
            for row in values[1:]:  # Skip header row
                if len(row) >= 4 and str(row[0]) == str(user_id):
                    expense_date = datetime.strptime(row[1], '%Y-%m-%d')
                    print(f"Checking expense on date {row[1]} (parsed as {expense_date.date()})")
                    if start_date and end_date:
                        if start_date <= expense_date.date() <= end_date:
                            print("  -> Passed date filter")
                            expenses.append({
                                'date': row[1],
                                'amount': float(row[2]),
                                'category': row[3],
                                'description': row[4] if len(row) > 4 else ''
                            })
                    else:
                        print("  -> No date filter applied")
                        expenses.append({
                            'date': row[1],
                            'amount': float(row[2]),
                            'category': row[3],
                            'description': row[4] if len(row) > 4 else ''
                        })

            return expenses
        except Exception as e:
            print(f"Error getting expenses: {e}")
            return []

    def _calculate_summary(self, expenses):
        """Calculate summary of expenses by category from a list of expenses."""
        summary = {}
        for expense in expenses:
            # Get the category from the expense
            category_with_emoji = expense['category']
            
            # Convert to category key by removing emoji
            category = None
            for key, value in CATEGORIES.items():
                if value == category_with_emoji:
                    category = key
                    break
            
            # If we couldn't find the category key, use the original category
            if category is None:
                category = category_with_emoji
            
            # Add to summary
            if category not in summary:
                summary[category] = 0
            summary[category] += expense['amount']
        return summary

    def get_daily_summary(self, user_id):
        """Get summary of expenses for today."""
        try:
            today = datetime.now().date()
            expenses = self.get_expenses(user_id)

            # Filter today's expenses
            today_expenses = [
                exp for exp in expenses
                if datetime.strptime(exp['date'], '%Y-%m-%d').date() == today
            ]

            return self._calculate_summary(today_expenses)
        except Exception as e:
            print(f"Error getting daily summary: {e}")
            return {}

    def get_weekly_summary(self, user_id):
        """Get summary of expenses for the current week."""
        try:
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            expenses = self.get_expenses(user_id, start_date=start_of_week, end_date=today)
            return self._calculate_summary(expenses)
        except Exception as e:
            print(f"Error getting weekly summary: {e}")
            return {}

    def get_monthly_summary(self, user_id):
        """Get summary of expenses for the current month."""
        try:
            today = datetime.now().date()
            start_of_month = today.replace(day=1)
            expenses_month = self.get_expenses(user_id, start_date=start_of_month, end_date=today)

            # Get expenses for the last 31 days
            start_date_last_31_days = today - timedelta(days=30)
            expenses_last_31_days = self.get_expenses(user_id, start_date=start_date_last_31_days, end_date=today)

            return {
                "this_month": self._calculate_summary(expenses_month),
                "last_31_days": self._calculate_summary(expenses_last_31_days)
            }
        except Exception as e:
            print(f"Error getting monthly summary: {e}")
            return {}

    def get_all_time_summary(self, user_id):
        """Get summary of all time expenses."""
        try:
            expenses = self.get_expenses(user_id)
            return self._calculate_summary(expenses)
        except Exception as e:
            print(f"Error getting all time summary: {e}")
            return {}

    def get_last_month_summary(self, user_id):
        """Get summary of expenses for the previous calendar month."""
        try:
            today = datetime.now().date()
            first_day_of_this_month = today.replace(day=1)
            last_day_of_last_month = first_day_of_this_month - timedelta(days=1)
            first_day_of_last_month = last_day_of_last_month.replace(day=1)
            expenses = self.get_expenses(user_id, start_date=first_day_of_last_month, end_date=last_day_of_last_month)
            return self._calculate_summary(expenses)
        except Exception as e:
            print(f"Error getting last month summary: {e}")
            return {}

    def get_yearly_summary(self, user_id):
        """Get summary of expenses for the current year."""
        try:
            today = datetime.now().date()
            first_day_of_year = today.replace(month=1, day=1)
            expenses = self.get_expenses(user_id, start_date=first_day_of_year, end_date=today)
            return self._calculate_summary(expenses)
        except Exception as e:
            print(f"Error getting yearly summary: {e}")
            return {}

    def set_budget(self, user_id, category, amount):
        """Set budget for a category."""
        try:
            # Check if budget already exists
            range_name = 'Budgets!A:C'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            row_index = None
            
            for i, row in enumerate(values[1:], start=2):  # Skip header row
                if len(row) >= 2 and str(row[0]) == str(user_id) and row[1] == category:
                    row_index = i
                    break

            if row_index:
                # Update existing budget
                range_name = f'Budgets!C{row_index}'
                body = {
                    'values': [[amount]]
                }
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.SPREADSHEET_ID,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            else:
                # Add new budget
                body = {
                    'values': [[user_id, category, amount]]
                }
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.SPREADSHEET_ID,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()

            return True
        except Exception as e:
            print(f"Error setting budget: {e}")
            return False

    def get_budget(self, user_id, category):
        """Get budget for a category."""
        try:
            range_name = 'Budgets!A:C'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            for row in values[1:]:  # Skip header row
                if len(row) >= 3 and str(row[0]) == str(user_id) and row[1] == category:
                    return float(row[2])
            return None
        except Exception as e:
            print(f"Error getting budget: {e}")
            return None

    def save_user_chat_id(self, user_id, chat_id):
        """Save or update a user's chat ID in the Budgets sheet."""
        try:
            range_name = 'Budgets!A:D' # Adjusted range for new column
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name
            ).execute()

            values = result.get('values', [])
            user_row_index = None

            # Find the row for the user ID
            for i, row in enumerate(values[1:], start=2): # Start from row 2 to skip header
                # Check if row has at least User ID column and it matches
                if len(row) > 0 and str(row[0]) == str(user_id):
                    user_row_index = i
                    break

            if user_row_index:
                # Update chat ID in the existing row
                # Assumes Chat ID is the second column (index 1)
                range_to_update = f'Budgets!B{user_row_index}'
                body = { 'values': [[str(chat_id)]] }
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.SPREADSHEET_ID,
                    range=range_to_update,
                    valueInputOption='RAW',
                    body=body
                ).execute()
                print(f"Updated chat ID for user {user_id}")
            else:
                # Add a new row for the user with User ID and Chat ID
                # Category and Amount can be empty initially
                body = { 'values': [[str(user_id), str(chat_id), '', '']] }
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.SPREADSHEET_ID,
                    range=range_name, # Append to the defined range
                    valueInputOption='RAW',
                    body=body
                ).execute()
                print(f"Added new user {user_id} with chat ID {chat_id}")

            return True
        except Exception as e:
            print(f"Error saving user chat ID: {e}")
            return False

    def get_all_users_with_chat_id(self):
        """Retrieves all user IDs and their associated Chat IDs from the Budgets sheet."""
        try:
            range_name = 'Budgets!A:B' # Get User ID and Chat ID columns
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values:
                return []

            users_data = []
            # Iterate starting from the second row to skip headers
            for row in values[1:]:
                 # Ensure row has at least User ID and Chat ID
                if len(row) >= 2 and row[0] and row[1]:
                    users_data.append({'user_id': str(row[0]), 'chat_id': str(row[1])})

            return users_data
        except Exception as e:
            print(f"Error getting all users with chat ID: {e}")
            return []

    def delete_expenses_today(self, user_id, category=None):
        """Deletes expense entries for a user for today, optionally filtered by category."""
        try:
            range_name = 'Expenses!A:E' # Get all expense data
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values:
                print("No expenses found to delete.")
                return False

            today_str = datetime.now().strftime("%Y-%m-%d")
            rows_to_delete = [] # Store 1-indexed row numbers to delete

            # Find rows that match the criteria (user, date, category)
            # Iterate from the last row upwards to avoid index issues during batch deletion
            for i in range(len(values) - 1, 0, -1): # Iterate from second to last row up to the first data row (index 1)
                row = values[i]
                # Ensure row has enough columns and matches user ID and today's date
                if len(row) >= 2 and str(row[0]) == str(user_id) and row[1] == today_str:
                    # Check category if specified
                    if category is None or (len(row) >= 4 and row[3].lower() == category.lower()):
                        # Add the 1-indexed row number (i + 1 because header is row 1)
                        rows_to_delete.append(i + 1)

            if not rows_to_delete:
                print(f"No matching expenses found for deletion for user {user_id} today (category: {category}).")
                return False

            # Prepare batch delete request. Requests should be ordered by row index DESC.
            # We iterated from the bottom up, so rows_to_delete is already in the correct order.
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': self._get_sheet_id('Expenses'), # Need a helper to get sheetId
                        'dimension': 'ROWS',
                        'startIndex': row - 1, # API uses 0-indexed
                        'endIndex': row # API end index is exclusive
                    }
                }
            } for row in rows_to_delete]

            # Execute the batch delete
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.SPREADSHEET_ID,
                body={'requests': requests}
            ).execute()

            print(f"Deleted {len(rows_to_delete)} expenses for user {user_id} for today (category: {category}).")
            return True

        except Exception as e:
            print(f"Error deleting expenses: {e}")
            return False

    def _get_sheet_id(self, sheet_name):
        """Helper to get the sheet ID from the sheet name."""
        try:
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=self.SPREADSHEET_ID).execute()
            sheets = sheet_metadata.get('sheets', [])
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return None # Sheet not found
        except Exception as e:
            print(f"Error getting sheet ID: {e}")
            return None

    def get_latest_expense(self, user_id):
        """Gets the latest expense entry for a user along with its row index."""
        try:
            range_name = 'Expenses!A:E' # Get all expense data
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values or len(values) <= 1: # Check if there's a header row and at least one data row
                print("No expenses found.")
                return None

            # Iterate from the last data row upwards
            for i in range(len(values) - 1, 0, -1): # Iterate from last row up to the first data row (index 1)
                row = values[i]
                # Ensure row has at least User ID and it matches
                if len(row) > 0 and str(row[0]) == str(user_id):
                    # Return the expense data and the 1-indexed row number
                    return {
                        'row_index': i + 1,
                        'date': row[1] if len(row) > 1 else '',
                        'amount': float(row[2]) if len(row) > 2 else 0.0,
                        'category': row[3] if len(row) > 3 else '',
                        'description': row[4] if len(row) > 4 else ''
                    }

            print(f"No expenses found for user {user_id}.")
            return None # No expense found for the user

        except Exception as e:
            print(f"Error getting latest expense: {e}")
            return None

    def delete_row(self, row_index):
        """Deletes a specific row by its 1-indexed row number."""
        if row_index is None or row_index <= 1: # Cannot delete header row or invalid index
            print(f"Invalid row index for deletion: {row_index}")
            return False
        try:
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': self._get_sheet_id('Expenses'), # Get sheetId for 'Expenses'
                        'dimension': 'ROWS',
                        'startIndex': row_index - 1, # API uses 0-indexed start
                        'endIndex': row_index # API end index is exclusive
                    }
                }
            }]

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.SPREADSHEET_ID,
                body={'requests': requests}
            ).execute()

            print(f"Deleted row {row_index}.")
            return True

        except Exception as e:
            print(f"Error deleting row {row_index}: {e}")
            return False 