import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                               QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
                               QTableWidgetItem, QPushButton, QLineEdit, QMessageBox,
                               QComboBox, QDoubleSpinBox, QDialog, QFormLayout, QDialogButtonBox,
                               QTextEdit, QDateTimeEdit)
from PySide6.QtCore import Qt, QTimer
import pg8000
import os
import signal
import threading
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# Load environment variables from .env file
from pathlib import Path
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value



class ConnectionManager:
    def __init__(self, database_url):
        self.database_url = database_url
        self._connection = None
        
    def get_connection_with_timeout(self, timeout_seconds=5):
        """Get database connection with aggressive timeout"""
        result = [None]
        exception = [None]
        
        def connect_thread():
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(self.database_url)
                
                # Close existing connection if it exists
                if self._connection:
                    try:
                        self._connection.close()
                    except:
                        pass
                
                print(f"Attempting database connection...")
                start_time = time.time()
                
                # Create new connection with timeout settings
                conn = pg8000.connect(
                    host=parsed.hostname,
                    database=parsed.path[1:],
                    user=parsed.username,
                    password=parsed.password,
                    port=parsed.port or 5432,
                    ssl_context=True,
                    timeout=3  # 3 second connection timeout
                )
                
                # Set aggressive query timeout
                cur = conn.cursor()
                cur.execute("SET statement_timeout = '5s'")  # 5 second query timeout
                cur.execute("SET lock_timeout = '3s'")      # 3 second lock timeout
                cur.execute("SET idle_in_transaction_session_timeout = '10s'")
                conn.commit()
                
                elapsed = time.time() - start_time
                print(f"Database connection established in {elapsed:.2f}s")
                
                result[0] = conn
                
            except Exception as e:
                exception[0] = e
                print(f"Database connection failed: {e}")
        
        # Run connection in separate thread with timeout
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
        
        # Wait for connection with timeout
        thread.join(timeout_seconds)
        
        if thread.is_alive():
            print(f"Database connection timed out after {timeout_seconds}s")
            raise Exception(f"Database connection timed out after {timeout_seconds} seconds")
        
        if exception[0]:
            raise exception[0]
            
        if result[0] is None:
            raise Exception("Failed to establish database connection")
            
        self._connection = result[0]
        return self._connection
        
    def get_connection(self):
        """Legacy method for backward compatibility"""
        return self.get_connection_with_timeout()


class BudgetDesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Budget Manager - Desktop")
        self.setGeometry(100, 100, 1000, 700)
        
        # Database connection (same as app.py)
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            QMessageBox.critical(self, "Error", "DATABASE_URL environment variable not set")
            return
        
        # Use connection manager instead of creating new connections
        self.conn_manager = ConnectionManager(self.database_url)
        
        # Current period tracking
        self.current_period_id = None
        self.budget_periods = []
            
        self.setup_ui()
        self.load_periods()
        self.load_data()
    

    def get_db_connection(self):
        return self.conn_manager.get_connection()
    
    
    def setup_ui(self):
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Accounts tab
        self.accounts_widget = QWidget()
        self.tab_widget.addTab(self.accounts_widget, "Accounts")
        self.setup_accounts_tab()
        
        # Budget Categories tab
        self.budget_widget = QWidget()
        self.tab_widget.addTab(self.budget_widget, "Budget Categories")
        self.setup_budget_tab()
        
        # Purchases tab
        self.purchases_widget = QWidget()
        self.tab_widget.addTab(self.purchases_widget, "Purchases")
        self.setup_purchases_tab()
    
    def setup_accounts_tab(self):
        layout = QVBoxLayout(self.accounts_widget)
        
        # Title
        title = QLabel("Account Balances")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Accounts table
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels(["ID", "Account Name", "Balance (R)"])
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.accounts_table)
        
        # Account management controls
        controls_layout = QHBoxLayout()
        
        # Add new account
        add_account_btn = QPushButton("Add Account")
        add_account_btn.clicked.connect(self.add_account)
        controls_layout.addWidget(add_account_btn)
        
        # Edit account
        edit_account_btn = QPushButton("Edit Selected")
        edit_account_btn.clicked.connect(self.edit_account)
        controls_layout.addWidget(edit_account_btn)
        
        # Delete account
        delete_account_btn = QPushButton("Delete Selected")
        delete_account_btn.clicked.connect(self.delete_account)
        controls_layout.addWidget(delete_account_btn)
        
        # Transfer between accounts
        transfer_btn = QPushButton("Transfer Money")
        transfer_btn.clicked.connect(self.transfer_money)
        controls_layout.addWidget(transfer_btn)
        
        controls_layout.addStretch()
        
        # Quick balance update
        controls_layout.addWidget(QLabel("Quick Balance Update:"))
        self.balance_entry = QLineEdit()
        self.balance_entry.setMaximumWidth(150)
        controls_layout.addWidget(self.balance_entry)
        
        update_btn = QPushButton("Update Balance")
        update_btn.clicked.connect(self.update_account_balance)
        controls_layout.addWidget(update_btn)
        
        # Add cleanup button
        cleanup_btn = QPushButton("Cleanup Bad Data")
        cleanup_btn.clicked.connect(self.cleanup_bad_data)
        cleanup_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        controls_layout.addWidget(cleanup_btn)
        
        layout.addLayout(controls_layout)
    
    def setup_budget_tab(self):
        layout = QVBoxLayout(self.budget_widget)
        
        # Period selection header
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Budget Period:"))
        self.period_combo = QComboBox()
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        period_layout.addWidget(self.period_combo)
        period_layout.addStretch()
        layout.addLayout(period_layout)
        
        # Title
        title = QLabel("Budget Categories")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Budget table
        self.budget_table = QTableWidget()
        self.budget_table.setColumnCount(5)
        self.budget_table.setHorizontalHeaderLabels(["ID", "Category", "Budgeted (R)", "Spent (R)", "Remaining (R)"])
        self.budget_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.budget_table)
        
        # Budget management controls
        budget_controls_layout = QHBoxLayout()
        
        # Add new category
        add_category_btn = QPushButton("Add Category")
        add_category_btn.clicked.connect(self.add_budget_category)
        budget_controls_layout.addWidget(add_category_btn)
        
        # Edit category
        edit_category_btn = QPushButton("Edit Selected")
        edit_category_btn.clicked.connect(self.edit_budget_category)
        budget_controls_layout.addWidget(edit_category_btn)
        
        # Delete category
        delete_category_btn = QPushButton("Delete Selected")
        delete_category_btn.clicked.connect(self.delete_budget_category)
        budget_controls_layout.addWidget(delete_category_btn)
        
        budget_controls_layout.addStretch()
        
        # Quick budget update
        budget_controls_layout.addWidget(QLabel("Quick Budget Update:"))
        self.budget_entry = QLineEdit()
        self.budget_entry.setMaximumWidth(150)
        budget_controls_layout.addWidget(self.budget_entry)
        
        budget_btn = QPushButton("Update Budget")
        budget_btn.clicked.connect(self.update_budget_amount)
        budget_controls_layout.addWidget(budget_btn)
        
        layout.addLayout(budget_controls_layout)
    
    def setup_purchases_tab(self):
        layout = QVBoxLayout(self.purchases_widget)
        
        # Title
        title = QLabel("Recent Purchases")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Purchases table
        self.purchases_table = QTableWidget()
        self.purchases_table.setColumnCount(7)
        self.purchases_table.setHorizontalHeaderLabels(["ID", "User", "Amount", "Account", "Category", "Description", "Date"])
        self.purchases_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.purchases_table)
        
        # Purchase management controls
        purchase_controls_layout = QHBoxLayout()
        
        # Add new purchase
        add_purchase_btn = QPushButton("Add Purchase")
        add_purchase_btn.clicked.connect(self.add_purchase)
        purchase_controls_layout.addWidget(add_purchase_btn)
        
        # Delete purchase
        delete_purchase_btn = QPushButton("Delete Selected")
        delete_purchase_btn.clicked.connect(self.delete_purchase)
        purchase_controls_layout.addWidget(delete_purchase_btn)
        
        purchase_controls_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.load_data)
        purchase_controls_layout.addWidget(refresh_btn)
        
        layout.addLayout(purchase_controls_layout)
    
    def load_periods(self):
        """Load available budget periods from database."""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute('''
                SELECT id, period_name, start_date, end_date, is_active 
                FROM budget_periods 
                ORDER BY start_date
            ''')
            periods = cur.fetchall()
            
            self.budget_periods = []
            self.period_combo.clear()
            
            for period in periods:
                period_data = {
                    'id': period[0],
                    'name': period[1],
                    'start_date': period[2],
                    'end_date': period[3],
                    'is_active': period[4]
                }
                self.budget_periods.append(period_data)
                self.period_combo.addItem(period[1], period[0])
                
                # Set current period if active
                if period[4]:  # is_active
                    self.current_period_id = period[0]
                    self.period_combo.setCurrentText(period[1])
            
            conn.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Period Load Error", f"Failed to load budget periods: {str(e)}")
    
    def on_period_changed(self):
        """Handle period selection change."""
        current_data = self.period_combo.currentData()
        if current_data:
            self.current_period_id = current_data
            self.load_data()  # Reload data for new period
    
    def load_data(self):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Load accounts with timeout protection
            try:
                cur.execute('SELECT id, name, balance FROM accounts ORDER BY name')
                accounts = cur.fetchall()
                
                # Populate accounts table
                self.accounts_table.setRowCount(len(accounts))
                for row, account in enumerate(accounts):
                    self.accounts_table.setItem(row, 0, QTableWidgetItem(str(account[0])))
                    self.accounts_table.setItem(row, 1, QTableWidgetItem(str(account[1])))
                    self.accounts_table.setItem(row, 2, QTableWidgetItem(f"R{account[2]:.2f}"))
            except Exception as e:
                QMessageBox.warning(self, "Data Load Warning", f"Failed to load accounts: {str(e)}")
                self.accounts_table.setRowCount(0)
            
            # Load budget categories with timeout protection
            try:
                if self.current_period_id:
                    cur.execute('''
                        SELECT id, name, budgeted_amount, current_balance 
                        FROM budget_categories 
                        WHERE period_id = %s 
                        ORDER BY name
                    ''', (self.current_period_id,))
                else:
                    # Fallback to current active period if no period selected
                    cur.execute('''
                        SELECT bc.id, bc.name, bc.budgeted_amount, bc.current_balance 
                        FROM budget_categories bc
                        JOIN budget_periods bp ON bc.period_id = bp.id
                        WHERE bp.is_active = TRUE 
                        ORDER BY bc.name
                    ''')
                categories = cur.fetchall()
                
                # Populate budget table
                self.budget_table.setRowCount(len(categories))
                for row, cat in enumerate(categories):
                    budgeted = float(cat[2])
                    spent = abs(float(cat[3]))  # current_balance is negative when money is spent
                    remaining = budgeted - spent
                    self.budget_table.setItem(row, 0, QTableWidgetItem(str(cat[0])))
                    self.budget_table.setItem(row, 1, QTableWidgetItem(str(cat[1])))
                    self.budget_table.setItem(row, 2, QTableWidgetItem(f"R{budgeted:.2f}"))
                    self.budget_table.setItem(row, 3, QTableWidgetItem(f"R{spent:.2f}"))
                    self.budget_table.setItem(row, 4, QTableWidgetItem(f"R{remaining:.2f}"))
            except Exception as e:
                QMessageBox.warning(self, "Data Load Warning", f"Failed to load budget categories: {str(e)}")
                self.budget_table.setRowCount(0)
            
            # Load recent purchases with timeout protection
            try:
                cur.execute('''
                    SELECT p.id, p.user_name, p.amount, a.name, bc.name, p.description, p.date
                    FROM purchases p 
                    LEFT JOIN accounts a ON p.account_id = a.id
                    LEFT JOIN budget_categories bc ON p.budget_category_id = bc.id
                    ORDER BY p.date DESC LIMIT 50
                ''')
                purchases = cur.fetchall()
                
                # Populate purchases table
                self.purchases_table.setRowCount(len(purchases))
                for row, purchase in enumerate(purchases):
                    formatted_date = purchase[6].strftime("%Y-%m-%d %H:%M") if purchase[6] else ""
                    self.purchases_table.setItem(row, 0, QTableWidgetItem(str(purchase[0])))
                    self.purchases_table.setItem(row, 1, QTableWidgetItem(str(purchase[1])))
                    self.purchases_table.setItem(row, 2, QTableWidgetItem(f"R{purchase[2]:.2f}"))
                    self.purchases_table.setItem(row, 3, QTableWidgetItem(purchase[3] or "N/A"))
                    self.purchases_table.setItem(row, 4, QTableWidgetItem(purchase[4] or "N/A"))
                    self.purchases_table.setItem(row, 5, QTableWidgetItem(purchase[5] or ""))
                    self.purchases_table.setItem(row, 6, QTableWidgetItem(formatted_date))
            except Exception as e:
                QMessageBox.warning(self, "Data Load Warning", f"Failed to load purchases: {str(e)}")
                self.purchases_table.setRowCount(0)
            
            conn.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Connection Error", f"Failed to connect to database: {str(e)}\n\nTry refreshing the data again.")
    
    def cleanup_bad_data(self):
        """Clean up accounts with generic/empty names"""
        reply = QMessageBox.question(self, "Cleanup Database", 
                                   "This will delete accounts with names like 'Bank Account X' and zero balances. Continue?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                
                # Delete accounts with generic names and zero balance
                cur.execute('''
                    DELETE FROM accounts 
                    WHERE (name LIKE 'Bank Account %' OR name LIKE 'Account %' OR name = '') 
                    AND balance = 0
                ''')
                deleted_accounts = cur.rowcount
                
                # Delete empty budget categories
                cur.execute('''
                    DELETE FROM budget_categories 
                    WHERE (name = '' OR name IS NULL) 
                    AND budgeted_amount = 0 
                    AND current_balance = 0
                ''')
                deleted_categories = cur.rowcount
                
                conn.commit()
                conn.close()
                
                self.load_data()
                QMessageBox.information(self, "Cleanup Complete", 
                                      f"Deleted {deleted_accounts} accounts and {deleted_categories} categories")
                
            except Exception as e:
                QMessageBox.critical(self, "Cleanup Error", f"Failed to cleanup: {str(e)}")
    
    def update_account_balance(self):
        selected_row = self.accounts_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select an account")
            return
        
        if not self.balance_entry.text().strip():
            QMessageBox.warning(self, "Input Error", "Please enter a balance amount")
            return
        
        try:
            new_balance = float(self.balance_entry.text())
            account_id = int(self.accounts_table.item(selected_row, 0).text())
            account_name = self.accounts_table.item(selected_row, 1).text()
            
            reply = QMessageBox.question(self, "Confirm Balance Update", 
                                       f"Set '{account_name}' balance to R{new_balance:.2f}?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute('UPDATE accounts SET balance = %s WHERE id = %s', (new_balance, account_id))
                conn.commit()
                conn.close()
                
                self.balance_entry.clear()
                self.load_data()
                QMessageBox.information(self, "Success", "Account balance updated!")
            
        except ValueError:
            QMessageBox.critical(self, "Input Error", "Please enter a valid number")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update balance: {str(e)}")
    
    def update_budget_amount(self):
        selected_row = self.budget_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select a budget category")
            return
        
        if not self.budget_entry.text().strip():
            QMessageBox.warning(self, "Input Error", "Please enter a budget amount")
            return
        
        try:
            new_budget = float(self.budget_entry.text())
            category_id = int(self.budget_table.item(selected_row, 0).text())
            category_name = self.budget_table.item(selected_row, 1).text()
            
            reply = QMessageBox.question(self, "Confirm Budget Update", 
                                       f"Set '{category_name}' budget to R{new_budget:.2f}?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute('UPDATE budget_categories SET budgeted_amount = %s WHERE id = %s', (new_budget, category_id))
                conn.commit()
                conn.close()
                
                self.budget_entry.clear()
                self.load_data()
                QMessageBox.information(self, "Success", "Budget amount updated!")
            
        except ValueError:
            QMessageBox.critical(self, "Input Error", "Please enter a valid number")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update budget: {str(e)}")
    
    # Account management methods
    def add_account(self):
        dialog = AccountDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, account_type, balance = dialog.get_data()
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute('INSERT INTO accounts (name, account_type, balance) VALUES (%s, %s, %s)', 
                           (name, account_type, balance))
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", "Account added successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to add account: {str(e)}")
    
    def edit_account(self):
        selected_row = self.accounts_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select an account")
            return
        
        account_id = int(self.accounts_table.item(selected_row, 0).text())
        current_name = self.accounts_table.item(selected_row, 1).text()
        current_balance = float(self.accounts_table.item(selected_row, 2).text().replace('R', ''))
        
        dialog = AccountDialog(self, current_name, "bank", current_balance)
        if dialog.exec() == QDialog.Accepted:
            name, account_type, balance = dialog.get_data()
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute('UPDATE accounts SET name = %s, account_type = %s, balance = %s WHERE id = %s', 
                           (name, account_type, balance, account_id))
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", "Account updated successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to update account: {str(e)}")
    
    def delete_account(self):
        selected_row = self.accounts_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select an account")
            return
        
        account_name = self.accounts_table.item(selected_row, 1).text()
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete account '{account_name}'?\nThis will also delete all associated purchases.",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            account_id = int(self.accounts_table.item(selected_row, 0).text())
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                # Delete associated purchases first
                cur.execute('DELETE FROM purchases WHERE account_id = %s', (account_id,))
                # Delete account
                cur.execute('DELETE FROM accounts WHERE id = %s', (account_id,))
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", "Account deleted successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete account: {str(e)}")
    
    def transfer_money(self):
        # Get all accounts for the transfer dialog with timeout protection
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            try:
                cur.execute('SELECT id, name, balance FROM accounts ORDER BY name')
                accounts = cur.fetchall()
            except Exception as e:
                QMessageBox.critical(self, "Database Timeout", f"Failed to load accounts for transfer: {str(e)}")
                return
                
            conn.close()
            
            if len(accounts) < 2:
                QMessageBox.warning(self, "Insufficient Accounts", "You need at least 2 accounts to make a transfer.")
                return
            
            dialog = TransferDialog(self, accounts)
            if dialog.exec() == QDialog.Accepted:
                data = dialog.get_data()
                
                conn = self.get_db_connection()
                cur = conn.cursor()
                
                # Check if source account has sufficient funds
                cur.execute('SELECT balance FROM accounts WHERE id = %s', (data['from_account_id'],))
                source_balance = cur.fetchone()[0]
                
                if source_balance < data['amount']:
                    QMessageBox.warning(self, "Insufficient Funds", 
                                      f"Source account only has R{source_balance:.2f}, but you're trying to transfer R{data['amount']:.2f}")
                    conn.close()
                    return
                
                # Perform the transfer
                # Subtract from source account
                cur.execute('UPDATE accounts SET balance = balance - %s WHERE id = %s', 
                           (data['amount'], data['from_account_id']))
                
                # Add to destination account
                cur.execute('UPDATE accounts SET balance = balance + %s WHERE id = %s', 
                           (data['amount'], data['to_account_id']))
                
                # Record the transfer in the dedicated transfers table
                transfer_date = data['date']
                description = data['description'] or f"Transfer from {data['from_account_name']} to {data['to_account_name']}"
                originator = data.get('originator', 'Robert')  # Default to Robert if not specified
                
                cur.execute('''
                    INSERT INTO transfers (from_account_id, to_account_id, amount, description, originator_user, transfer_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (data['from_account_id'], data['to_account_id'], data['amount'], 
                      description, originator, transfer_date))
                
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", 
                                      f"Transferred R{data['amount']:.2f} from {data['from_account_name']} to {data['to_account_name']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to process transfer: {str(e)}")
    
    # Budget category management methods
    def add_budget_category(self):
        if not self.current_period_id:
            QMessageBox.warning(self, "No Period Selected", "Please select a budget period first.")
            return
            
        dialog = BudgetCategoryDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, budgeted_amount = dialog.get_data()
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO budget_categories (name, budgeted_amount, current_balance, period_id) 
                    VALUES (%s, %s, 0, %s)
                ''', (name, budgeted_amount, self.current_period_id))
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", "Budget category added successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to add category: {str(e)}")
    
    def edit_budget_category(self):
        selected_row = self.budget_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select a budget category")
            return
        
        category_id = int(self.budget_table.item(selected_row, 0).text())
        current_name = self.budget_table.item(selected_row, 1).text()
        current_budget = float(self.budget_table.item(selected_row, 2).text().replace('R', ''))
        
        dialog = BudgetCategoryDialog(self, current_name, current_budget)
        if dialog.exec() == QDialog.Accepted:
            name, budgeted_amount = dialog.get_data()
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute('UPDATE budget_categories SET name = %s, budgeted_amount = %s WHERE id = %s', 
                           (name, budgeted_amount, category_id))
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", "Budget category updated successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to update category: {str(e)}")
    
    def delete_budget_category(self):
        selected_row = self.budget_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select a budget category")
            return
        
        category_name = self.budget_table.item(selected_row, 1).text()
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete category '{category_name}'?\nAssociated purchases will have their category cleared.",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            category_id = int(self.budget_table.item(selected_row, 0).text())
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                # Clear category from purchases
                cur.execute('UPDATE purchases SET budget_category_id = NULL WHERE budget_category_id = %s', (category_id,))
                # Delete category
                cur.execute('DELETE FROM budget_categories WHERE id = %s', (category_id,))
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", "Budget category deleted successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete category: {str(e)}")
    
    # Purchase management methods
    def add_purchase(self):
        # Use cached data from load_data() instead of making new database calls
        print("Starting add_purchase - using cached data...")
        start_time = time.time()
        
        try:
            # Extract account data from the accounts table
            accounts = []
            for row in range(self.accounts_table.rowCount()):
                account_id = int(self.accounts_table.item(row, 0).text())
                account_name = self.accounts_table.item(row, 1).text()
                accounts.append((account_id, account_name))
            
            # Extract category data from the budget table  
            categories = []
            for row in range(self.budget_table.rowCount()):
                category_id = int(self.budget_table.item(row, 0).text())
                category_name = self.budget_table.item(row, 1).text()
                categories.append((category_id, category_name))
            
            elapsed = time.time() - start_time
            print(f"Cached data extracted in {elapsed:.2f}s - {len(accounts)} accounts, {len(categories)} categories")
            
            print("Creating PurchaseDialog...")
            dialog_start = time.time()
            dialog = PurchaseDialog(self, accounts, categories)
            dialog_elapsed = time.time() - dialog_start
            print(f"PurchaseDialog created in {dialog_elapsed:.2f}s")
            
            print("Showing dialog...")
            show_start = time.time()
            
            # Use non-modal approach for WSL2 compatibility
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            
            # Connect to handle result when dialog finishes
            def handle_result():
                show_elapsed = time.time() - show_start
                print(f"Dialog interaction completed in {show_elapsed:.2f}s")
                self.process_purchase_result(dialog)
            
            dialog.accepted.connect(handle_result)
            
            show_elapsed = time.time() - show_start
            print(f"Dialog shown in {show_elapsed:.2f}s")
            return  # Don't block the main thread
                
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add purchase: {str(e)}")
    
    def process_purchase_result(self, dialog):
        """Process the purchase dialog result asynchronously"""
        try:
            data = dialog.get_data()
            
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Insert purchase
            cur.execute('''
                INSERT INTO purchases (user_name, amount, account_id, budget_category_id, description, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (data['user'], data['amount'], data['account_id'], data['category_id'], 
                  data['description'], data['date']))
            
            # Update account balance
            if data['account_id']:
                cur.execute('UPDATE accounts SET balance = balance - %s WHERE id = %s', 
                           (data['amount'], data['account_id']))
            
            # Update budget category balance (with period validation)
            if data['category_id']:
                if self.current_period_id:
                    # Validate that the category belongs to the current period
                    cur.execute('''
                        UPDATE budget_categories 
                        SET current_balance = current_balance - %s 
                        WHERE id = %s AND period_id = %s
                    ''', (data['amount'], data['category_id'], self.current_period_id))
                else:
                    # Fallback for backward compatibility
                    cur.execute('''
                        UPDATE budget_categories SET current_balance = current_balance - %s WHERE id = %s
                    ''', (data['amount'], data['category_id']))
            
            conn.commit()
            conn.close()
            self.load_data()
            QMessageBox.information(self, "Success", "Purchase added successfully!")
            
            # Close the dialog
            dialog.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add purchase: {str(e)}")
            dialog.close()
    
    def delete_purchase(self):
        selected_row = self.purchases_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select a purchase")
            return
        
        purchase_amount = self.purchases_table.item(selected_row, 2).text()
        purchase_desc = self.purchases_table.item(selected_row, 5).text()
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete this purchase?\n{purchase_amount} - {purchase_desc}",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            purchase_id = int(self.purchases_table.item(selected_row, 0).text())
            try:
                # Get purchase details first to reverse balance changes
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute('SELECT amount, account_id, budget_category_id FROM purchases WHERE id = %s', (purchase_id,))
                purchase = cur.fetchone()
                
                if purchase:
                    amount, account_id, category_id = purchase
                    
                    # Reverse account balance
                    if account_id:
                        cur.execute('UPDATE accounts SET balance = balance + %s WHERE id = %s', (amount, account_id))
                    
                    # Reverse budget category balance (with period validation)
                    if category_id:
                        # Note: We don't validate period here since we're reversing a historical transaction
                        # The category might be from a different period than currently selected
                        cur.execute('UPDATE budget_categories SET current_balance = current_balance + %s WHERE id = %s', (amount, category_id))
                    
                    # Delete purchase
                    cur.execute('DELETE FROM purchases WHERE id = %s', (purchase_id,))
                    
                    conn.commit()
                    conn.close()
                    self.load_data()
                    QMessageBox.information(self, "Success", "Purchase deleted successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete purchase: {str(e)}")


# Dialog classes - THESE NEED TO BE AT THE END, AFTER THE MAIN CLASS
class AccountDialog(QDialog):
    def __init__(self, parent, name="", account_type="bank", balance=0.0):
        super().__init__(parent)
        self.setWindowTitle("Account")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Enter account name...")
        layout.addRow("Account Name:", self.name_edit)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["bank", "credit", "cash", "investment"])
        self.type_combo.setCurrentText(account_type)
        layout.addRow("Account Type:", self.type_combo)
        
        self.balance_spin = QDoubleSpinBox()
        self.balance_spin.setRange(-999999.99, 999999.99)
        self.balance_spin.setDecimals(2)
        self.balance_spin.setValue(balance)
        layout.addRow("Initial Balance:", self.balance_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Account name cannot be empty!")
            return
        if len(name) < 2:
            QMessageBox.warning(self, "Validation Error", "Account name must be at least 2 characters!")
            return
        self.accept()
    
    def get_data(self):
        return (self.name_edit.text().strip(), self.type_combo.currentText(), self.balance_spin.value())


class BudgetCategoryDialog(QDialog):
    def __init__(self, parent, name="", budgeted_amount=0.0):
        super().__init__(parent)
        self.setWindowTitle("Budget Category")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Enter category name...")
        layout.addRow("Category Name:", self.name_edit)
        
        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setRange(0, 999999.99)
        self.budget_spin.setDecimals(2)
        self.budget_spin.setValue(budgeted_amount)
        layout.addRow("Budgeted Amount:", self.budget_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Category name cannot be empty!")
            return
        if len(name) < 2:
            QMessageBox.warning(self, "Validation Error", "Category name must be at least 2 characters!")
            return
        if self.budget_spin.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Budget amount must be greater than 0!")
            return
        self.accept()
    
    def get_data(self):
        return (self.name_edit.text().strip(), self.budget_spin.value())


class PurchaseDialog(QDialog):
    def __init__(self, parent, accounts, categories):
        print(f"PurchaseDialog.__init__ starting with {len(accounts)} accounts, {len(categories)} categories")
        init_start = time.time()
        
        super().__init__(parent)
        self.setWindowTitle("Add Purchase")
        self.setModal(False)  # Never use modal in WSL2
        self.resize(400, 300)
        
        layout = QFormLayout(self)
        
        print("Creating form fields...")
        field_start = time.time()
        
        self.user_edit = QLineEdit("")  # Start empty instead of "husband"
        self.user_edit.setPlaceholderText("Enter user name...")
        layout.addRow("User:", self.user_edit)
        
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 999999.99)
        self.amount_spin.setDecimals(2)
        layout.addRow("Amount (R):", self.amount_spin)
        
        print("Populating account combo...")
        combo_start = time.time()
        
        self.account_combo = QComboBox()
        self.account_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.account_combo.setMinimumContentsLength(20)
        self.account_combo.addItem("-- Select Account --", None)
        for account in accounts:
            self.account_combo.addItem(f"{account[1]}", account[0])
        
        combo_elapsed = time.time() - combo_start
        print(f"Account combo populated in {combo_elapsed:.2f}s")
        layout.addRow("Account:", self.account_combo)
        
        print("Populating category combo...")
        cat_combo_start = time.time()
        
        self.category_combo = QComboBox()
        self.category_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.category_combo.setMinimumContentsLength(20)
        self.category_combo.addItem("-- Select Category --", None)
        for category in categories:
            self.category_combo.addItem(category[1], category[0])
            
        cat_combo_elapsed = time.time() - cat_combo_start
        print(f"Category combo populated in {cat_combo_elapsed:.2f}s")
        layout.addRow("Category:", self.category_combo)
        
        print("Creating remaining fields...")
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Enter purchase description...")
        layout.addRow("Description:", self.description_edit)
        
        self.date_edit = QDateTimeEdit(datetime.now())
        self.date_edit.setCalendarPopup(True)
        layout.addRow("Date & Time:", self.date_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        total_elapsed = time.time() - init_start
        print(f"PurchaseDialog.__init__ completed in {total_elapsed:.2f}s")
    
    def validate_and_accept(self):
        user = self.user_edit.text().strip()
        if not user:
            QMessageBox.warning(self, "Validation Error", "User name cannot be empty!")
            return
        
        if self.amount_spin.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Amount must be greater than 0!")
            return
        
        if self.account_combo.currentData() is None:
            reply = QMessageBox.question(self, "No Account Selected", 
                                       "No account selected. Continue without updating account balance?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
        
        description = self.description_edit.toPlainText().strip()
        if not description:
            reply = QMessageBox.question(self, "No Description", 
                                       "No description entered. Continue anyway?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
        
        self.accept()
    
    def get_data(self):
        return {
            'user': self.user_edit.text().strip(),
            'amount': self.amount_spin.value(),
            'account_id': self.account_combo.currentData(),
            'category_id': self.category_combo.currentData(),
            'description': self.description_edit.toPlainText().strip(),
            'date': self.date_edit.dateTime().toPython()
        }


class TransferDialog(QDialog):
    def __init__(self, parent, accounts):
        super().__init__(parent)
        self.setWindowTitle("Transfer Money Between Accounts")
        self.setModal(True)
        self.resize(400, 250)
        
        layout = QFormLayout(self)
        
        # From account
        self.from_account_combo = QComboBox()
        for account in accounts:
            self.from_account_combo.addItem(f"{account[1]} (R{account[2]:.2f})", account[0])
        layout.addRow("From Account:", self.from_account_combo)
        
        # To account
        self.to_account_combo = QComboBox()
        for account in accounts:
            self.to_account_combo.addItem(f"{account[1]} (R{account[2]:.2f})", account[0])
        # Set to second account by default
        if len(accounts) > 1:
            self.to_account_combo.setCurrentIndex(1)
        layout.addRow("To Account:", self.to_account_combo)
        
        # Originator (who is initiating the transfer)
        self.originator_combo = QComboBox()
        self.originator_combo.addItem("Robert", "Robert")
        self.originator_combo.addItem("Peanut", "Peanut")
        layout.addRow("Transfer Originator:", self.originator_combo)
        
        # Amount
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 999999.99)
        self.amount_spin.setDecimals(2)
        layout.addRow("Amount (R):", self.amount_spin)
        
        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description for the transfer")
        layout.addRow("Description:", self.description_edit)
        
        # Date
        self.date_edit = QDateTimeEdit(datetime.now())
        self.date_edit.setCalendarPopup(True)
        layout.addRow("Date & Time:", self.date_edit)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        # Store accounts data for validation
        self.accounts = accounts
    
    def validate_and_accept(self):
        from_id = self.from_account_combo.currentData()
        to_id = self.to_account_combo.currentData()
        
        if from_id == to_id:
            QMessageBox.warning(self, "Invalid Transfer", "Cannot transfer to the same account!")
            return
        
        if self.amount_spin.value() <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Transfer amount must be greater than 0!")
            return
        
        self.accept()
    
    def get_data(self):
        from_id = self.from_account_combo.currentData()
        to_id = self.to_account_combo.currentData()
        
        # Get account names for the transaction records
        from_name = self.from_account_combo.currentText().split(' (')[0]
        to_name = self.to_account_combo.currentText().split(' (')[0]
        
        return {
            'from_account_id': from_id,
            'to_account_id': to_id,
            'from_account_name': from_name,
            'to_account_name': to_name,
            'amount': self.amount_spin.value(),
            'description': self.description_edit.text(),
            'originator': self.originator_combo.currentData(),
            'date': self.date_edit.dateTime().toPython()
        }


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BudgetDesktopApp()
    window.show()
    sys.exit(app.exec())