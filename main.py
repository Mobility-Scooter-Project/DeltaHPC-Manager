import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import paramiko
from paramiko.ssh_exception import SSHException
import os
from threading import Thread
from stat import S_ISDIR
import time

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

        # Enable the upload, download, delete, and disconnect buttons after a successful connection
        enable_buttons()

    except paramiko.ssh_exception.AuthenticationException as e:
        messagebox.showerror("Authentication Error", f"Authentication failed: {str(e)}")
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
            # Check if the file exists locally
            if not os.path.isfile(file_path):
                messagebox.showerror("Upload Error", "The selected file does not exist.")
                return

            # Default remote directory path
            default_path = f"/projects/bddu/data"

            # Ask the user for a subdirectory where the file will be uploaded, appended to the default path
            subdir = simpledialog.askstring("Upload Directory", f"Enter the subdirectory path (relative to {default_path}):")
            if subdir:
                remote_dir = os.path.join(default_path, subdir)
            else:
                remote_dir = default_path

            # Ensure the directory exists, create it if it doesn't
            make_remote_dir(remote_dir)

            # Define the remote path where the file will be uploaded
            remote_path = os.path.join(remote_dir, os.path.basename(file_path))

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
        default_path = f"/projects/bddu/data"
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
            progress = (transferred / total) * 100
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

def delete_file_or_folder():
    global sftp
    try:
        # Check if SFTP session is active
        if sftp is None:
            messagebox.showerror("Deletion Error", "Not connected to the server.")
            return

        # Default remote directory path
        default_path = f"/projects/bddu/data"
        
        # Ask the user for the path of the file/folder to be deleted
        path_to_delete = simpledialog.askstring("Delete Path", f"Enter the remote path of the file/folder to delete (relative to {default_path}):")
        
        if path_to_delete:
            remote_path = os.path.join(default_path, path_to_delete)

            # Check if the remote path exists
            try:
                file_stat = sftp.stat(remote_path)
            except FileNotFoundError:
                messagebox.showerror("Deletion Error", "The specified file or folder does not exist.")
                return

            # Ask for user confirmation
            confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{remote_path}'?")
            if not confirm:
                return  # User canceled the deletion

            # If it's a directory, delete it recursively
            if S_ISDIR(file_stat.st_mode):
                delete_directory_recursive(remote_path)
            else:
                sftp.remove(remote_path)  # If it's a file, delete it directly

            messagebox.showinfo("Deletion Complete", f"Successfully deleted '{remote_path}'")
    
    except Exception as e:
        messagebox.showerror("Deletion Error", str(e))

def delete_directory_recursive(remote_path):
    """Recursively delete a directory and all its contents."""
    for item in sftp.listdir(remote_path):
        item_path = os.path.join(remote_path, item)
        try:
            if is_directory(item_path):
                delete_directory_recursive(item_path)  # Recursively delete subdirectory
            else:
                sftp.remove(item_path)  # Delete file
        except Exception as e:
            messagebox.showerror("Deletion Error", f"Error deleting {item_path}: {str(e)}")
    sftp.rmdir(remote_path)  # Delete the now-empty directory


def delete_item_thread(remote_path, item_type, total_size):
    try:
        transferred = 0

        if item_type == "folder":
            for count in delete_folder(remote_path, total_size):
                transferred += count
                progress = (transferred / total_size) * 100
                root.after(0, update_progress_bar, progress)
        else:
            delete_file(remote_path, total_size)
            root.after(0, update_progress_bar, 100)

        messagebox.showinfo("Delete", f"Successfully deleted the {item_type} '{os.path.basename(remote_path)}'")
        
        # Reset progress bar and percentage label
        root.after(0, update_progress_bar, 0)
    except Exception as e:
        messagebox.showerror("Delete Error", str(e))

def delete_file(remote_path, file_size):
    """Delete a single file with progress tracking."""
    try:
        # Delete the file
        sftp.remove(remote_path)
    except Exception as e:
        raise e

def delete_folder(remote_path, total_size):
    """Recursively delete a folder and its contents with progress tracking."""
    try:
        for item in sftp.listdir_attr(remote_path):
            item_path = os.path.join(remote_path, item.filename)
            if S_ISDIR(item.st_mode):
                # Recursively delete the subdirectory
                yield from delete_folder(item_path, total_size)
            else:
                # Delete the file
                sftp.remove(item_path)
                yield item.st_size
        # Delete the folder itself
        sftp.rmdir(remote_path)
        yield 0  # For the folder itself
    except Exception as e:
        raise e

def calculate_directory_size(remote_path):
    """Calculate total size of all files in the directory recursively."""
    total_size = 0
    try:
        for item in sftp.listdir_attr(remote_path):
            item_path = os.path.join(remote_path, item.filename)
            if S_ISDIR(item.st_mode):
                total_size += calculate_directory_size(item_path)
            else:
                total_size += item.st_size
    except Exception as e:
        raise e
    return total_size

def is_directory(remote_path):
    """Check if the remote path is a directory."""
    try:
        return S_ISDIR(sftp.stat(remote_path).st_mode)
    except IOError:
        return False

def update_progress_bar(progress):
    """Update the progress bar and percentage label."""
    progress_var.set(progress)
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
        default_path = f"/projects/bddu/data"
        
        # Ask the user for the subdirectory to manage, appended to the default path
        subdir = simpledialog.askstring("Remote Directory", f"Enter the subdirectory path (relative to {default_path}):")
        if subdir:
            remote_dir = os.path.join(default_path, subdir)
        else:
            remote_dir = default_path

        # Check if the directory exists
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            messagebox.showerror("Folder Management Error", "The specified directory does not exist.")
            return

        # List directory contents
        folder_contents = sftp.listdir_attr(remote_dir)
        
        # Clear the display area before showing updated directory contents
        directory_display.config(state=tk.NORMAL)
        directory_display.delete(1.0, tk.END)
        directory_display.insert(tk.END, f"Contents of {remote_dir}:\n\n")
        
        for item in folder_contents:
            item_name = item.filename
            item_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.st_mtime))
            item_size = f"{item.st_size} bytes"
            if S_ISDIR(item.st_mode):
                directory_display.insert(tk.END, f"[DIR]  {item_name}\t\n")
            else:
                directory_display.insert(tk.END, f"[FILE] {item_name}\t\n")
        
        directory_display.config(state=tk.DISABLED)

    except Exception as e:
        messagebox.showerror("Folder Management Error", str(e))

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
        messagebox.showinfo("Disconnection", "Successfully disconnected from the server!")

        # Reset the global variables
        client = None
        sftp = None
        transport = None

        # Disable the buttons after disconnecting
        disable_buttons()

    except Exception as e:
        messagebox.showerror("Disconnection Error", str(e))

def enable_buttons():
    upload_btn.config(state=tk.NORMAL)
    download_btn.config(state=tk.NORMAL)
    delete_btn.config(state=tk.NORMAL)
    manage_folders_btn.config(state=tk.NORMAL)
    disconnect_btn.config(state=tk.NORMAL)

def disable_buttons():
    upload_btn.config(state=tk.DISABLED)
    download_btn.config(state=tk.DISABLED)
    delete_btn.config(state=tk.DISABLED)
    manage_folders_btn.config(state=tk.DISABLED)
    disconnect_btn.config(state=tk.DISABLED)

# Initialize the main window
root = tk.Tk()
root.title("Delta HPC File Manager")

# Set the window size
root.geometry("700x600")

# Username label and entry
username_label = tk.Label(root, text="Username:")
username_label.pack(pady=5)
username_entry = tk.Entry(root, width=40)
username_entry.pack(pady=5)

# Password label and entry
password_label = tk.Label(root, text="Password:")
password_label.pack(pady=5)
password_entry = tk.Entry(root, show="*", width=40)
password_entry.pack(pady=5)

# Connect button
connect_btn = tk.Button(root, text="Connect", width=20, command=connect_to_server)
connect_btn.pack(pady=10)

# Upload button
upload_btn = tk.Button(root, text="Upload File", width=20, state=tk.DISABLED, command=upload_file)
upload_btn.pack(pady=5)

# Download button
download_btn = tk.Button(root, text="Download File", width=20, state=tk.DISABLED, command=download_file)
download_btn.pack(pady=5)

# Delete button
delete_btn = tk.Button(root, text="Delete File/Folder", width=20, state=tk.DISABLED, command=delete_file_or_folder)
delete_btn.pack(pady=5)

# Manage Folders button
manage_folders_btn = tk.Button(root, text="List Directory Contents", width=20, state=tk.DISABLED, command=manage_folders)
manage_folders_btn.pack(pady=5)

# Disconnect button
disconnect_btn = tk.Button(root, text="Disconnect", width=20, state=tk.DISABLED, command=disconnect_from_server)
disconnect_btn.pack(pady=10)

# Progress bar
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=500)
progress_bar.pack(pady=10)

# Percentage label
percentage_label = tk.Label(root, text="0%")
percentage_label.pack(pady=5)

# Directory display
directory_display = tk.Text(root, height=15, width=80, state=tk.DISABLED)
directory_display.pack(pady=10)

# Start the GUI event loop
root.mainloop()
