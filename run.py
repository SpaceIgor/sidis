import os
import shutil
import uvicorn
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client import OAuthError
from fastapi import FastAPI, Form
from fastapi import Request
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, RedirectResponse
from config import *

# Create the APP
app = FastAPI()

# OAuth settings
if GOOGLE_CLIENT_ID is None or GOOGLE_CLIENT_SECRET is None:
    raise BaseException('Missing env variables')

# Set up OAuth
config_data = {'GOOGLE_CLIENT_ID': GOOGLE_CLIENT_ID, 'GOOGLE_CLIENT_SECRET': GOOGLE_CLIENT_SECRET}
starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# Set up the middleware to read the request session
if SECRET_KEY is None:
    raise BaseException('Missing SECRET_KEY')
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Specify the directory you want to manage
TARGET_DIRECTORY = '/path/to/your/directory'


@app.get('/')
def public(request: Request):
    user = request.session.get('user')
    if user:
        name = user.get('name')
        return HTMLResponse(f'<p>Hello {name}!</p>'
                            f'<a href=/logout>Logout</a>'
                            f'<br><a href=/view_directory>View Directory</a>'
                            f'<br><a href=/add_item_form>Add Item</a>'
                            f'<br><a href=/delete_item_form>Delete Item</a>'
                            f'<br><a href=/move_item_form>Move Item</a>'
                            f'<br><a href=/edit_file_form>Edit File</a>')
    return HTMLResponse('<a href=/login>Login</a>')


@app.route('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')


@app.route('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')  # This creates the url for our /auth endpoint
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.route('/auth')
async def auth(request: Request):
    try:
        access_token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse(url='/')
    user_data = await oauth.google.parse_id_token(request, access_token)
    request.session['user'] = dict(user_data)
    return RedirectResponse(url='/')


@app.route('/view_directory')
async def view_directory(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    # Check if the user has necessary permissions or any other authentication logic
    # You may want to customize this part based on your requirements

    # Get the list of files and folders in the specified directory
    files_and_folders = os.listdir(TARGET_DIRECTORY)

    # Create an HTML response to display the list
    content = '<h2>Files and Folders in {}</h2>'.format(TARGET_DIRECTORY)
    content += '<ul>'
    for item in files_and_folders:
        content += '<li>{}</li>'.format(item)
    content += '</ul>'

    return HTMLResponse(content)


@app.route('/add_item_form')
async def add_item_form(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    form = '''
    <form method="post" action="/add_item">
        <label for="item_name">Item Name:</label>
        <input type="text" id="item_name" name="item_name" required>
        <button type="submit">Add Item</button>
    </form>
    '''

    return HTMLResponse(form)


@app.post('/add_item')
async def add_item(request: Request, item_name: str = Form(...)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    # Check if the user has necessary permissions or any other authentication logic
    # You may want to customize this part based on your requirements

    # Add the new item to the directory
    new_item_path = os.path.join(TARGET_DIRECTORY, item_name)
    if not os.path.exists(new_item_path):
        if not item_name.strip():  # Check if the item name is not empty or whitespace
            return HTMLResponse('<p>Item name cannot be empty or whitespace.</p>')
        else:
            # You can customize this part based on the type of item you want to add (file or directory)
            # For now, let's assume it's a file
            with open(new_item_path, 'w') as new_file:
                new_file.write('')  # Create an empty file

            return HTMLResponse(f'<p>Item "{item_name}" added successfully!</p>'
                                f'<a href=/view_directory>Back to Directory</a>')
    else:
        return HTMLResponse('<p>An item with the same name already exists. Please choose a different name.</p>'
                            '<a href=/add_item_form>Back to Add Item Form</a>')


@app.route('/delete_item_form')
async def delete_item_form(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    form = '''
    <form method="post" action="/delete_item">
        <label for="item_name">Item Name:</label>
        <input type="text" id="item_name" name="item_name" required>
        <button type="submit">Delete Item</button>
    </form>
    '''

    return HTMLResponse(form)


@app.post('/delete_item')
async def delete_item(request: Request, item_name: str = Form(...)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    # Check if the user has necessary permissions or any other authentication logic
    # You may want to customize this part based on your requirements

    # Delete the specified item from the directory
    item_path = os.path.join(TARGET_DIRECTORY, item_name)
    if os.path.exists(item_path):
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)  # Delete the directory and its contents
        else:
            os.remove(item_path)  # Delete the file

        return HTMLResponse(f'<p>Item "{item_name}" deleted successfully!</p>'
                            f'<a href=/view_directory>Back to Directory</a>')
    else:
        return HTMLResponse('<p>Item not found. Please enter a valid item name.</p>'
                            '<a href=/delete_item_form>Back to Delete Item Form</a>')


@app.route('/move_item_form')
async def move_item_form(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    # Get the list of files and folders in the specified directory
    files_and_folders = os.listdir(TARGET_DIRECTORY)

    form = '''
    <form method="post" action="/move_item">
        <label for="item_name">Item Name:</label>
        <input type="text" id="item_name" name="item_name" required>
        <label for="destination_folder">Destination Folder:</label>
        <select id="destination_folder" name="destination_folder" required>
    '''
    for item in files_and_folders:
        form += f'<option value="{item}">{item}</option>'

    form += '''
        </select>
        <button type="submit">Move Item</button>
    </form>
    '''

    return HTMLResponse(form)


@app.post('/move_item')
async def move_item(request: Request, item_name: str = Form(...), destination_folder: str = Form(...)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    # Check if the user has necessary permissions or any other authentication logic
    # You may want to customize this part based on your requirements

    # Move the specified item to the destination folder
    item_path = os.path.join(TARGET_DIRECTORY, item_name)
    destination_path = os.path.join(TARGET_DIRECTORY, destination_folder, item_name)

    if os.path.exists(item_path):
        os.rename(item_path, destination_path)

        return HTMLResponse(f'<p>Item "{item_name}" moved to "{destination_folder}" successfully!</p>'
                            f'<a href=/view_directory>Back to Directory</a>')
    else:
        return HTMLResponse('<p>Item not found. Please enter a valid item name.</p>'
                            '<a href=/move_item_form>Back to Move Item Form</a>')


@app.route('/edit_file_form')
async def edit_file_form(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    # Get the list of files in the specified directory
    files_in_directory = [f for f in os.listdir(TARGET_DIRECTORY) if os.path.isfile(os.path.join(TARGET_DIRECTORY, f))]

    form = '''
    <form method="post" action="/edit_file">
        <label for="file_name">File Name:</label>
        <select id="file_name" name="file_name" required>
    '''
    for file_name in files_in_directory:
        form += f'<option value="{file_name}">{file_name}</option>'

    form += '''
        </select>
        <label for="file_content">File Content:</label>
        <textarea id="file_content" name="file_content" rows="4" required></textarea>
        <button type="submit">Edit File</button>
    </form>
    '''

    return HTMLResponse(form)


@app.post('/edit_file')
async def edit_file(request: Request, file_name: str = Form(...), file_content: str = Form(...)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    # Check if the user has necessary permissions or any other authentication logic
    # You may want to customize this part based on your requirements

    # Edit the content of the specified file
    file_path = os.path.join(TARGET_DIRECTORY, file_name)

    if os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write(file_content)

        return HTMLResponse(f'<p>File "{file_name}" edited successfully!</p>'
                            f'<a href=/view_directory>Back to Directory</a>')
    else:
        return HTMLResponse('<p>File not found. Please enter a valid file name.</p>'
                            '<a href=/edit_file_form>Back to Edit File Form</a>')


if __name__ == '__main__':
    uvicorn.run(app, port=7000)
