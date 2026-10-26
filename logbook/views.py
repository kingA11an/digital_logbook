from django.shortcuts import render 

def home_view(request): 
    # add logic here later to check if the user is a Student or supervisor
    # and redirect them to their specific dashboard. For now, just show the home page.
    return render(request, 'home.html')