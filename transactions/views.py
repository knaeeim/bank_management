from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView
from django.views import View
from .models import Transaction, BankSettings
from .forms import *
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .constants import DEPOSIT, WITHDRAWAL, LOAN, LOAN_PAID, TRANSFER_IN, TRANSFER_OUT
from django.contrib import messages
from datetime import datetime
from django.db.models import Sum
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string

# Create your views here.

def send_transaction_email(user, amount, subject, template):
    mail_subject = 'Deposite Confirmation'
    message = render_to_string(template, { 
        'user' : user, 
        'amount' : amount, 
    })
    to_email = user.email
    send_mail = EmailMultiAlternatives(subject, '', to=[to_email])
    send_mail.attach_alternative(message, 'text/html')
    send_mail.send()


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    template_name = 'transaction_form.html'
    form_class = TransactionForm
    title = ''
    success_url = reverse_lazy('report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account' : self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title' : self.title
        })
        return context
    
class DepositeView(TransactionCreateView):
    form_class = DepositeForm
    title = 'Deposite BDT'

    def get_initial(self):
        initial = super().get_initial()
        initial.update({
            'transaction_type' : DEPOSIT
        })
        return initial
    
    def form_valid(self, form):
        print(self.request.POST)
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        account.balance += amount
        account.save(update_fields = ['balance'])
        messages.success(self.request, f'BDT {amount} has been successfully deposited to your account')
        send_transaction_email(self.request.user, amount, 'Deposite Confirmation', 'deposite_email.html')
        return super().form_valid(form)

class WithdrawMoney(TransactionCreateView):
    form_class = WithdrawForm
    title = 'Withdraw BDT'

    def dispatch(self, request, *args, **kwargs):
        # Dynamically check if the bank is bankrupt
        bank_settings = BankSettings.objects.first()
        if bank_settings and bank_settings.is_bankrupt:
            messages.error(request, "The bank is currently bankrupt. WithDrawn are not allowed.")
            return redirect('home')  # Redirect to a safe page
        return super().dispatch(request, *args, **kwargs)
    

    def get_initial(self):
        initial = super().get_initial()
        initial.update({
            'transaction_type' : WITHDRAWAL
        })
        return initial
    
    def form_valid(self, form):
        amount = form.cleaned_data['amount']
        account = self.request.user.account
        account.balance -= amount
        account.save(update_fields = ['balance'])
        messages.success(self.request, f'BDT {amount} has been successfully withdarw from your account')
        send_transaction_email(self.request.user, amount, 'Withdrawl Confirmation', 'withdrawal.html')
        return super().form_valid(form)
    
class LoanRequestView(TransactionCreateView):
    form_class = LoanRequestForm
    title = 'Requesting for Loan'

    def dispatch(self, request, *args, **kwargs):
        # Dynamically check if the bank is bankrupt
        bank_settings = BankSettings.objects.first()
        if bank_settings and bank_settings.is_bankrupt:
            messages.error(request, "The bank is currently bankrupt. Loan Request View not allowed.")
            return redirect('home')  # Redirect to a safe page
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update({
            'transaction_type' : LOAN
        })
        return initial
    
    def form_valid(self, form):
        amount = form.cleaned_data['amount']
        current_loan_count = Transaction.objects.filter(account = self.request.user.account, transaction_type = LOAN, loan_approve = True).count()
        if current_loan_count >= 3:
            messages.error(self.request, 'You have already 3 active loans, first return them to get another loan')
            return super().form_invalid(form)
        messages.success(self.request, f'BDT {amount} of loan Request has been sent to the bank authority')
        send_transaction_email(self.request.user, amount, 'Loan Application Status', 'loan_application.html')
        return super().form_valid(form)

class TransactionReportView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'transaction_report.html'
    balance = 0

    def get_queryset(self):
        queryset = super().get_queryset().filter(account = self.request.user.account)

        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

            queryset = queryset.filter(timestamp__date__gte = start_date, timestamp__date__lte = end_date)

            self.balance =  self.balance = queryset.aggregate(Sum('amount'))['amount__sum'] or 0
        else:
            self.balance = self.request.user.account.balance

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account' : self.request.user.account,
            'curr_balance' : self.balance
        })
        return context


class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)

        if loan.loan_approve:
            user_account = loan.account
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.transaction_type = LOAN_PAID
                loan.save()
                messages.success(request, 'Loan has been successfully paid')
                send_transaction_email(self.request.user, loan.amount, 'Loan Repayment Confirmation', 'loan_confirmation.html')
                return redirect('report')
            else:
                messages.error(request, 'You do not have sufficient balance to pay the loan')
                return redirect('report')


class LoanListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'loan_request.html'
    context_object_name = 'loans'

    def get_queryset(self):
        user_account = self.request.user.account
        queryset = super().get_queryset().filter(account = user_account, transaction_type = LOAN)
        return queryset


class TransferMoneyView(LoginRequiredMixin, View):
    template_name = 'transfer_money.html'
    title = "Transfer Money"

    def dispatch(self, request, *args, **kwargs):
        # Dynamically check if the bank is bankrupt
        bank_settings = BankSettings.objects.first()
        if bank_settings and bank_settings.is_bankrupt:
            messages.error(request, "The bank is currently bankrupt. Transfer Money is not allowed.")
            return redirect('home')  # Redirect to a safe page
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update({
            'transaction_type' : TRANSFER_OUT
        })

    def get(self, request):
        form = TransferMoneyForm(sender_account = request.user.account)
        return render(request, self.template_name, {'form' : form, 'title' : self.title})
    
    def post(self, request):
        form = TransferMoneyForm(request.POST, sender_account = request.user.account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Money has been successfully transferred')
            receiver_account = form.receiver_account
            send_transaction_email(request.user, form.cleaned_data['amount'], "Transfer Confirmation", 'transfer_email.html')
            send_transaction_email(receiver_account.user, form.cleaned_data['amount'], "Transfer Confirmation", 'transfer_email.html')
            return redirect('report')
        return render(request, self.template_name, {'form' : form, 'title' : self.title})


