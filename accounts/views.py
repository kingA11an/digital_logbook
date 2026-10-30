from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout

def login_view(request):
    # STEP 1: Handle Form Submission (POST)
    if request.method == 'POST':
        # Grab the exact names we used in the HTML input fields
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check if the credentials match a real user in the database
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Generate the session key (Log them in)
            login(request, user)
            
            # Role-Based Redirect Engine
            if user.role == 'STUDENT':
                # We will build this dashboard view next! For now, send them to home.
                return redirect('logbook:student_dashboard') 
            elif user.role == 'FIELD_SUPERVISOR':
                return redirect('logbook:home')
            elif user.role == 'UNI_SUPERVISOR':
                return redirect('logbook:home')
            else:
                return redirect('logbook:home') # Admin fallback
        else:
            # Login failed: Send the form back with an error trigger
            return render(request, 'login.html', {'error_message': True})
            
    # STEP 2: Handle Page Visit (GET)
    # If they just navigated to the URL, show the blank login form
    return render(request, 'login.html')

def logout_view(request):
    # This destroys the user's session
    logout(request)
    # Send them back to the home page after logging out
    return redirect('logbook:home')