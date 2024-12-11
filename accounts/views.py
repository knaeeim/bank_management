from django.shortcuts import render, redirect
from django.views.generic import FormView
from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from .forms import UserRegistrationForm, UserUpdateForm, PasswordChangeForm
from django.contrib.auth import login, logout
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from transactions.views import send_transaction_email
from django.contrib import messages


# Create your views here.
class UserRegistrationView(FormView):
    template_name = 'accounts/user_registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile_update')

    def form_valid(self, form):
        print(form.cleaned_data)
        user = form.save()
        login(self.request, user)
        print(user)
        return super().form_valid(form)
    
class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'
    
    def get_success_url(self):
        return reverse_lazy('home')
    
def user_logout(request):
    logout(request)
    return redirect('login')


class UserUpdateView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        form = UserUpdateForm(instance = request.user)
        return render(request, self.template_name, {'form' : form})
    
    def post(self, request):
        print("received data ", request.POST)
        form = UserUpdateForm(request.POST, instance = request.user)
        # print(form)
        if form.is_valid():
            print("form is valid")
            form.save()
            print(form.cleaned_data)
            return redirect('profile_update')
        return render(request, self.template_name, {'form' : form})
    
    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

class ChangePassword(LoginRequiredMixin, View):
    template_name = 'accounts/change_pass.html'
    model = User
    form_class = PasswordChangeForm

    def get(self, request):
        form = self.form_class(user = request.user)
        return render(request, self.template_name, {'form' : form})
    
    def post(self, request):
        form = self.form_class(user = request.user, data = request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password has been successfully changed')
            send_transaction_email(request.user, 0, 'Password Change Confirmation', 'accounts/password_email.html')
            return redirect('profile_update')
        return render(request, self.template_name, {'form' : form})
