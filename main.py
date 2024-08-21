import tkinter as tk
from tkinter import filedialog, messagebox
import paramiko
from paramiko.ssh_exception import SSHException
import os

# Global variables to hold the SSH client and SFTP session
client = None
sftp = None
transport = None

def duo_authentication_handler(title, instructions, fields):
    responses = []
    for field in fields:
        prompt = field[0].strip()
        if "password" in prompt.lower():
            responses.append(password_entry.get())  # Password entered in GUI
        elif "passcode or option" in prompt.lower():
            responses.append("1")  # Adjust based on actual Duo prompts
        else:
            raise SSHException(f"Unexpected prompt: {prompt}")
    return responses

def connect_to_server():
    global client, sftp, transport
    try:
        # Get values from the GUI fields
        username = username_entry.get()
        password = password_entry.get()

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
        global sftp
        sftp = client.open_sftp()
        messagebox.showinfo("Connection", "Successfully connected to the server!")

        # Enable the upload and disconnect buttons after a successful connection
        enable_buttons()

    except paramiko.ssh_exception.SSHException as e:
        messagebox.showerror("Connection Error", f"SSH Error: {str(e)}")
    except Exception as e:
        messagebox.showerror("Connection Error", str(e))

def upload_file():
    global sftp
    try:
        # Check if SFTP session is active
        if sftp is None:
            messagebox.showerror("Upload Error", "Not connected to the server.")
            return

        # Open a file dialog to select a file
        file_path = filedialog.askopenfilename()
        if file_path:
            # Define the remote path where the file will be uploaded
            remote_path = "/projects/bddu/dnguyen15/" + os.path.basename(file_path)
            sftp.put(file_path, remote_path)
            messagebox.showinfo("Upload", f"Successfully uploaded {os.path.basename(file_path)}")
    except Exception as e:
        messagebox.showerror("Upload Error", str(e))

def disconnect_from_server():
    global client, sftp, transport
    try:
        # Close the SFTP session and SSH client
        if sftp:
            sftp.close()
        if client:
            client.close()
        if transport:
            transport.close()
        messagebox.showinfo("Disconnected", "Disconnected from the server.")
    except Exception as e:
        messagebox.showerror("Disconnection Error", str(e))

# Helper function to enable buttons after a successful connection
def enable_buttons():
    upload_btn.config(state=tk.NORMAL)
    disconnect_btn.config(state=tk.NORMAL)

# Set up the GUI window
root = tk.Tk()
root.title("Delta HPC Server File Upload")

# Create GUI elements for user input
tk.Label(root, text="Username:").pack(pady=5)
username_entry = tk.Entry(root, width=40)
username_entry.pack(pady=5)

tk.Label(root, text="Password:").pack(pady=5)
password_entry = tk.Entry(root, show="*", width=40)
password_entry.pack(pady=5)

# Create buttons for connecting, uploading, and disconnecting
connect_btn = tk.Button(root, text="Connect to Server", command=connect_to_server)
connect_btn.pack(pady=10)

upload_btn = tk.Button(root, text="Upload File", command=upload_file, state=tk.DISABLED)
upload_btn.pack(pady=10)

disconnect_btn = tk.Button(root, text="Disconnect", command=disconnect_from_server, state=tk.DISABLED)
disconnect_btn.pack(pady=10)

# Start the Tkinter main loop
root.mainloop()
