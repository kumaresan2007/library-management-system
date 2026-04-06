from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from .forms import LoginForm


def login_view(request):
    # If already logged in → go to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                # Role-based redirect
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'staff':
                    return redirect('staff_dashboard')
                else:
                    return redirect('member_dashboard')

            else:
                messages.error(request, 'Invalid username or password')

    else:
        form = LoginForm()

    return render(request, 'library/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')