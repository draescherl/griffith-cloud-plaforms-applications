import random

import google.oauth2.id_token
from flask import Flask, render_template, request, redirect
from google.auth.transport import requests
from google.cloud import datastore
from google.oauth2 import service_account

app = Flask(__name__)
credentials = service_account.Credentials.from_service_account_file("gcp-creds.json")
datastore_client = datastore.Client(credentials=credentials)
firebase_request_adapter = requests.Request()


def store_time(email, dt):
    entity = datastore.Entity(key=datastore_client.key('User', email, 'visit'))
    entity.update({'timestamp': dt})
    datastore_client.put(entity)


def fetch_times(email, limit):
    ancestor_key = datastore_client.key('User', email)
    query = datastore_client.query(kind='visit', ancestor=ancestor_key)
    query.order = ['-timestamp']
    times = query.fetch(limit=limit)
    return times


def create_address(address1, address2, address3, address4):
    # 63 bit random number that will server as the key for this address object
    # not sure why the datastore doesn't like 64 bit numbers
    id = random.getrandbits(63)
    entity_key = datastore_client.key('Address', id)
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'address1': address1,
        'address2': address2,
        'address3': address3,
        'address4': address4
    })
    datastore_client.put(entity)
    return id


def add_address_to_user(user_info, id):
    address_keys = user_info['address_list']
    address_keys.append(id)
    user_info.update({
        'address_list': address_keys
    })
    datastore_client.put(user_info)


def delete_address(claims, id):
    user_info = retrieve_user_info(claims)
    address_list_keys = user_info['address_list']
    address_key = datastore_client.key('Address', address_list_keys[id])
    datastore_client.delete(address_key)
    del address_list_keys[id]
    user_info.update({
        'address_list': address_list_keys
    })
    datastore_client.put(user_info)


def retrieve_addresses(user_info):
    # make key objects out of all the keys and retrieve them
    address_ids = user_info['address_list']
    address_keys = []
    for i in range(len(address_ids)):
        address_keys.append(datastore_client.key('Address', address_ids[i]))
    address_list = datastore_client.get_multi(address_keys)
    return address_list


def retrieve_user_info(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore_client.get(entity_key)
    return entity


def create_user_info(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'email': claims['email'],
        'address_list': []
    })
    datastore_client.put(entity)


def update_user_info(claims, new_string, new_int, new_float):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore_client.get(entity_key)
    entity.update({
        'string_value': new_string,
        'int_value': new_int,
        'float_value': new_float
    })
    datastore_client.put(entity)


@app.route('/edit-user-info', methods=['POST'])
def editUserInfo():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            new_string = request.form['string_update']
            new_int = request.form['int_update']
            new_float = request.form['float_update']
            update_user_info(claims, new_string, new_int, new_float)
        except ValueError as exc:
            error_message = str(exc)
    return redirect("/")


@app.route('/add-address', methods=['POST'])
def addAddress():
    id_token = request.cookies.get("token")
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user_info = retrieve_user_info(claims)
            id = create_address(request.form['address1'], request.form['address2'], request.form['address3'], request.form['address4'])
            add_address_to_user(user_info, id)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/delete-address/<int:id>', methods=['POST'])
def deleteAddressFromUser(id):
    id_token = request.cookies.get("token")
    error_message = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            delete_address(claims, id)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    addresses = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user_info = retrieve_user_info(claims)
            if user_info is None:
                create_user_info(claims)
                user_info = retrieve_user_info(claims)
            addresses = retrieve_addresses(user_info)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('index.html', user_data=claims, error_message=error_message, user_info=user_info, addresses=addresses)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
