import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                               QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
                               QTableWidgetItem, QPushButton, QLineEdit, QMessageBox,
                               QComboBox, QDoubleSpinBox, QDialog, QFormLayout, QDialogButtonBox,
                               QTextEdit, QDateTimeEdit)
from PySide6.QtCore import Qt
import pg8000
import os
from datetime import datetime
from decimal import Decimal

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
            
        self.setup_ui()
        self.load_data()
    
    def get_db_connection(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.database_url)
        return pg8000.connect(
            host=parsed.hostname,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            port=parsed.port or 5432,
            ssl_context=True
        )
    
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
        
        layout.addLayout(controls_layout)
    
    def setup_budget_tab(self):
        layout = QVBoxLayout(self.budget_widget)
        
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
    
    def load_data(self):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Load accounts
            cur.execute('SELECT id, name, balance FROM accounts ORDER BY name')
            accounts = cur.fetchall()
            
            # Populate accounts table
            self.accounts_table.setRowCount(len(accounts))
            for row, account in enumerate(accounts):
                self.accounts_table.setItem(row, 0, QTableWidgetItem(str(account[0])))
                self.accounts_table.setItem(row, 1, QTableWidgetItem(str(account[1])))
                self.accounts_table.setItem(row, 2, QTableWidgetItem(f"R{account[2]:.2f}"))
            
            # Load budget categories
            cur.execute('SELECT id, name, budgeted_amount, current_balance FROM budget_categories ORDER BY name')
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
            
            # Load recent purchases
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
            
            conn.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {str(e)}")
    
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
        # Get all accounts for the transfer dialog
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, name, balance FROM accounts ORDER BY name')
            accounts = cur.fetchall()
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
                
                # Record the transfer as a single purchase from the source account
                transfer_date = data['date']
                description = data['description'] or f"Transfer to {data['to_account_name']}"
                
                # Record only the withdrawal from source account with clear description
                cur.execute('''
                    INSERT INTO purchases (user_name, amount, account_id, budget_category_id, description, date)
                    VALUES (%s, %s, %s, NULL, %s, %s)
                ''', ('Robert', data['amount'], data['from_account_id'], 
                      f"Transfer: {description} → {data['to_account_name']}", transfer_date))
                
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", 
                                      f"Transferred R{data['amount']:.2f} from {data['from_account_name']} to {data['to_account_name']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to process transfer: {str(e)}")
    
    # Budget category management methods
    def add_budget_category(self):
        dialog = BudgetCategoryDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, budgeted_amount = dialog.get_data()
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute('INSERT INTO budget_categories (name, budgeted_amount, current_balance) VALUES (%s, %s, 0)', 
                           (name, budgeted_amount))
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
        # Get accounts and categories for dropdowns
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, name FROM accounts ORDER BY name')
            accounts = cur.fetchall()
            cur.execute('SELECT id, name FROM budget_categories ORDER BY name')
            categories = cur.fetchall()
            conn.close()
            
            dialog = PurchaseDialog(self, accounts, categories)
            if dialog.exec() == QDialog.Accepted:
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
                
                # Update budget category balance
                if data['category_id']:
                    cur.execute('UPDATE budget_categories SET current_balance = current_balance - %s WHERE id = %s', 
                               (data['amount'], data['category_id']))
                
                conn.commit()
                conn.close()
                self.load_data()
                QMessageBox.information(self, "Success", "Purchase added successfully!")
                
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add purchase: {str(e)}")
    
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
                    
                    # Reverse budget category balance
                    if category_id:
                        cur.execute('UPDATE budget_categories SET current_balance = current_balance + %s WHERE id = %s', (amount, category_id))
                    
                    # Delete purchase
                    cur.execute('DELETE FROM purchases WHERE id = %s', (purchase_id,))
                    
                    conn.commit()
                    conn.close()
                    self.load_data()
                    QMessageBox.information(self, "Success", "Purchase deleted successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete purchase: {str(e)}")


# Dialog classes
class AccountDialog(QDialog):
    def __init__(self, parent, name="", account_type="bank", balance=0.0):
        super().__init__(parent)
        self.setWindowTitle("Account")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.name_edit = QLineEdit(name)
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
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_data(self):
        return (self.name_edit.text(), self.type_combo.currentText(), self.balance_spin.value())


class BudgetCategoryDialog(QDialog):
    def __init__(self, parent, name="", budgeted_amount=0.0):
        super().__init__(parent)
        self.setWindowTitle("Budget Category")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.name_edit = QLineEdit(name)
        layout.addRow("Category Name:", self.name_edit)
        
        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setRange(0, 999999.99)
        self.budget_spin.setDecimals(2)
        self.budget_spin.setValue(budgeted_amount)
        layout.addRow("Budgeted Amount:", self.budget_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_data(self):
        return (self.name_edit.text(), self.budget_spin.value())


class PurchaseDialog(QDialog):
    def __init__(self, parent, accounts, categories):
        super().__init__(parent)
        self.setWindowTitle("Add Purchase")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QFormLayout(self)
        
        self.user_edit = QLineEdit("husband")  # Default to husband for desktop entries
        layout.addRow("User:", self.user_edit)
        
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 999999.99)
        self.amount_spin.setDecimals(2)
        layout.addRow("Amount (R):", self.amount_spin)
        
        self.account_combo = QComboBox()
        self.account_combo.addItem("None", None)
        for account in accounts:
            self.account_combo.addItem(f"{account[1]}", account[0])
        layout.addRow("Account:", self.account_combo)
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("None", None)
        for category in categories:
            self.category_combo.addItem(category[1], category[0])
        layout.addRow("Category:", self.category_combo)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        layout.addRow("Description:", self.description_edit)
        
        self.date_edit = QDateTimeEdit(datetime.now())
        self.date_edit.setCalendarPopup(True)
        layout.addRow("Date & Time:", self.date_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_data(self):
        return {
            'user': self.user_edit.text(),
            'amount': self.amount_spin.value(),
            'account_id': self.account_combo.currentData(),
            'category_id': self.category_combo.currentData(),
            'description': self.description_edit.toPlainText(),
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
            'date': self.date_edit.dateTime().toPython()
        }


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BudgetDesktopApp()
    window.show()
    sys.exit(app.exec())