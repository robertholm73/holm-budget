import sys
import requests
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QLabel, QTableWidget, QTableWidgetItem, 
                               QPushButton, QLineEdit, QDateEdit, QComboBox, 
                               QMessageBox, QTabWidget, QTextEdit, QSpinBox)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class BudgetAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server_url = "https://holm-budget-production.up.railway.app"  # Change this to your deployed URL
        self.local_db = "holm-budget-database.db"
        self.init_local_db()
        self.setup_ui()
        self.setup_timer()
        self.load_data()
        
    def init_local_db(self):
        """Initialize local SQLite database"""
        conn = sqlite3.connect(self.local_db)
        
        # Create tables matching server schema
        conn.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS budget_categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                budgeted_amount REAL NOT NULL DEFAULT 0,
                current_balance REAL NOT NULL DEFAULT 0
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY,
                user TEXT NOT NULL,
                amount REAL NOT NULL,
                account_id INTEGER,
                budget_category_id INTEGER,
                description TEXT,
                date TEXT NOT NULL,
                account_name TEXT,
                category TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("Budget Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Family Budget Manager")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Sync button
        sync_layout = QHBoxLayout()
        self.sync_btn = QPushButton("Sync with Server")
        self.sync_btn.clicked.connect(self.sync_with_server)
        self.status_label = QLabel("Ready")
        sync_layout.addWidget(self.sync_btn)
        sync_layout.addWidget(self.status_label)
        sync_layout.addStretch()
        layout.addLayout(sync_layout)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Add tabs
        self.setup_overview_tab()
        self.setup_transactions_tab()
        self.setup_analysis_tab()
        self.setup_manual_entry_tab()
        self.setup_accounts_tab()
    
    def setup_overview_tab(self):
        """Setup overview tab with summary information"""
        overview_widget = QWidget()
        layout = QVBoxLayout(overview_widget)
        
        # Summary cards
        summary_layout = QHBoxLayout()
        
        # Total spent this month
        self.total_month_label = QLabel("This Month: R0.00")
        self.total_month_label.setStyleSheet("background: #f0f0f0; padding: 20px; border-radius: 10px; font-size: 14px; font-weight: bold;")
        summary_layout.addWidget(self.total_month_label)
        
        # Average daily
        self.avg_daily_label = QLabel("Daily Average: R0.00")
        self.avg_daily_label.setStyleSheet("background: #e8f4fd; padding: 20px; border-radius: 10px; font-size: 14px; font-weight: bold;")
        summary_layout.addWidget(self.avg_daily_label)
        
        # Most common category
        self.top_category_label = QLabel("Top Category: None")
        self.top_category_label.setStyleSheet("background: #fff2e8; padding: 20px; border-radius: 10px; font-size: 14px; font-weight: bold;")
        summary_layout.addWidget(self.top_category_label)
        
        layout.addLayout(summary_layout)
        
        # Account balances section
        layout.addWidget(QLabel("Account Balances:"))
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels(["Account", "Type", "Balance"])
        self.accounts_table.setMaximumHeight(200)
        layout.addWidget(self.accounts_table)
        
        # Budget status section
        layout.addWidget(QLabel("Budget Status:"))
        self.budget_table = QTableWidget()
        self.budget_table.setColumnCount(4)
        self.budget_table.setHorizontalHeaderLabels(["Category", "Budgeted", "Spent", "Remaining"])
        self.budget_table.setMaximumHeight(200)
        layout.addWidget(self.budget_table)
        
        # Recent transactions
        layout.addWidget(QLabel("Recent Transactions:"))
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["Date", "Amount", "Account", "Category", "Description"])
        layout.addWidget(self.recent_table)
        
        self.tabs.addTab(overview_widget, "Overview")
    
    def setup_transactions_tab(self):
        """Setup transactions tab with full transaction list"""
        transactions_widget = QWidget()
        layout = QVBoxLayout(transactions_widget)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Category:"))
        self.category_filter = QComboBox()
        self.category_filter.addItems(["All", "Food", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Other"])
        self.category_filter.currentTextChanged.connect(self.filter_transactions)
        filter_layout.addWidget(self.category_filter)
        filter_layout.addStretch()
        
        # Export button
        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_transactions)
        filter_layout.addWidget(export_btn)
        
        layout.addLayout(filter_layout)
        
        # Transactions table
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.setHorizontalHeaderLabels(["Date", "User", "Amount", "Account", "Category", "Description"])
        layout.addWidget(self.transactions_table)
        
        self.tabs.addTab(transactions_widget, "All Transactions")
    
    def setup_analysis_tab(self):
        """Setup analysis tab with charts and statistics"""
        analysis_widget = QWidget()
        layout = QVBoxLayout(analysis_widget)
        
        # Chart placeholder
        self.chart_widget = QWidget()
        self.chart_widget.setMinimumHeight(400)
        self.chart_widget.setStyleSheet("background: white; border: 1px solid #ccc;")
        chart_layout = QVBoxLayout(self.chart_widget)
        chart_layout.addWidget(QLabel("Charts will be displayed here"))
        layout.addWidget(self.chart_widget)
        
        # Analysis controls
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Analysis Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Last 7 days", "Last 30 days", "Last 3 months", "All time"])
        self.period_combo.currentTextChanged.connect(self.update_analysis)
        controls_layout.addWidget(self.period_combo)
        controls_layout.addStretch()
        
        analyze_btn = QPushButton("Generate Analysis")
        analyze_btn.clicked.connect(self.generate_analysis)
        controls_layout.addWidget(analyze_btn)
        
        layout.addLayout(controls_layout)
        
        # Analysis results
        self.analysis_text = QTextEdit()
        self.analysis_text.setMaximumHeight(200)
        layout.addWidget(self.analysis_text)
        
        self.tabs.addTab(analysis_widget, "Analysis")
    
    def setup_manual_entry_tab(self):
        """Setup manual entry tab for adding transactions from desktop"""
        manual_widget = QWidget()
        layout = QVBoxLayout(manual_widget)
        
        layout.addWidget(QLabel("Add Transaction Manually:"))
        
        # Form fields
        form_layout = QVBoxLayout()
        
        # Account selection
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("Account:"))
        self.account_input = QComboBox()
        account_layout.addWidget(self.account_input)
        form_layout.addLayout(account_layout)
        
        # Amount
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("Amount (R):"))
        self.amount_input = QLineEdit()
        amount_layout.addWidget(self.amount_input)
        form_layout.addLayout(amount_layout)
        
        # Category
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.category_input = QComboBox()
        self.category_input.addItems(["Food", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Other"])
        category_layout.addWidget(self.category_input)
        form_layout.addLayout(category_layout)
        
        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_input = QLineEdit()
        desc_layout.addWidget(self.desc_input)
        form_layout.addLayout(desc_layout)
        
        # User
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("User:"))
        self.user_input = QComboBox()
        self.user_input.addItems(["wife", "husband"])
        user_layout.addWidget(self.user_input)
        form_layout.addLayout(user_layout)
        
        # Add button
        add_btn = QPushButton("Add Transaction")
        add_btn.clicked.connect(self.add_manual_transaction)
        form_layout.addWidget(add_btn)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        self.tabs.addTab(manual_widget, "Manual Entry")
    
    def setup_accounts_tab(self):
        """Setup accounts management tab"""
        accounts_widget = QWidget()
        layout = QVBoxLayout(accounts_widget)
        
        layout.addWidget(QLabel("Account Management:"))
        
        # Account balance update section
        balance_layout = QVBoxLayout()
        balance_layout.addWidget(QLabel("Update Account Balance:"))
        
        balance_form = QHBoxLayout()
        balance_form.addWidget(QLabel("Account:"))
        self.balance_account_combo = QComboBox()
        balance_form.addWidget(self.balance_account_combo)
        
        balance_form.addWidget(QLabel("New Balance (R):"))
        self.new_balance_input = QLineEdit()
        balance_form.addWidget(self.new_balance_input)
        
        update_balance_btn = QPushButton("Update Balance")
        update_balance_btn.clicked.connect(self.update_account_balance)
        balance_form.addWidget(update_balance_btn)
        
        balance_layout.addLayout(balance_form)
        layout.addLayout(balance_layout)
        
        # Budget management section
        budget_layout = QVBoxLayout()
        budget_layout.addWidget(QLabel("Budget Management:"))
        
        budget_form = QHBoxLayout()
        budget_form.addWidget(QLabel("Category:"))
        self.budget_category_combo = QComboBox()
        budget_form.addWidget(self.budget_category_combo)
        
        budget_form.addWidget(QLabel("Budget Amount (R):"))
        self.budget_amount_input = QLineEdit()
        budget_form.addWidget(self.budget_amount_input)
        
        update_budget_btn = QPushButton("Update Budget")
        update_budget_btn.clicked.connect(self.update_budget_amount)
        budget_form.addWidget(update_budget_btn)
        
        budget_layout.addLayout(budget_form)
        layout.addLayout(budget_layout)
        
        layout.addStretch()
        
        self.tabs.addTab(accounts_widget, "Accounts")
    
    def update_account_combos(self):
        """Update account and budget category combo boxes"""
        if hasattr(self, 'accounts'):
            # Update account combos
            self.account_input.clear()
            self.balance_account_combo.clear()
            for account in self.accounts:
                account_text = f"{account[1]} (R{account[3]:.2f})"
                self.account_input.addItem(account_text, account[0])
                self.balance_account_combo.addItem(account_text, account[0])
        
        if hasattr(self, 'budget_categories'):
            # Update budget category combos
            self.category_input.clear()
            self.budget_category_combo.clear()
            for budget in self.budget_categories:
                self.category_input.addItem(budget[1])
                budget_text = f"{budget[1]} (R{budget[2]:.2f} budgeted)"
                self.budget_category_combo.addItem(budget_text, budget[0])
    
    def update_account_balance(self):
        """Update account balance via API"""
        account_id = self.balance_account_combo.currentData()
        new_balance = self.new_balance_input.text()
        
        if not account_id or not new_balance:
            QMessageBox.warning(self, "Warning", "Please select account and enter balance.")
            return
        
        try:
            balance = float(new_balance)
            
            # Make API call to update the balance
            data = {
                "account_id": account_id,
                "balance": balance
            }
            
            response = requests.post(f"{self.server_url}/update_account_balance", 
                                   json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    QMessageBox.information(self, "Success", "Account balance updated successfully!")
                    self.new_balance_input.clear()
                    self.sync_with_server()  # Refresh data
                else:
                    QMessageBox.warning(self, "Error", f"Update failed: {result.get('message')}")
            else:
                QMessageBox.critical(self, "Error", "Server error. Please try again.")
                
        except ValueError:
            QMessageBox.critical(self, "Error", "Please enter a valid balance amount.")
        except requests.exceptions.RequestException:
            QMessageBox.critical(self, "Error", "Could not connect to server. Check your connection.")
    
    def update_budget_amount(self):
        """Update budget category amount via API"""
        category_id = self.budget_category_combo.currentData()
        budget_amount = self.budget_amount_input.text()
        
        if not category_id or not budget_amount:
            QMessageBox.warning(self, "Warning", "Please select category and enter budget amount.")
            return
        
        try:
            amount = float(budget_amount)
            
            # Make API call to update the budget
            data = {
                "category_id": category_id,
                "budget_amount": amount
            }
            
            response = requests.post(f"{self.server_url}/update_budget_amount", 
                                   json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    QMessageBox.information(self, "Success", "Budget amount updated successfully!")
                    self.budget_amount_input.clear()
                    self.sync_with_server()  # Refresh data
                else:
                    QMessageBox.warning(self, "Error", f"Update failed: {result.get('message')}")
            else:
                QMessageBox.critical(self, "Error", "Server error. Please try again.")
                
        except ValueError:
            QMessageBox.critical(self, "Error", "Please enter a valid budget amount.")
        except requests.exceptions.RequestException:
            QMessageBox.critical(self, "Error", "Could not connect to server. Check your connection.")
    
    def setup_timer(self):
        """Setup timer for automatic syncing"""
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_with_server)
        self.sync_timer.start(60000)  # Sync every minute
    
    def sync_with_server(self):
        """Sync data from server"""
        try:
            self.status_label.setText("Syncing...")
            response = requests.get(f"{self.server_url}/get_purchases", timeout=10)
            
            if response.status_code == 200:
                purchases = response.json()
                self.update_local_db(purchases)
                self.load_data()
                self.status_label.setText(f"Synced - {len(purchases)} total transactions")
            else:
                self.status_label.setText("Sync failed - Server error")
                
        except requests.exceptions.RequestException as e:
            self.status_label.setText("Sync failed - Server unreachable")
    
    def update_local_db(self, purchases):
        """Update local database with server data"""
        conn = sqlite3.connect(self.local_db)
        
        # Clear existing data
        conn.execute("DELETE FROM purchases")
        
        # Insert new data
        for purchase in purchases:
            conn.execute('''
                INSERT INTO purchases (id, user, amount, category, description, date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (purchase['id'], purchase['user'], purchase['amount'], 
                  purchase['category'], purchase['description'], purchase['date']))
        
        conn.commit()
        conn.close()
    
    def load_data(self):
        """Load data from local database and update UI"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.execute("SELECT * FROM purchases ORDER BY date DESC")
        self.purchases = cursor.fetchall()
        conn.close()
        
        self.update_overview()
        self.update_transactions_table()
    
    def update_overview(self):
        """Update overview tab with current data"""
        if not self.purchases:
            return
        
        # Calculate this month's total
        current_month = datetime.now().strftime("%Y-%m")
        month_total = sum(p[2] for p in self.purchases if p[5].startswith(current_month))
        self.total_month_label.setText(f"This Month: ${month_total:.2f}")
        
        # Calculate daily average
        if len(self.purchases) > 0:
            days_with_purchases = len(set(p[5][:10] for p in self.purchases))
            if days_with_purchases > 0:
                daily_avg = sum(p[2] for p in self.purchases) / days_with_purchases
                self.avg_daily_label.setText(f"Daily Average: ${daily_avg:.2f}")
        
        # Find top category
        categories = {}
        for p in self.purchases:
            cat = p[3] or "Other"
            categories[cat] = categories.get(cat, 0) + p[2]
        
        if categories:
            top_cat = max(categories, key=categories.get)
            self.top_category_label.setText(f"Top Category: {top_cat} (${categories[top_cat]:.2f})")
        
        # Update recent transactions table
        self.recent_table.setRowCount(min(10, len(self.purchases)))
        for i, purchase in enumerate(self.purchases[:10]):
            self.recent_table.setItem(i, 0, QTableWidgetItem(purchase[5][:10]))
            self.recent_table.setItem(i, 1, QTableWidgetItem(f"${purchase[2]:.2f}"))
            self.recent_table.setItem(i, 2, QTableWidgetItem(purchase[3] or "Other"))
            self.recent_table.setItem(i, 3, QTableWidgetItem(purchase[4] or ""))
    
    def update_transactions_table(self):
        """Update the full transactions table"""
        self.transactions_table.setRowCount(len(self.purchases))
        
        for i, purchase in enumerate(self.purchases):
            self.transactions_table.setItem(i, 0, QTableWidgetItem(purchase[5][:10]))
            self.transactions_table.setItem(i, 1, QTableWidgetItem(purchase[1]))
            self.transactions_table.setItem(i, 2, QTableWidgetItem(f"${purchase[2]:.2f}"))
            self.transactions_table.setItem(i, 3, QTableWidgetItem(purchase[3] or "Other"))
            self.transactions_table.setItem(i, 4, QTableWidgetItem(purchase[4] or ""))
    
    def filter_transactions(self):
        """Filter transactions by category"""
        selected_category = self.category_filter.currentText()
        
        if selected_category == "All":
            filtered_purchases = self.purchases
        else:
            filtered_purchases = [p for p in self.purchases if p[3] == selected_category]
        
        self.transactions_table.setRowCount(len(filtered_purchases))
        
        for i, purchase in enumerate(filtered_purchases):
            self.transactions_table.setItem(i, 0, QTableWidgetItem(purchase[5][:10]))
            self.transactions_table.setItem(i, 1, QTableWidgetItem(purchase[1]))
            self.transactions_table.setItem(i, 2, QTableWidgetItem(f"${purchase[2]:.2f}"))
            self.transactions_table.setItem(i, 3, QTableWidgetItem(purchase[3] or "Other"))
            self.transactions_table.setItem(i, 4, QTableWidgetItem(purchase[4] or ""))
    
    def export_transactions(self):
        """Export transactions to CSV"""
        try:
            import csv
            from PySide6.QtWidgets import QFileDialog
            
            filename, _ = QFileDialog.getSaveFileName(self, "Save CSV", "transactions.csv", "CSV Files (*.csv)")
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Date', 'User', 'Amount', 'Category', 'Description'])
                    
                    for purchase in self.purchases:
                        writer.writerow([purchase[5][:10], purchase[1], purchase[2], 
                                       purchase[3] or "Other", purchase[4] or ""])
                
                QMessageBox.information(self, "Export Complete", f"Transactions exported to {filename}")
        
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
    
    def update_analysis(self):
        """Update analysis based on selected period"""
        period = self.period_combo.currentText()
        # Implementation for period-based analysis
        pass
    
    def generate_analysis(self):
        """Generate detailed analysis"""
        if not self.purchases:
            self.analysis_text.setText("No transactions to analyze.")
            return
        
        # Calculate various statistics
        total_amount = sum(p[2] for p in self.purchases)
        avg_transaction = total_amount / len(self.purchases)
        
        # Category breakdown
        categories = {}
        for p in self.purchases:
            cat = p[3] or "Other"
            categories[cat] = categories.get(cat, 0) + p[2]
        
        # User breakdown
        users = {}
        for p in self.purchases:
            users[p[1]] = users.get(p[1], 0) + p[2]
        
        # Generate analysis text
        analysis = f"""BUDGET ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

SUMMARY:
• Total Transactions: {len(self.purchases)}
• Total Amount: ${total_amount:.2f}
• Average Transaction: ${avg_transaction:.2f}

SPENDING BY CATEGORY:
"""
        
        for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (amount / total_amount) * 100
            analysis += f"• {cat}: ${amount:.2f} ({percentage:.1f}%)\n"
        
        analysis += "\nSPENDING BY USER:\n"
        for user, amount in sorted(users.items(), key=lambda x: x[1], reverse=True):
            percentage = (amount / total_amount) * 100
            analysis += f"• {user}: ${amount:.2f} ({percentage:.1f}%)\n"
        
        # Recent trends
        analysis += "\nRECENT ACTIVITY:\n"
        recent_7_days = [p for p in self.purchases if 
                        (datetime.now() - datetime.fromisoformat(p[5].replace('Z', '+00:00'))).days <= 7]
        
        if recent_7_days:
            recent_total = sum(p[2] for p in recent_7_days)
            analysis += f"• Last 7 days: ${recent_total:.2f} ({len(recent_7_days)} transactions)\n"
            analysis += f"• Daily average (last 7 days): ${recent_total/7:.2f}\n"
        
        self.analysis_text.setText(analysis)
    
    def add_manual_transaction(self):
        """Add a transaction manually from desktop"""
        try:
            amount = float(self.amount_input.text())
            category = self.category_input.currentText()
            description = self.desc_input.text()
            user = self.user_input.currentText()
            
            # Create transaction data
            transaction = {
                "amount": amount,
                "category": category,
                "description": description
            }
            
            # Try to send to server
            try:
                response = requests.post(f"{self.server_url}/sync_purchases", 
                                       json=[transaction], timeout=10)
                
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Transaction added successfully!")
                    self.sync_with_server()  # Refresh data
                    
                    # Clear form
                    self.amount_input.clear()
                    self.desc_input.clear()
                else:
                    QMessageBox.warning(self, "Warning", "Transaction saved locally, will sync later.")
            
            except requests.exceptions.RequestException:
                # Save locally if server unavailable
                conn = sqlite3.connect(self.local_db)
                conn.execute('''
                    INSERT INTO purchases (user, amount, category, description, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user, amount, category, description, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                
                QMessageBox.information(self, "Saved Locally", 
                                      "Server unavailable. Transaction saved locally.")
                self.load_data()
        
        except ValueError:
            QMessageBox.critical(self, "Error", "Please enter a valid amount.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add transaction: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = BudgetAnalyzer()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()