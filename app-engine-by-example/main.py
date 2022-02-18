import random

import google.oauth2.id_token
from flask import Flask, render_template, request, redirect, Response
from google.auth.transport import requests
from google.cloud import datastore, storage
from google.oauth2 import service_account

import local_constants

app = Flask(__name__)
credentials = service_account.Credentials.from_service_account_file("gcp-creds.json")
datastore_client = datastore.Client(credentials=credentials)
storage_client = storage.Client(credentials=credentials)
firebase_request_adapter = requests.Request()


def create_address(address1, address2, address3, address4):
    # 63 bit random number that will server as the key for this address object
    # not sure why the datastore doesn't like 64-bit numbers
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
    entity.update({'email': claims['email']})
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


def createDummyData(number):
    entity_key = datastore_client.key('DummyData', number)
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'number': number,
        'squared': number ** 2,
        'cubed': number ** 3
    })
    return entity


def createDummyData2(name, id, boolean):
    entity_key = datastore_client.key('DummyData', id)
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'name': name,
        'id': id,
        'boolean': boolean
    })
    return entity


def blobList(prefix):
    #storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    return storage_client.list_blobs(local_constants.PROJECT_STORAGE_BUCKET, prefix=prefix)


def addDirectory(directory_name):
    #storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(directory_name)
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')


def addFile(file):
    #storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(file.filename)
    blob.upload_from_file(file)


def downloadBlob(filename):
    #storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(filename)
    return blob.download_as_bytes()


@app.route('/add-directory', methods=['POST'])
def addDirectoryHandler():
    id_token = request.cookies.get('token')
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            directory_name = request.form['dir_name']
            if directory_name == '' or directory_name[len(directory_name) - 1] != '/':
                return redirect('/')
            user_info = retrieve_user_info(claims)
            addDirectory(directory_name)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/upload-file', methods=['POST'])
def fileUploadHandler():
    id_token = request.cookies.get('token')
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            file = request.files['file_name']
            if file.filename == '':
                return redirect('/')
            user_info = retrieve_user_info(claims)
            addFile(file)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/download-file/<string:filename>', methods=['POST'])
def downloadFile(filename):
    id_token = request.cookies.get('token')
    error_message = None
    claims = None
    user_info = None
    file_bytes = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as exc:
            error_message = str(exc)
    return Response(downloadBlob(filename), mimetype='application/octet-stream')


@app.route('/multi-add', methods=['POST'])
def multiAdd():
    id_token = request.cookies.get("token")
    error_message = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            entity_1 = createDummyData(1)
            entity_2 = createDummyData(2)
            entity_3 = createDummyData(3)
            entity_4 = createDummyData(4)
            datastore_client.put_multi([
                entity_1,
                entity_2,
                entity_3,
                entity_4
            ])
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/batch-add', methods=['POST'])
def batchAdd():
    id_token = request.cookies.get("token")
    error_message = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            entity_5 = createDummyData(5)
            entity_6 = createDummyData(6)
            entity_7 = createDummyData(7)
            entity_8 = createDummyData(8)
            batch = datastore_client.batch()
            with batch:
                batch.put(entity_5)
                batch.put(entity_6)
                batch.put(entity_7)
                batch.put(entity_8)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/transaction-add', methods=['POST'])
def transactionAdd():
    id_token = request.cookies.get('token')
    error_message = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            entity_9 = createDummyData(9)
            entity_10 = createDummyData(10)
            entity_11 = createDummyData(11)
            entity_12 = createDummyData(12)
            transaction = datastore_client.transaction()
            with transaction:
                transaction.put(entity_9)
                transaction.put(entity_10)
                transaction.put(entity_11)
                transaction.put(entity_12)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/multi-delete', methods=['POST'])
def multiDelete():
    id_token = request.cookies.get("token")
    error_message = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            entity_1_key = datastore_client.key('DummyData', 1)
            entity_2_key = datastore_client.key('DummyData', 2)
            entity_3_key = datastore_client.key('DummyData', 3)
            entity_4_key = datastore_client.key('DummyData', 4)
            datastore_client.delete_multi([
                entity_1_key,
                entity_2_key,
                entity_3_key,
                entity_4_key
            ])
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/batch-delete', methods=['POST'])
def batchDelete():
    id_token = request.cookies.get('token')
    error_message = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            entity_5_key = datastore_client.key('DummyData', 5)
            entity_6_key = datastore_client.key('DummyData', 6)
            entity_7_key = datastore_client.key('DummyData', 7)
            entity_8_key = datastore_client.key('DummyData', 8)
            batch = datastore_client.batch()
            with batch:
                batch.delete(entity_5_key)
                batch.delete(entity_6_key)
                batch.delete(entity_7_key)
                batch.delete(entity_8_key)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/transaction-delete', methods=['POST'])
def transactionDelete():
    id_token = request.cookies.get('token')
    error_message = None
    # verify the claims of the user and if they are verified then request deletion of the given address
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            # generate four entities, so we can store them in the datastore
            entity_9_key = datastore_client.key('DummyData', 9)
            entity_10_key = datastore_client.key('DummyData', 10)
            entity_11_key = datastore_client.key('DummyData', 11)
            entity_12_key = datastore_client.key('DummyData', 12)
            # persist the entities to the datastore using transaction delete
            transaction = datastore_client.transaction()
            with transaction:
                transaction.delete(entity_9_key)
                transaction.delete(entity_10_key)
                transaction.delete(entity_11_key)
                transaction.delete(entity_12_key)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


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
            id = create_address(request.form['address1'], request.form['address2'], request.form['address3'],
                                request.form['address4'])
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


@app.route('/initialise-dummy-data', methods=['POST'])
def initialiseDummyData():
    entity_1 = createDummyData2("foo", 1, True)
    entity_2 = createDummyData2("bar", 2, False)
    entity_3 = createDummyData2("baz", 3, False)
    entity_4 = createDummyData2("wookie", 4, True)
    datastore_client.put_multi([
        entity_1,
        entity_2,
        entity_3,
        entity_4
    ])
    return redirect('/')


@app.route('/pull-entity-by-id', methods=['POST'])
def pullEntityById():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            if request.form['id'] == '':
                return redirect('/')
            id = int(request.form['id'])
            query = datastore_client.query(kind='DummyData')
            query.add_filter('id', '=', id)
            result = query.fetch()
        except ValueError as exc:
            error_message = str(exc)
    return render_template('index.html', user_data=claims, error_message=error_message, data=result)


@app.route('/pull-entity-by-name', methods=['POST'])
def pullEntityByName():
    id_token = request.cookies.get('token')
    error_message = None
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            if request.form['name'] == '':
                return redirect('/')
            name = request.form['name']
            query = datastore_client.query(kind='DummyData')
            query.add_filter('name', '=', name)
            result = query.fetch()
        except ValueError as exc:
            error_message = str(exc)
    return render_template('index.html', user_data=claims, error_message=error_message, data=result)


@app.route('/query-multiple-attribs', methods=['POST'])
def queryMultipleAttribs():
    id_token = request.cookies.get('token')
    error_message = None
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            query = datastore_client.query(kind='DummyData')
            query.add_filter('id', '<', 4)
            query.add_filter('boolean', '=', True)
            result = query.fetch()
        except ValueError as exc:
            str(exc)
    return render_template('index.html', user_data=claims, error_message=error_message, data=result)


@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    file_list = []
    directory_list = []
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user_info = retrieve_user_info(claims)
            if user_info is None:
                create_user_info(claims)
                user_info = retrieve_user_info(claims)
            blob_list = blobList(None)
            for i in blob_list:
                if i.name[len(i.name) - 1] == '/':
                    directory_list.append(i)
                else:
                    file_list.append(i)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('index.html', user_data=claims, error_message=error_message, user_info=user_info, file_list=file_list, directory_list=directory_list)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
