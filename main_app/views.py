from operator import indexOf
from queue import Empty
from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from dotenv import load_dotenv
from psycopg2 import Date
from .models import Event, Comment
import requests, os
from .models import Event, Comment, User_Avatar, User_Event
import uuid
import boto3

S3_BASE_URL = 'https://s3.us-east-2.amazonaws.com/'
BUCKET = 'catcollector-wawa'

# Create your views here.
def home(request):
    return render(request, 'index.html')

def signup(request):
    error_message = ''
    if request.method == 'POST':
        # This is how to create a 'user' form object
        # that includes the data from the browser
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # This will add the user to the database
            user = form.save()
            # This is how we log a user in via code
            login(request, user)
            return redirect('create_user')
        else:
            error_message = 'Invalid sign up - try again'
    # A bad POST or a GET request, so render signup.html with an empty form
    form = UserCreationForm()
    context = {'form': form, 'error_message': error_message}
    return render(request, 'registration/signup.html', context)

def events_index(request):
    events = Event.objects.all()
    return render(request, 'events/index.html', {'events': events})

def event_detail(request, event_id):
    event = Event.objects.get(id=event_id)
    return render(request, 'events/detail.html', {'event':event})

class EventCreate(CreateView):
    model = Event
    fields = '__all__'

def create_comment(request, event_id):
    event = Event.objects.get(id=event_id)
    comment = Comment.objects.create(user=request.user, event=event, content=request.POST.get('content', ''))
    return redirect('event_detail', event_id=event_id)

def delete_comment(request, event_id, comment_id):
    comment = Comment.objects.get(id=comment_id)
    comment.delete()
    return redirect('event_detail', event_id=event_id)

def search(request):
    load_dotenv()
    query = request.GET.get('q')
    key = os.getenv('ACCESS_TOKEN')
    r = requests.get(f'https://app.ticketmaster.com/discovery/v2/events.json?keyword={query}&apikey={key}')
    r_json = r.json()
    embed = r_json.get('_embedded', {})
    events = embed.get('events', [])
    print(events)
    for idx, event in enumerate(events): # transforms the json so that venues is accessible with . notation
        embed = event.get('_embedded')
        venues = embed.get('venues')
        events[idx]['venues'] = venues
    return render(request, 'events/search.html', {'events': events})

def user_detail(request):
    return render(request, 'user/detail.html')

def add_photo(request, user_id):
  # photo-file will be the "name" attribute on the <input type="file">
  photo_file = request.FILES.get('photo-file', None)
  user_bio = request.POST.get('bio', None)
  if photo_file:
    s3 = boto3.client('s3')
    # need a unique "key" for S3 / needs image file extension too
    key = uuid.uuid4().hex[:6] + photo_file.name[photo_file.name.rfind('.'):]
    # just in case something goes wrong
    try:
      s3.upload_fileobj(photo_file, BUCKET, key)
      #build the full url string
      url = f"{S3_BASE_URL}{BUCKET}/{key}"
      # we can assign to cat_id or cat (if you have a cat object)
      User_Avatar.objects.create(url=url, user_id=user_id, bio= user_bio)
      user = User_Avatar.objects.get(user_id= user_id)
      user.save()
      print(user.__dict__)
    except:
      print('An error occurred uploading to S3.')
  return redirect('/user')  

def going_event(request, event_id, user_id):
    user = User_Avatar.objects.get(user_id=user_id)
    event = Event.objects.get(id=event_id)
    try:
        event_user = User_Event.objects.get(user=user, event=event)
    except:
        user_event = User_Event.objects.create(user=user, event=event)
        user_event.save()
        print(user_event)
    # Event.objects.get(id=event_id).user_avatar.add(user_id)
    return redirect('/user')

# def ticketmaster_event(request, ticketmaster_id):
#     load_dotenv()
#     key = os.getenv('ACCESS_TOKEN')
#     r=requests.get(f'https://app.ticketmaster.com/discovery/v2/events.json?id={ticketmaster_id}&apikey={key}')
#     if r.status_code != 404:
#         r_json = r.json()
#         embed = r_json.get('_embedded', {})
#         events = embed.get('events', [])
#         if events:
#             the_event = events[0]
#             event = Event.objects.get_or_create(url_ticketmaster = ticketmaster_id, defaults={
#                 'event_name':the_event['name'],
#                 'event_type':the_event['type'],
#                 'location': the_event['_embedded']['venues'][0]['name'],
#                 'artist':'None',
#                 'image':'None',
#                 'description':'None',
#                 'date':'2022-05-03'})
#             return render(request, 'events/detail.html', {'event': event})
#         else:
#             return render(request, 'events/search.html', {'events': []})

def ticketmaster_create(request, event_id):
    load_dotenv()
    key = os.getenv('ACCESS_TOKEN')
    r = requests.get(f'https://app.ticketmaster.com/discovery/v2/events.json?id={event_id}&apikey={key}')
    r_json = r.json()
    print(r_json)
    embed = r_json.get('_embedded', {})
    events = embed.get('events', [])
    the_event = events[0]
    event = Event.objects.get_or_create(url_ticketmaster = event_id, defaults={
                'event_name':the_event['name'],
                'event_type':the_event['type'],
                'location': the_event['_embedded']['venues'][0]['name'],
                'artist':'None',
                'image':'None',
                'description':'None',
                'date':'2022-05-03'})
    
    return redirect(f'/events/{Event.objects.get(url_ticketmaster=event_id).id}')    

def create_user(request):
    return render(request, 'user/create.html')

def add_bio(request, user_id):
    user = User_Avatar.objects.get(user_id=user_id)
    user.bio = request.GET.get('bio')
    user.save()
    return redirect('/user')

def not_going(request, user_id, event_id):
    user = User_Avatar.objects.get(user_id=user_id)
    event = Event.objects.get(id=event_id)
    delete_connect = User_Event.objects.get(user=user, event=event)
    delete_connect.delete()
    return redirect('/user')

