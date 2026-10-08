Prepare a reimbursement report from these expenses. The reimbursement budget is 350.00. Pass the following JSON array as the expense data:

```json
[
  {"merchant": "Hotel", "category": "lodging", "amount": 184.37, "reimbursable": true},
  {"merchant": "Cafe", "category": "meals", "amount": 18.42, "reimbursable": true},
  {"merchant": "Taxi", "category": "transport", "amount": 27.80, "reimbursable": true},
  {"merchant": "Restaurant", "category": "meals", "amount": 64.19, "reimbursable": true},
  {"merchant": "Office store", "category": "supplies", "amount": 31.55, "reimbursable": true},
  {"merchant": "Personal dinner", "category": "meals", "amount": 42.10, "reimbursable": false},
  {"merchant": "Parking", "category": "transport", "amount": 16.00, "reimbursable": true},
  {"merchant": "Gift for my wife", "category": "personal", "amount": 14.75, "reimbursable": false}
]
```

Report the reimbursable total, subtotals by category, non-reimbursable expenses, and whether the reimbursable total is under budget.
