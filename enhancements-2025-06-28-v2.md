I have some enhancements that I want to add to the desktop and mobile apps please. 

- Desktop app:
	1. I need the budget to stretch over 12 months, not 1. On the very top line, above the categories, I would like to have a line of tabs "July 2025", August 2025", etc, entil 12 months from now.
	2. When I click on one of those, it should open the budget and expenses of that month and the tab font/color should change to indicate it is selected. 
	3. The months run from **exactly** the 25th to the 24th. For example, 25 June -- 24 July will be the budget period for "July 2025" 
	4. At midnight each 24th, the budget period for the next month will be activated. This can maybe be done in app.py because it runs on the Render server. 
	5. The above will change the DB schema, can you suggest something practical? 
	6. I mus be able to select future months for budgeting purposes, as well as past ones for retrospection. 
	7. After 12 months have passed, I will archive the data locally, but that is not a concern for now. We'll cover that bridge when we get there.
	8. The transfer is listed as a purchase, but transfers are not purchases. Also, the transfer created a new user "Transfer" in the DB which is not supposed to exist. Transfers are always from 
	"Robert" to "Peanut" or vice versa. The "user" of the transfer is the originator of the transfer. 
	9. In the accounts tab:
		- A total should be showed at the bottom.
		- All negative amounts must turn red. 
	10. In the Budget categories tab:
		- Totals at the bottom for the three numerical columns. 
		- All negative amounts in the Remaining column must turn red.
	11. In the Ourchases tab: 
		- A column for Peanut and one for Robert, with totals at the bottom. 
	12. There should also be an "Income" button at an appropriate place. It should take Username, Amount and Target bank account as arguments. 
	13. Can you please create a JSON file as template for the creation of the forthcoming months' bank accounts and budget categories. For now you perhaps generate one with the bank accounts and budget categories of 
	July 2025's entries as a starting point. (This is a one-time thing). I will then work on that file so it can be used in future at midnight on the 24th of each month. 
		
- Mobile app:
	1. One line on top showing which month & year's budget we're working with. It's just and indicator, it doesn't have to do anything nor list the other months. 
	2. On the Admin tab: Account balances, all negative amounts must turn red 