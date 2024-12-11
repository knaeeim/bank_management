from django.urls import path
from .views import *


urlpatterns = [
    path('deposite/', DepositeView.as_view(), name='deposite'),
    path('withdraw/', WithdrawMoney.as_view(), name='withdraw'),
    path('loan_request/', LoanRequestView.as_view(), name='loan_request'),
    path('loan_list/', LoanListView.as_view(), name='loan_list'),
    path('report/', TransactionReportView.as_view(), name='report'),
    path('loan/<int:loan_id>', PayLoanView.as_view(), name='pay_loan'),
    path('transfer_money', TransferMoneyView.as_view(), name='transfer_money'),
]