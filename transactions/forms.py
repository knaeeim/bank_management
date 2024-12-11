from django import forms
from .models import Transaction
from accounts.models import UserBankAccount
from datetime import datetime
from .constants import TRANSFER_OUT, TRANSFER_IN

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'transaction_type']

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super().__init__(*args, **kwargs)
        self.fields['transaction_type'].disabled = True # This will disable the transaction_type field
        self.fields['transaction_type'].widget = forms.HiddenInput() # This will hide the transaction_type field

    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save()
    

class DepositeForm(TransactionForm):
    def clean_amount(self):
        min_deposite_amount = 500
        amount = self.cleaned_data['amount']
        if amount < min_deposite_amount:
            raise forms.ValidationError(f"Minimum deposite amount is BDT {min_deposite_amount}")
        return amount
    

class WithdrawForm(TransactionForm):
    def clean_amount(self):
        account = self.account
        min_withraw = 500
        max_withdraw = 500000
        balance = account.balance
        amount = self.cleaned_data['amount']

        if amount < min_withraw:
            raise forms.ValidationError(f"Minimum withdraw amount is BDT {min_withraw}")
        
        if amount > max_withdraw:
            raise forms.ValidationError(f'Maximum withdraw amount is BDT {max_withdraw}')
        
        if balance < amount:
            raise forms.ValidationError("Insufficient balance, You have only BDT {balance} in your account")
        
        return amount
    
class LoanRequestForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data['amount']

        return amount
    
class TransferMoneyForm(forms.Form):
    account_no = forms.IntegerField()
    amount = forms.DecimalField(max_digits=10, decimal_places=2)

    def __init__(self, *args, **kwargs):
        self.sender_account = kwargs.pop('sender_account')
        super().__init__(*args, **kwargs)
        self.receiver_account = None

    def clean_account_no(self):
        account_no = self.cleaned_data['account_no']

        try:
            receiver_account = UserBankAccount.objects.get(account_no = account_no)
        except UserBankAccount.DoesNotExist:
            raise forms.ValidationError("Invalid account number")
        
        if receiver_account == self.sender_account:
            raise forms.ValidationError("You can't transfer money to your own account")
        
        self.receiver_account = receiver_account
        return account_no
    
    def clean_amount(self):
        min_transfer = 500
        amount = self.cleaned_data['amount']

        if amount < min_transfer:
            raise forms.ValidationError(f"Minimum transfer amount is BDT {min_transfer}")
        
        max_transfer = 500000

        if amount > max_transfer:
            raise forms.ValidationError(f"Maximum transfer amount is BDT {max_transfer}")
        
        if self.sender_account.balance < amount:
            raise forms.ValidationError("Insufficient balance")
        
        return amount
    
    def save(self):
        amount = self.cleaned_data['amount']

        self.sender_account.balance -= self.cleaned_data['amount']
        self.receiver_account.balance += self.cleaned_data['amount']
        self.sender_account.save(update_fields = ['balance'])
        self.receiver_account.save(update_fields = ['balance'])

        Transaction.objects.create(
            account=self.sender_account,
            amount=-amount,  # Deducted amount as negative
            transaction_type= TRANSFER_OUT,
            balance_after_transaction = self.sender_account.balance,
            # description=f'Transfer to {self.receiver_account.account_no}',
            timestamp=datetime.now(),
        )

        # Create transaction for receiver
        Transaction.objects.create(
            account=self.receiver_account,
            amount=amount,  # Added amount as positive
            transaction_type= TRANSFER_IN,
            balance_after_transaction = self.receiver_account.balance,
            # description=f'Transfer from {self.sender_account.account_no}',
            timestamp=datetime.now(),
        )