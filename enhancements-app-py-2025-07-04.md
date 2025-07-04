
- In app.py:
	- All default bank accounts Bank Account 1, etc, are hardcoded. This should be removed because they end up in the DB - **every time**. 
	This is the third time I'm trying to remove them. Using a cleanup button/function EVERY time I use the app is not a solution. 
	- I wrote a settings file.json file in ./config
		- Everything is written as key:value pairs. 
		
		Regarding the bank accounts: All text "Bank 0" should be replaced by "Bank Zero" in the DB (as directed by the JSON) (this is the full name of the bank). **Please** do not 
	corrupt the data while performing this account name change. There is aleardy a lot of important data in there. 
		- In other words: "Peanut":["Bank Zero Cheque" ...] (json file) should be interpreted as "Peanut - Bank Zero Cheque" **exactly** as it is in the DB at the moment. 
		It is just encoded differently and gives me more freedom in future, where I can simply eddit/add the JSON, and the app will follow.
		- Regarding the budget categories, they are similarly encoded as key:value pairs in the json. As with the bank accounts, something like "Peanut": ["Bank Charges..."] will be
		rendered by Python as "Peanut - Bank Charges" , etc. 