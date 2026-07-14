import argparse
import calendar
from datetime import datetime
import json
import csv
import sys
transaction_file = "intelligence_transactions.csv"
budget_file = "intelligence_budget.json"
report_file = "intelligence_report.txt"
REQUIRED_FIELDS = ["transaction_type", "category", "amount", "description", "date"]

class Transaction:
    def __init__(self, transaction_type, category: str, amount: float, description: str, date=None):
        self.transaction_type = transaction_type
        self.category = category
        self.description = description
        self.__amount = amount
        if date is None:
           self.date = datetime.today().strftime("%Y-%m-%d")
        else:
            self.date = date
    
    @property
    def amount(self):
        return self.__amount
    
    @amount.setter
    def amount(self, value):
        if value <=0:
            raise ValueError("Amount must be greater than zero")
        self.__amount = value

    
    def to_dict(self):
        transaction = {
            "transaction_type" : self.transaction_type,
            "category" : self.category,
            "amount" : self.amount,
            "description": self.description, 
            "date" : self.date
        }
        return transaction
    @classmethod
    def from_dict(cls, data):
        transaction_type = data["transaction_type"]
        category = data["category"]
        amount = float(data["amount"])
        description = data["description"]
        date = data["date"]
        return cls(transaction_type, category, amount, description, date)

class Budget:
    def __init__(self):
        self.__limits = self.load()
    
    def get_limit(self, category):
        return self.__limits.get(category, None)
    
    
    def get_all_limits(self):
        return self.__limits
    
    def load(self):
        try:
           with open(budget_file, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        
        except json.JSONDecodeError as e:
            print(f"Warning: {budget_file} is corrupted ({e}). "
                     f"Ignoring its contents.")
            return {}
        
        except OSError as e:
               print(f"Warning: {budget_file} could not be read ({e}).")
               return {}
    
    
    def save(self):
        with open(budget_file, "w") as file:
            json.dump(self.__limits, file, indent=2)
    
    def set_limit(self, category, amount):
        self.__limits[category] = amount
        self.save()
    
    def delete_limit(self, category):
        if category in self.__limits:
            self.__limits.pop(category)
            self.save()
            return "Category deleted successfully"
        else:
            return "Category not found"


    def check_overspend(self, category, actual):
        bound = self.get_limit(category)
        if bound is None or actual <= bound:
           return 0
        return actual - bound

class Report:
    def __init__(self, transaction, budget):
        self.transaction = transaction
        self.budget = budget
    
    def monthly_totals(self):
        total_expenses = {}
        for t in self.transaction:
            if t.transaction_type == "expense":
                month = t.date[:7]
                total_expenses[month] = total_expenses.get(month, 0) + t.amount
        return total_expenses
    
    def compare_months(self):
        total_expenses = self.monthly_totals()
        months = sorted(total_expenses.keys())
        
        if len(months) < 2:
            return "Not enough monthly data to compare (need expenses in at least 2 different months)"
        
        
        prev_month, current_month = months[-2], months[-1]
        prev_total = total_expenses[prev_month]
        current_total = total_expenses[current_month]
        
        if prev_total == 0:
           return "Cannot calculate percentage change: previous month had $0 in expenses."
           

        change = ((current_total - prev_total) / prev_total) * 100
        if change > 0:
           return f"Spending is UP by {change:.2f}% compared to {prev_month}."
        elif change < 0:
           return f"Spending is DOWN by {abs(change):.2f}% compared to {prev_month}."
        else:
           return f"Spending is unchanged compared to {prev_month}."
    
    def savings_rate(self):
        income = 0
        expense = 0
        for t in self.transaction:
            if t.transaction_type == "income":
                income += t.amount
            elif t.transaction_type == "expense":
                expense += t.amount
        try: 
           savings = (income - expense) / income * 100
        except ZeroDivisionError:
           return "Income can't be zero"
        return f"{float(savings):.2f}%"
    
    def category_vs_budget(self):
        category_totals = {}
        category_dict = {}
        for t in self.transaction:
            if t.transaction_type == "expense":
                category = t.category
                amount = t.amount
                category_totals[category] = category_totals.get(category, 0) + amount
        
        for category, total in category_totals.items():
            actual = total
            limit = self.budget.get_limit(category)
            difference = self.budget.check_overspend(category, actual)
            category_dict[category] = {"actual": actual, "limit": limit, "difference": difference}
        return category_dict
        
    def forecast(self, category):
        current_month = datetime.today().strftime("%Y-%m")
        c_total = 0
        for t in self.transaction:
            if t.transaction_type == "expense" and t.date[:7] == current_month and t.category == category:
               c_total += t.amount
        if c_total == 0:
            return "No spending recorded for this category this month"
        days_elapsed = datetime.today().day
        year = datetime.today().year
        month = datetime.today().month
        days_in_month = calendar.monthrange(year, month)[1]
        days_remaining = days_in_month - days_elapsed
        daily_spend = c_total / days_elapsed
        limit = self.budget.get_limit(category)
        if c_total >= limit:
           return f"Warning: already overspent '{category.capitalize()}' this month"
        if limit is None:
            return "No budget limit set for this category"
        days_until_overspend = (limit - c_total) / daily_spend
        if days_until_overspend < days_remaining:
            return f"Warning: at this rate you will overspend '{category.capitalize()}' in {int(days_until_overspend)} days"
        else:
            return f"Category '{category.capitalize()}' is on track"
    
    def balance(self):
        income = 0
        expense = 0
        print("==========BALANCE========")
        for t in self.transaction:
            if t.transaction_type == "income":
                income += t.amount
            elif t.transaction_type == "expense":
                expense += t.amount
        
        current_balance = income - expense
        print(f"Balance :${current_balance}")

    def summary(self):
        income = 0
        expense = 0
        print("==========BALANCE========")
        for t in self.transaction:
            if t.transaction_type == "income":
                income += t.amount
            elif t.transaction_type == "expense":
                expense += t.amount
        
        current_balance = income - expense
        print(f"Total Income: ${income}")
        print(f"Total Expenses: ${expense}")
        print(f"Current Balance: ${current_balance}")
        print()

        print("===========MONTHLY TOTALS=========")
        total_expenses = self.monthly_totals()
        for month, t_expense in total_expenses.items():
            print(f"{month} : {t_expense}")
        print()
        
        print("=========MONTHLY COMPARISON========")
        print(self.compare_months())
        print()

        print("=========SAVINGS RATE========")
        savings = self.savings_rate()
        if isinstance(savings, str):
           print(f"Savings rate: {savings}")
        else:
           print(f"Savings rate: {savings:.2f}%")
        print()

        print("=========CATEGORY vs BUDGET========")
        category_dict = self.category_vs_budget()
        for category, category_data in category_dict.items():
            actual = category_data["actual"]
            limit = category_data["limit"]
            difference = category_data["difference"]
            
            print(f"Category: {category}")
            print(f"Actual: {actual}")
            print(f"Limit: {limit}")
            if difference > 0:
                print(f" Over budget by ${difference:.2f}")
        print()

        print("============FORECAST==========")
        for category, category_data in category_dict.items():
            if self.budget.get_limit(category) is not None:
                print(self.forecast(category))
    
    def export_txt(self, filename):
        income = 0
        expense = 0
        try:
           with open(filename, "w") as file:
                file.write("=" * 50 + "\n")
                file.write("PERSONAL BUDGET INTELLIGENCE TOOL\n")
                file.write(f"Generated: {datetime.today().strftime('%Y-%m-%d %H:%M')}\n")
                file.write("=" * 50 + "\n\n")
                
                file.write("BALANCE\n")
                for t in self.transaction:
                    if t.transaction_type == "income":
                       income += t.amount
                    elif t.transaction_type == "expense":
                       expense += t.amount
                current_balance = income - expense
                file.write(f"Total Income: ${income}\n")
                file.write(f"Total Expenses: ${expense}\n")
                file.write(f"Current Balance: ${current_balance}\n")
                file.write("-" * 50 + "\n")
                
                file.write("MONTHLY TOTALS\n")
                total_expenses = self.monthly_totals()
                for month, t_expense in total_expenses.items():
                    file.write(f"{month} : ${t_expense}\n")
                file.write("-" * 50 + "\n")

                file.write("MONTHLY COMPARISON\n")
                file.write(f"{self.compare_months()}\n")
                file.write("-" * 50 + "\n")
                
                file.write("SAVINGS RATE\n")
                savings = self.savings_rate()
                if isinstance(savings, str):
                   file.write(f"Savings rate: {savings}\n")
                else:
                   file.write(f"Savings rate: {savings:.2f}%\n")
                file.write("-" * 50 + "\n")
                
                file.write("CATEGORY vs BUDGET\n")
                category_dict = self.category_vs_budget()
                for category, category_data in category_dict.items():
                    actual = category_data["actual"]
                    limit = category_data["limit"]
                    difference = category_data["difference"]
                    file.write(f"Category: {category.capitalize()}\n")
                    file.write(f"Actual: ${actual}\n")
                    file.write(f"Limit: ${limit}\n")
                    if difference > 0:
                       file.write(f" Over budget by ${difference:.2f}\n")
                file.write("-" * 50 + "\n")

                file.write("FORECAST\n")
                for category, category_data in category_dict.items():
                    if self.budget.get_limit(category) is not None:
                       file.write(f"{self.forecast(category)}\n")
        except OSError as e:
               print(f"Failed to write report: {e}")
               return
        print(f"Text file exported successfully to '{filename}'.")

def load_transactions():
    transactions = []
    try:
        with open(transaction_file, "r", newline="") as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader, start=2):  
                if row is None:
                    continue
                missing = [f for f in REQUIRED_FIELDS if not row.get(f)]
                if missing:
                    print(f"Warning: skipping row {i} in {transaction_file} "
                          f"(missing field(s): {', '.join(missing)})")
                    continue
                try:
                    t = Transaction.from_dict(row)
                    
                except (ValueError, TypeError):
                    print(f"Warning: skipping row {i} in {transaction_file} "
                          f"(invalid amount: {row['amount']!r})")
                    continue
                transactions.append(t)
        return transactions
    except FileNotFoundError:
        return []
    except (csv.Error, UnicodeDecodeError, OSError) as e:
        print(f"Warning: {transaction_file} could not be read ({e}). "
              f"Starting with an empty transaction list.")
        return []

def save_transactions(transaction):
    with open(transaction_file, "w", newline="") as file:
        fieldnames = REQUIRED_FIELDS
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for t in transaction:
            writer.writerow(t.to_dict())

def add_transaction(transactions):
    transaction_type = input("Is this an income or expense?: ").strip().lower()
    category = input("Which category does this belong to?: ").strip().lower()
    while True:
        try:
            amount = float(input("What is the amount?: $"))
            break
        except ValueError:
            print("  Please enter a number.")
    description = input("Give a description in two words or less: ").strip()
    t = Transaction(transaction_type, category, amount, description, date=None)
    transactions.append(t)
    save_transactions(transactions)
    print("Updated and saved!")

def delete_transaction(transactions):
    if not transactions:
        print("No transactions to return")
        return
    for i, t in enumerate(transactions, start=1):
        print(f"{i}. {t.date} | {t.transaction_type} | {t.category} | ${t.amount:.2f} | {t.description}")
    user_input = int(input("What number of the transaction will you like to delete: "))
    if user_input <= 0:
        print("Number starts from 1")
    elif user_input > len(transactions):
        print("Number is higher than range ")
    else:
        confirmation = input("Are you sure (y/n): ").lower()
        if confirmation == "y":
           actual_index = user_input - 1
           transactions.pop(actual_index)
           save_transactions(transactions)
           print("Transaction deleted successfully")
        else:
            print("Deletion cancelled")
            return

def manage_budget(budget):
    for c , a in budget.get_all_limits().items():
        print(f"{c.capitalize()}: ${a}")
    print("-----Choose the action you will like to perform-----")
    print("1. Set/update limit")
    print("2. Delete limit")
    print("3. exit")
    while True:
        option = input("What action will you like to perform on limit: ")
        if option == "1":
           category = input("Which category will you like to set limit for: ")
           amount = float(input("What is the limit amount: "))
           budget.set_limit(category, amount)
           print("Limit updated")
        elif option == "2":
             category = input("Which category will you like to delete: ")
             print(budget.delete_limit(category))
        elif option == "3":
            break

def parse_args():
    parser = argparse.ArgumentParser(description="Personal Budget Intelligence Tool")
    parser.add_argument("--report", action="store_true", help= "Enable report and exit")
    return parser.parse_args()

def menu():
    print("===== PERSONAL BUDGET INTELLIGENCE TOOL =====")
    print("1. Add transaction")
    print("2. Show balance")
    print("3. Monthly Comparison")
    print("4. Category vs Budget")
    print("5. Savings Rate")
    print("6. Overspend Forecast")
    print("7. Show spending breakdown")
    print("8. Export report")
    print("9. Manage budget limits")
    print("10. Delete transaction")
    print("0. Exit")
    print("==============================================")

def main():
    args = parse_args()
    transactions = load_transactions()
    budget = Budget()
    report = Report(transactions, budget)
    if args.report:
        report.export_txt(report_file)
        sys.exit("Bye")
    else:
        while True:
          menu()
          choice = input("Enter your choice (1-9): ").strip()
          if choice == "1":
              add_transaction(transactions)
          
          elif choice == "2":
               report.balance()
          
          elif choice == "3":
               print(report.compare_months())
          
          elif choice == "4":
               print(report.category_vs_budget())
          
          elif choice == "5":
               print(report.savings_rate())
          
          elif choice == "6":
               category = input("Which category will you like to get a forecast on: ")
               print(report.forecast(category))
          
          elif choice == "7":
              report.summary()
          
          elif choice == "8":
              report.export_txt(report_file)
          
          elif choice == "9":
              manage_budget(budget)
        
          elif choice == "10":
              delete_transaction(transactions)
          
          elif choice == "0":
              print("See you!")
              break
          
          else:
              print("Invalid choice, you can only choose between 0-9")
if __name__ == "__main__":
    main()
          


          


    


                


                
            

                
                


                

            



    