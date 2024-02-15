from pymongo import MongoClient
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session, url_for
from flask import Flask, render_template, request, flash, redirect, url_for

from flask_pymongo import PyMongo
import hashlib
import os
from bson import ObjectId
import bson
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  
client = MongoClient('mongodb://localhost:27017/')
db = client['eve_management'] 
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MONGO_URI'] = "mongodb://localhost:27017/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

@app.route('/',  methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        print(email)
        print(password)
        print(role)

        # Query the appropriate collection based on the selected role
        collection = db[role]
        # Check if the user exists in the collection
        user = collection.find_one({'email': email})
        if user and bcrypt.check_password_hash(user['password'], password):
            print("here")
            # Authentication successful, store user information in session
            session['user'] = {'email': user['email'], 'role': role}

            # Redirect to the appropriate dashboard based on the role
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'organizers':
                return redirect(url_for('organizer_dashboard'))
            elif role == 'attendees':
                return redirect(url_for('attendees_dashboard'))

    return render_template('login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    organizers=db['temp']
    attendees=db['attendees']


    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first-name')
        last_name = request.form.get('last-name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        dob = request.form.get('dob')
        role = request.form.get('role')
        password = request.form.get('password')

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create a user object
        user = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'address': address,
            'dob': dob,
            'role': role,
            'password': hashed_password
        }

        # Insert user into the respective collection
        if role == 'organizer':
            organizers.insert_one(user)
        elif role == 'attendee':
            attendees.insert_one(user)

        return redirect('/')

    return render_template('register.html')  # Create a template for the registration form


@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/organizer_dashboard')
def organizer_dashboard():
    return render_template('organizer_dashboard.html')

@app.route('/attendees_dashboard')
def attendees_dashboard():
    return render_template('attendees_dashboard.html')


@app.route('/admin_venue')
def admin_venue():
    return render_template('admin_venues.html')


@app.route('/org_approval')
def org_approval():
    orgs_collection = db['temp']
    org=orgs_collection.find()
    return render_template('manage_orgs.html',organizations=org)

@app.route('/admin_add_event')
def admin_add_event():
    venues_collection = db['venues']
    venues=venues_collection.find()
    return render_template('create_event.html',venues=venues)


@app.route('/approve_organization/<organization_id>', methods=['POST'])
def approve_organization(organization_id):
    orgs_collection = db['temp']
    org = orgs_collection.find_one({"_id": ObjectId(organization_id)})

    org_orgs = db['organizers']
    org_orgs.insert_one(org)


    orgs_collection.delete_one({"_id": ObjectId(organization_id)})

    return redirect(url_for('admin_dashboard'))


@app.route('/reject_organization/<organization_id>', methods=['POST'])
def reject_organization(organization_id):
    orgs_collection = db['temp']
    orgs_collection.delete_one({"_id": ObjectId(organization_id)})
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_add_venue')
def admin_add_venue():
    return render_template('admin_add_venue.html')

@app.route('/submit-venue', methods=['POST'])
def submit_venue():
    venues_collection = db['venues']
    if request.method == 'POST':
        # Extract form data
        venue_name = request.form['venueName']
        amenities = request.form.getlist('amenities')
        address = request.form['address']
        price = request.form['price']

        # Insert data into MongoDB
        venue_data = {
            'venue_name': venue_name,
            'amenities': amenities,
            'address': address,
            'price': price
        }

        venues_collection.insert_one(venue_data)

        return redirect('/admin_venue')
    

@app.route('/submit-event', methods=['POST'])
def submit_event():
    if request.method == 'POST':
        event_name = request.form['eventName']
        event_type = request.form['eventType']
        venue = request.form['venue']
        event_description = request.form['eventDescription']
        date = request.form['eventDate']
        user_email = username = session['user']['email']

        if event_type == 'paid':
            capacity = request.form.get('capacity')
            ticket_price = request.form.get('ticketPrice')
        elif event_type == 'unpaid':
            capacity = request.form.get('capacity')
            ticket_price = 0
        else:
            capacity = 0
            ticket_price = 0

        events_collection = db["events"] 
        event_data = {
            "user_email":user_email,
            'event_name': event_name,
            'event_type': event_type,
            'venue': venue,
            "date": date,
            'event_description': event_description,
            'capacity': int(capacity),
            'org_capacity': int(capacity),
            'ticket_price': ticket_price,
            'status':"pending",
        }

        events_collection.insert_one(event_data)

        return redirect(url_for('organizer_dashboard'))

    
@app.route('/admin_view_venues')
def admin_view_venues():
    venues_collection = db['venues']
    all_venues = venues_collection.find()
    return render_template('admin_view_venues.html', venues=all_venues)

@app.route('/admin_view_events')
def admin_view_events():
    events_collection = db['events']
    events = events_collection.find()
    return render_template('admin_view_events.html', events=events)

@app.route('/edit_event/<event_id>')
def edit_event(event_id):
    events_collection = db['events']
    events = events_collection.find_one({"_id": ObjectId(event_id)})
    venues_collection = db['venues']
    venues = venues_collection.find()
    return render_template('edit_event.html', event=events,venues=venues)

@app.route('/org_view_events')
def org_view_events():
    events_collection = db['events']
    user_email = username = session['user']['email']
    events = events_collection.find({"user_email":user_email})
    return render_template('view_event_table.html', events=events)


@app.route('/org_view_active')
def org_view_active():
    events_collection = db['events']
    user_email = username = session['user']['email']
    events = events_collection.find({"user_email":user_email})
    return render_template('view_active.html', events=events)


@app.route('/cancel_event/<event_id>', methods=['GET'])
def cancel_event(event_id):
    events_collection = db['events']
    print("yee")
    print(event_id)
    obj_id = ObjectId(event_id)
    events_collection.update_one({"_id": obj_id}, {"$set": {"status": "cancelled"}})
    return redirect('org_view_events')

@app.route('/delete_event/<event_id>', methods=['GET'])
def delete_event(event_id):
    events_collection = db['events']
    events_collection.delete_one({"_id": ObjectId(event_id)})
    return redirect('org_view_events')


@app.route('/view_attendee/<event_name>', methods=['GET'])
def view_attendee(event_name):
    books_collection = db['booking']
    print(event_name)
    booking_instances=books_collection.find({"event_name": event_name})
    return render_template('org_attendee.html', booking_instances=booking_instances)


@app.route('/approve_event/<event_id>', methods=['GET'])
def approve_event(event_id):
    events_collection = db['events']
    obj_id = ObjectId(event_id)
    events_collection.update_one({"_id": obj_id}, {"$set": {"status": "approved"}})
    return redirect(url_for('admin_view_events'))


@app.route('/reject_event/<event_id>', methods=['GET'])
def reject_event(event_id):
    events_collection = db['events']
    obj_id = ObjectId(event_id)
    events_collection.update_one({"_id": obj_id}, {"$set": {"status": "rejected"}})
    return redirect(url_for('admin_view_events'))




@app.route('/view_events')
def view_events():
    events_collection = db['events']
    events = events_collection.find({"status": "approved"})
    return render_template('view_events.html', events=events)


@app.route('/admin_payments')
def admin_payments():
    events_collection = db['events']
    venue_collection = db['venues']
    events = events_collection.find({"status": "approved"})
    event_data = []
    for event in events:
         event_name = event["event_name"]
         price = event["ticket_price"]
         capacity = event["capacity"]
         evetype=event["event_type"]
         org_count=event["org_capacity"]
         sold=(int(org_count)-int(capacity))
         pp=event["ticket_price"]
         total_amount=(int(pp)*int(sold))
         venue_name = event["venue"]
         venue = venue_collection.find_one({"venue_name": venue_name})
         percent=int(venue['price'])
         percent_of_total = (percent / 100) * total_amount
         adm_price=percent_of_total
         event_data.append({
         "event_name": event_name,
         "evetype":evetype,
         "pp": pp,
         "sold":sold,
         "profit":total_amount,
         "adm_price": adm_price
         })
    print(event_data)
    return render_template('admin_payments.html',event_data=event_data)


@app.route('/org_profit')
def org_payments():
    events_collection = db['events']
    venue_collection = db['venues']
    user_email = username = session['user']['email']
    events = events_collection.find({"user_email": user_email, "status": "approved"})
    event_data = []
    for event in events:
         event_name = event["event_name"]
         price = event["ticket_price"]
         capacity = event["capacity"]
         evetype=event["event_type"]
         org_count=event["org_capacity"]
         sold=(int(org_count)-int(capacity))
         pp=event["ticket_price"]
         total_amount=(int(pp)*int(sold))
         venue_name = event["venue"]
         venue = venue_collection.find_one({"venue_name": venue_name})
         percent=int(venue['price'])
         percent_of_total = (percent / 100) * total_amount
         adm_price=percent_of_total
         event_data.append({
         "event_name": event_name,
         "evetype":evetype,
         "pp": pp,
         "sold":sold,
         "profit":total_amount,
         "adm_price": adm_price
         })
    print(event_data)
    return render_template('org_payments.html',event_data=event_data)


from bson import ObjectId

@app.route('/event/<event_id>')
def show_event(event_id):
    events_collection = db['events']
    event = events_collection.find_one({"_id": ObjectId(event_id)})
    location=event['venue']
    venues_collection = db['venues']

    all_venues = venues_collection.find_one({"venue_name": location})
    all_event_document = {
    "event_name": event["event_name"],
    "event_type": event["event_type"],
    "venue": {
        "venue_name": all_venues["venue_name"],
        "amenities": all_venues["amenities"],
        "address": all_venues["address"],
        "price": all_venues["price"]
    },
    "event_description": event["event_description"],
    "capacity": event["capacity"],
    "ticket_price": event["ticket_price"]


}
    return render_template('event_detail.html', all_event_document=all_event_document)

@app.route('/book-tickets', methods=['POST'])
def book_tickets():
    if request.method == 'POST':
        event_name = request.form.get('event_name')
        venue_name = request.form.get('venue_name')
    return render_template('payment.html',event_name=event_name,venue_name=venue_name)

@app.route('/generate_tickets', methods=['POST'])
def generate_tickets():
    card_number = request.form.get('cardNumber')
    card_holder_name = request.form.get('cardHolderName')
    cvv = request.form.get('cvv')
    expiration_date = request.form.get('expirationDate')
    event_name = request.form.get('event')
    venue_name = request.form.get('venue')

    # Retrieve user email from the session
    user_email = username = session['user']['email']

    # Retrieve event data
    events_collection = db['events']
    event = events_collection.find_one({"event_name": event_name})
    event_type = event['event_type']
    date=event["date"]
    print(date)

    # Retrieve venue data
    venues_collection = db['venues']
    venue = venues_collection.find_one({"venue_name": venue_name})
    amenities = venue['amenities']
    venue_address = venue['address']
    venue_price = venue['price']

    

    if event_type=='paid':
        price=event["ticket_price"]
    else:
        price=0

    if event_type=='paid' or event_type=='unpaid':
        ticket_num=event["capacity"]
        events_collection.update_one({"event_name": event_name}, {"$inc": {"capacity": -1}})

    booking_data = {
        "user_email": user_email,
        "ticket_num": ticket_num,
        "price": price,
        "date":date,
        "event_name": event_name,
        "event_type": event_type,
        "venue_name": venue_name,
        "address": venue_address,
        'status' : "active"
    }

    booking_collection = db['booking']
    booking_collection.insert_one(booking_data)
    payment_data = {
        "user_email": user_email,
        "ticket_num":ticket_num,
        "price":price,
        "date":date,
        "event_name": event_name,
        "event_type": event_type,
        "venue_name": venue_name,
        "address": venue_address,
        "card_number": card_number,
        "card_holder_name": card_holder_name,
        "cvv": cvv,
        "expiration_date": expiration_date
        }
    
    payment_collection = db['payment']
    payment_collection.insert_one(payment_data)
    return render_template('bill.html',booking_data=booking_data)



@app.route('/cancel_ticket/<booking_id>', methods=['GET','POST'])
def cancel_ticket(booking_id):
    bookings_collection = db['booking']
    events_collection = db['events']

    booking=bookings_collection.find_one({"_id": ObjectId(booking_id)})
    even=booking["event_name"]
    events_collection.update_one(
    {"event_name": even},
    {"$inc": {"capacity": 1}}
        )
    bookings_collection.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "Cancelled"}})
    return redirect('/view_history')


@app.route('/bill/<booking_id>', methods=['GET','POST'])
def bill(booking_id):
    bookings_collection = db['booking']
    booking_data=bookings_collection.find_one({"_id": ObjectId(booking_id)})
    return render_template('bill.html',booking_data=booking_data)



@app.route('/edit_venue/<venue_id>', methods=['GET'])
def edit_venue(venue_id):
    venues_collection = db['venues']
    venue = venues_collection.find_one({"_id": ObjectId(venue_id)})
    return render_template('edit_venue.html', venue=venue)


@app.route('/update_venue/<venue_id>', methods=['POST'])
def update_venue(venue_id):
    venues_collection = db['venues']
    if request.method == 'POST':
        new_venue_name = request.form['new_venue_name']
        new_amenities = request.form.getlist('new_amenities[]')
        new_address = request.form['new_address']
        new_price = request.form['new_price']
        print("heree")
        venues_collection.update_one(
            {"_id": ObjectId(venue_id)},
            {"$set": {
                "venue_name": new_venue_name,
                "amenities": new_amenities,
                "address": new_address,
                "price": new_price
            }}
        )
        return redirect('/admin_view_venues')

# Delete Venue Endpoint
@app.route('/delete_venue/<venue_id>', methods=['POST'])
def delete_venue(venue_id):
    venues_collection = db['venues']
    venues_collection.delete_one({"_id": ObjectId(venue_id)})
    return redirect('/admin_view_venues')

@app.route('/view_history')
def view_history():
    user_email = username = session['user']['email']
    booking_collection = db['booking']
    booking_instances = booking_collection.find({"user_email": user_email})
    return render_template('attendee_view_table.html', booking_instances=booking_instances)

@app.route('/user_track_events')
def user_track_events():
    booking_collection = db['events']
    booking_instances = booking_collection.find()
    return render_template('track_event.html', events=booking_instances)






@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()

    # Redirect to the home page or login page
    return redirect(url_for('index'))
if __name__ == '__main__':
    app.run(debug=True)

if __name__ == '__main__':
    app.run(debug=True)
       

#flask --app app.py --debug run 