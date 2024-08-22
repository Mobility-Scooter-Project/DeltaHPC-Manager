import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import paramiko
from paramiko.ssh_exception import SSHException
import os
from threading import Thread
from stat import S_ISDIR

# Global variables to hold the SSH client, SFTP session, and transport
client = None
sftp = None
transport = None
username = ""

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
        global username
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

        # Enable the upload, download, and disconnect buttons after a successful connection
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
            # Print the selected file path for debugging
            print(f"Selected file path: {file_path}")

            # Check if the file exists locally
            if not os.path.isfile(file_path):
                messagebox.showerror("Upload Error", "The selected file does not exist.")
                return

            # Default remote directory path
            default_path = f"/projects/bddu/{username}/data"

            # Ask the user for a subdirectory where the file will be uploaded, appended to the default path
            subdir = simpledialog.askstring("Upload Directory", f"Enter the subdirectory path (relative to {default_path}):")
            if subdir:
                remote_dir = os.path.join(default_path, subdir)
            else:
                remote_dir = default_path

            # Ensure the directory exists, create it if it doesn't
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                make_remote_dir(remote_dir)

            # Define the remote path where the file will be uploaded
            remote_path = os.path.join(remote_dir, os.path.basename(file_path))

            # Print the remote path for debugging
            print(f"Remote path: {remote_path}")

            # Get file size for progress tracking
            file_size = os.path.getsize(file_path)

            # Initialize the progress bar and percentage label
            progress_var.set(0)
            percentage_label.config(text="0%")

            # Start upload in a separate thread to avoid blocking the GUI
            Thread(target=upload_file_thread, args=(file_path, remote_path, file_size)).start()

    except Exception as e:
        messagebox.showerror("Upload Error", str(e))

def make_remote_dir(remote_dir):
    """Helper function to create a remote directory if it doesn't exist."""
    dirs = remote_dir.split("/")
    path = ""
    for dir in dirs:
        if dir:  # Ignore empty strings from leading '/'
            path = f"{path}/{dir}"
            try:
                sftp.stat(path)
            except FileNotFoundError:
                sftp.mkdir(path)


def upload_file_thread(file_path, remote_path, file_size):
    try:
        def progress_callback(transferred, total):
            # Calculate the progress percentage
            progress = (transferred / file_size) * 100
            # Update the progress on the main thread
            root.after(0, update_progress_bar, progress)

        with open(file_path, 'rb') as file_handle:
            sftp.putfo(file_handle, remote_path, callback=progress_callback)
        messagebox.showinfo("Upload", f"Successfully uploaded {os.path.basename(file_path)}")
        # Reset progress bar and percentage label
        root.after(0, update_progress_bar, 0)
    except Exception as e:
        messagebox.showerror("Upload Error", str(e))

def download_file():
    global sftp
    try:
        # Check if SFTP session is active
        if sftp is None:
            messagebox.showerror("Download Error", "Not connected to the server.")
            return
        default_path = f"/projects/bddu/{username}/data"
        # Ask the user for the remote path of the file to be downloaded
        remote_file = simpledialog.askstring("Remote Path", f"Enter the remote path of the file to download (relative to {default_path}):")
        
            
        if remote_file:
            remote_path = os.path.join(default_path, remote_file)
            # Check if the remote file exists
            try:
                file_size = sftp.stat(remote_path).st_size
            except FileNotFoundError:
                messagebox.showerror("Download Error", "The remote file does not exist.")
                return

            # Open a file dialog to select a save location
            file_path = filedialog.asksaveasfilename(initialfile=os.path.basename(remote_path))
            if file_path:
                # Initialize the progress bar and percentage label
                progress_var.set(0)
                percentage_label.config(text="0%")

                # Start download in a separate thread to avoid blocking the GUI
                Thread(target=download_file_thread, args=(remote_path, file_path, file_size)).start()

    except Exception as e:
        messagebox.showerror("Download Error", str(e))


def download_file_thread(remote_path, file_path, file_size):
    try:
        def progress_callback(transferred, total):
            # Calculate the progress percentage
            progress = (transferred / file_size) * 100
            # Update the progress on the main thread
            root.after(0, update_progress_bar, progress)

        # Download the file
        with open(file_path, 'wb') as file_handle:
            sftp.getfo(remote_path, file_handle, callback=progress_callback)
        messagebox.showinfo("Download", f"Successfully downloaded {os.path.basename(file_path)}")
        # Reset progress bar and percentage label
        root.after(0, update_progress_bar, 0)
    except Exception as e:
        messagebox.showerror("Download Error", str(e))

def update_progress_bar(progress):
    # Update the progress bar value
    progress_var.set(progress)
    # Update the percentage label
    percentage_label.config(text=f"{progress:.2f}%")
    root.update_idletasks()





def manage_folders():
    global sftp
    try:
        # Check if SFTP session is active
        if sftp is None:
            messagebox.showerror("Folder Management Error", "Not connected to the server.")
            return

        # Default remote directory path
        default_path = f"/projects/bddu/{username}/data"
        
        # Ask the user for the subdirectory to manage, appended to the default path
        subdir = simpledialog.askstring("Remote Directory", f"Enter the subdirectory path (relative to {default_path}):")
        if subdir:
            remote_dir = os.path.join(default_path, subdir)
        else:
            remote_dir = default_path

        # List files and directories in the remote directory
        file_list = sftp.listdir(remote_dir)
        
        # Clear the directory content display area
        directory_content_display.config(state=tk.NORMAL)  # Enable editing
        directory_content_display.delete(1.0, tk.END)  # Clear current content
        
        # Show the current directory path
        directory_content_display.insert(tk.END, f"Directory: {remote_dir}\n\n")

        # Display the files and directories
        if file_list:
            for item in file_list:
                # Check if it's a directory
                item_path = os.path.join(remote_dir, item)
                if is_directory(item_path):
                    directory_content_display.insert(tk.END, f"** {item}\n")  # Prefix directories with **
                else:
                    directory_content_display.insert(tk.END, f"{item}\n")  # No prefix for files
        else:
            directory_content_display.insert(tk.END, "No files or directories found.")
        
        directory_content_display.config(state=tk.DISABLED)  # Disable editing

    except Exception as e:
        messagebox.showerror("Folder Management Error", str(e))

def is_directory(path):
    """Helper function to check if the path is a directory."""
    try:
        return S_ISDIR(sftp.stat(path).st_mode)
    except IOError:
        return False



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
    download_btn.config(state=tk.NORMAL)
    manage_folders_btn.config(state=tk.NORMAL)
    disconnect_btn.config(state=tk.NORMAL)

# Set up the GUI window
root = tk.Tk()
root.title("Delta HPC Server File Management")

# Create GUI elements for user input
tk.Label(root, text="Username:").pack(pady=5)
username_entry = tk.Entry(root, width=40)
username_entry.pack(pady=5)

tk.Label(root, text="Password:").pack(pady=5)
password_entry = tk.Entry(root, show="*", width=40)
password_entry.pack(pady=5)

# Create buttons for connecting, uploading, downloading, managing folders, and disconnecting
connect_btn = tk.Button(root, text="Connect to Server", command=connect_to_server)
connect_btn.pack(pady=10)

upload_btn = tk.Button(root, text="Upload File", command=upload_file, state=tk.DISABLED)
upload_btn.pack(pady=10)

download_btn = tk.Button(root, text="Download File", command=download_file, state=tk.DISABLED)
download_btn.pack(pady=10)

manage_folders_btn = tk.Button(root, text="List current directory", command=manage_folders, state=tk.DISABLED)
manage_folders_btn.pack(pady=10)

disconnect_btn = tk.Button(root, text="Disconnect", command=disconnect_from_server, state=tk.DISABLED)
disconnect_btn.pack(pady=10)

# Add a progress bar for file upload and download
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=300)
progress_bar.pack(pady=10)

# Add a label for percentage
percentage_label = tk.Label(root, text="0%")
percentage_label.pack(pady=5)


directory_content_display = tk.Text(root, height=10, width=80, state=tk.DISABLED)
directory_content_display.pack(pady=10)

# Start the Tkinter main loop
root.mainloop()
