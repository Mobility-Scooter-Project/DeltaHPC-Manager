from tkinter import messagebox
import paramiko
from paramiko.ssh_exception import SSHException

import utils.buttons_util

client = None
sftp = None
transport = None
password = ""

def duo_authentication_handler(title, instructions, fields):
    responses = []
    for field in fields:
        prompt = field[0].strip()
        if "password" in prompt.lower():
            responses.append(password)  # Password entered in GUI
        elif "passcode or option" in prompt.lower():
            responses.append("1")  # Adjust based on actual Duo prompts
        else:
            raise SSHException(f"Unexpected prompt: {prompt}")
    return responses

def connect_to_server(username, pw, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn):
    global client, sftp, transport, password
    try:
        password = pw
        # Ensure the username and password are not empty
        if not username or not password:
            messagebox.showerror("Input Error", "Username and Password cannot be empty.")
            return

        # Fixed hostname for Delta HPC server
        hostname = "login.delta.ncsa.illinois.edu"

        # Initialize Paramiko Transport object
        transport = paramiko.Transport((hostname, 22))
        transport.connect(username=username, password=password)

        # Perform interactive authentication with Duo MFA
        transport.auth_interactive(username, duo_authentication_handler)

        # Initialize Paramiko SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client._transport = transport

        # Initialize the SFTP session
        sftp = client.open_sftp()
        messagebox.showinfo("Connection", "Successfully connected to the server!")

        # Enable the upload, download, delete, and disconnect buttons after a successful connection
        utils.buttons_util.enable_buttons(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)

    except paramiko.ssh_exception.AuthenticationException as e:
        messagebox.showerror("Authentication Error", f"Authentication failed: {str(e)}")
    except paramiko.ssh_exception.SSHException as e:
        messagebox.showerror("Connection Error", f"SSH Error: {str(e)}")
    except Exception as e:
        messagebox.showerror("Connection Error", str(e))

def disconnect_from_server(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn):
    global client, sftp, transport
    try:
        # Close the SFTP session and SSH client
        if sftp:
            sftp.close()
        if client:
            client.close()
        if transport:
            transport.close()
        messagebox.showinfo("Disconnection", "Successfully disconnected from the server!")

        # Reset the global variables
        client = None
        sftp = None
        transport = None

        # Disable the buttons after disconnecting
        utils.buttons_util.disable_buttons(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)

    except Exception as e:
        messagebox.showerror("Disconnection Error", str(e))