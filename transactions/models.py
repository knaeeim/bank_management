from django.db import models
from accounts.models import UserBankAccount
from .constants import TRANSACTION_TYPE

# Create your models here.
class Transaction(models.Model):
    account = models.ForeignKey(UserBankAccount, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after_transaction = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.IntegerField(choices=TRANSACTION_TYPE, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    loan_approve = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

class BankSettings(models.Model):
    is_bankrupt = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.is_bankrupt}"