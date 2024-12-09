import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk, font
import paramiko
from paramiko.ssh_exception import SSHException
import os
from threading import Thread, Lock
from stat import S_ISDIR
import time
import cv2
import random
import atexit
import tempfile
import posixpath

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QSlider, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt

# Global variables to hold the SSH client, SFTP session, and transport
client = None
sftp = None
transport = None
username = ""
local_temp_path = None
socket_lock = Lock()

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
        
        # Default remote directory path
        default_path = f"/projects/bddu/data_setup/data"
        Thread(target=display_directories, args = (default_path,)).start()

        # Open a file dialog to select a file
        file_paths = filedialog.askopenfilename(multiple = True)
        if file_paths: 
            # Ask the user for a subdirectory where the file will be uploaded, appended to the default path
            subdir = open_popup(default_path, "Upload Directory", "Upload", "Select the subdirectory path (root)")
            if subdir:
                remote_dir = posixpath.join(default_path, subdir)
            else:
                remote_dir = default_path

            # Ensure the directory exists, create it if it doesn't
            make_remote_dir(remote_dir)

        threads = []
        for file in file_paths: 
            if file:
                file_name = file.split('/')[-1]
                # Check if the file exists locally
                if not os.path.isfile(file):
                    messagebox.showerror("Upload Error", f"The selected file \"{file_name}\" does not exist.")
                    continue
                
                # Define the remote path where the file will be uploaded
                remote_path = posixpath.join(remote_dir, os.path.basename(file))

                # Check if the file already exists on the server
                try:
                    sftp.stat(remote_path)  # Check if the remote file exists
                    # If the file exists, prompt the user for confirmation to overwrite
                    overwrite = messagebox.askyesno("File Exists", f"The file \"{file_name}\" already exists on the server. Do you want to overwrite it?")
                    if not overwrite:
                        continue  # Cancel the upload if the user doesn't want to overwrite
                except FileNotFoundError:
                    # If the file doesn't exist, proceed with the upload
                    pass

                # Get file size for progress tracking
                file_size = os.path.getsize(file)

                # Initialize the progress bar and percentage label
                progress_var.set(0)
                percentage_label.config(text="0%")

                # Start upload in a separate thread to avoid blocking the GUI
                thread = Thread(target=upload_file_thread, args=(file, remote_path, file_size))
                disable_buttons()
                thread.start()
                threads.append(thread)

        if threads:
            check_threads(threads, "Upload")                

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
    with socket_lock:
        try:
            def progress_callback(transferred, total):
                # Calculate the progress percentage
                progress = (transferred / file_size) * 100
                # Update the progress on the main thread
                root.after(0, update_progress_bar, progress)

            with open(file_path, 'rb') as file_handle:
                sftp.putfo(file_handle, remote_path, callback=progress_callback)
            # Reset progress bar and percentage label
            root.after(0, update_progress_bar, 0)
        
        except Exception as e:
            root.after(0, messagebox.showerror, "Upload Error", str(e))

def check_threads(threads, action):
    alive_threads = []
    for thread in threads:
        if thread.is_alive():
            alive_threads.append(thread)

    if alive_threads:
        # If the thread is still running, check again after 100ms
        root.after(100, check_threads, alive_threads, action)
    else:
        root.after(0, messagebox.showinfo, action, f"File(s) successfully {action.lower()}ed")
        enable_buttons()

def open_popup(default_path, title, feature, text):
    # Create a window for the dropdown popup
    top = tk.Toplevel(root)
    top.geometry("500x100")
    top.title(title)
    
    # Initialize the selected file 
    selected_file = ""

    # Get the names of the files/folders 
    folder_contents = sftp.listdir_attr(default_path)
    file_names = []
    num_folder = 0

    # Get the names of folder contents
    for name in folder_contents:
        remote_path = posixpath.join(default_path, name.filename)
        if (feature == "Upload" or feature == "Display"):
            if is_directory(remote_path):
                file_names.append(name.filename)
                num_folder += 1
        else:
            if is_directory(remote_path):
                num_folder += 1
            file_names.append(name.filename)

    def get_selection(option):
        nonlocal selected_file
        selected_file = dropdown.get()

        # Check if the selected file string is not empty
        if selected_file: 
            remote_path = posixpath.join(default_path, selected_file)
            path_name = remote_path.replace(default_path, "root")

            # Keep the popup window opened
            if option != "View":
                top.destroy()

            # Check if the remote_path is a subdirectory 
            if option == "Open" and is_directory(remote_path):
                # Display error if the user tries to open a file
                file_name = open_popup(remote_path, title, feature, f"Select the remote path of the file to {feature.lower()} ({path_name}): ")
                if file_name or feature == "Display":
                    selected_file += f"/{file_name}"   
                else:
                    selected_file = ""
            elif option == "Open":
                messagebox.showerror("Open Error", f"Cannot open the file '{selected_file}'")
                selected_file = ""
            
            if option == "View":
                stream_video_preview(selected_file)
                selected_file = ""
        else:
            top.destroy()

    def create_subdirectory():
        nonlocal selected_file
        top.destroy()
        selected_file = simpledialog.askstring("New Subdirectory", f"Enter the subdirectory name ({default_path}):")

    # Add an intruction text for the popup
    tk.Label(top, text=text, font=("TkDefaultFont")).place(x=10, y=10)

    # Create the dropdown component
    dropdown = ttk.Combobox(top, state="readonly", values=file_names, width="75")
    dropdown.place(x=10, y=35)

    # A button for selecting a file/folder 
    tk.Button(top, text=feature, command=lambda: get_selection(feature)).place(x=20, y=65)

    # A button for canceling the popup
    tk.Button(top, text="Cancel", command=top.destroy).place(x=190, y=65)
        
    # A button for opening a subdirectory 
    open_btn = tk.Button(top, text="Open", command=lambda: get_selection("Open"))
    open_btn.place(x=250, y=65)

    # A button for creating a new subdirectory (only for the upload feature)
    if feature == "Upload":
        tk.Button(top, text="Create a new subdirectory", command=lambda: create_subdirectory()).place(x=300, y=65)
    
    if feature == "Download":
        tk.Button(top, text="Preview", command=lambda: get_selection("View")).place(x=300, y=65)

    # If there is no subdirectories, disable the open button
    if num_folder == 0:
        open_btn.config(state=tk.DISABLED)    
    
    top.wait_window()
    return selected_file

def download_file():
    global sftp
    try:
        # Check if SFTP session is active
        if sftp is None:
            messagebox.showerror("Download Error", "Not connected to the server.")
            return
        
        # Default remote directory path
        default_path = f"/projects/bddu/data_setup/data"

        # Ask the user for the remote path of the file to be downloaded         
        file_string = open_popup(default_path, "Remote Path", "Download", f"Select the remote path of the file to download (root):")
        remote_files = []
        if file_string:
            remote_files = file_string.split(", ")

        threads = []
        for remote_file in remote_files:
            if remote_file:
                remote_path = posixpath.join(default_path, remote_file)
                # Check if the remote path is a directory
                if not is_directory(remote_path):
                    # Open a file dialog to select a save location
                    file_path = filedialog.asksaveasfilename(initialfile=os.path.basename(remote_path))
                    if file_path:
                        # Initialize the progress bar and percentage label
                        progress_var.set(0)
                        percentage_label.config(text="0%")
                        # Start download in a separate thread to avoid blocking the GUI
                        thread = Thread(target=download_file_thread, args=(remote_path, file_path))
                        disable_buttons()
                        thread.start()
                        threads.append(thread)
                else:
                    messagebox.showerror("Download Error", f"Cannot download the subdirectory '{remote_file}'")

                                       
        if threads:
            check_threads(threads, "Download")   

    except Exception as e:
        messagebox.showerror("Download Error", str(e))

def download_file_thread(remote_path, file_path):    
    with socket_lock:
        try:    
            # root.mainloop()            
            def progress_callback(transferred, total):
                # Calculate the progress percentage
                progress = (transferred / total) * 100
                # Update the progress on the main thread
                root.after(0, update_progress_bar, progress)

            # Download the file
            with open(file_path, 'wb') as file_handle:
                sftp.getfo(remote_path, file_handle, callback=progress_callback)
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
        default_path = f"/projects/bddu/data_setup/data"
        
        # Ask the user for the path of the file/folder to be deleted    
        paths_string = open_popup(default_path, "Remote Path", "Delete", f"Select the remote path of the file to delete (root)")

        paths_to_delete = []
        if paths_string:
            paths_to_delete = paths_string.split(", ")

        for path_to_delete in paths_to_delete:
            if path_to_delete:
                remote_path = posixpath.join(default_path, path_to_delete)
                file_stat = sftp.stat(remote_path)

                # Ask for user confirmation
                confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{remote_path}'?")
                if not confirm:
                    continue  # User canceled the deletion

                # If it's a directory, delete it recursively
                if S_ISDIR(file_stat.st_mode):
                    delete_directory_recursive(remote_path)
                else:
                    sftp.remove(remote_path)  # If it's a file, delete it directly
                
                # Display the parent directory after deleting a file/folder
                updated_directory = "/".join(remote_path.rsplit("/", 1)[:-1])
                Thread(target=display_directories, args = (updated_directory,)).start()
                messagebox.showinfo("Deletion Complete", f"Successfully deleted '{remote_path}'")
    
    except Exception as e:
        messagebox.showerror("Deletion Error", str(e))

def delete_directory_recursive(remote_path):
    """Recursively delete a directory and all its contents."""
    for item in sftp.listdir(remote_path):
        item_path = posixpath.join(remote_path, item)
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
            item_path = posixpath.join(remote_path, item.filename)
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
            item_path = posixpath.join(remote_path, item.filename)
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
        default_path = f"/projects/bddu/data_setup/data"
        
        # Ask the user for the subdirectory to manage, appende  d to the default path
        subdir = open_popup(default_path, "Remote Directory", "Display", "Select the subdirectory path (root)")
        if subdir:
            remote_dir = posixpath.join(default_path, subdir)
        else:
            remote_dir = default_path

        # Check if the directory exists
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            messagebox.showerror("Folder Management Error", "The specified directory does not exist.")
            return

        display_directories(remote_dir)

    except Exception as e:
        messagebox.showerror("Folder Management Error", str(e))

def display_directories(remote_dir):
    # List directory contents
    folder_contents = sftp.listdir_attr(remote_dir)

    # Color tags for files, folders, and root directory
    directory_display.tag_config("dir_tag", foreground="#8B8000")
    directory_display.tag_config("file_tag", foreground="black")
    directory_display.tag_config("root_tag", foreground="red")

    # Clear the display area before showing updated directory contents
    directory_display.config(state=tk.NORMAL)
    directory_display.delete(1.0, tk.END)
    directory_display.insert(tk.END, f"Contents of {remote_dir}:\n\n", "root_tag")
    
    for item in folder_contents:
        item_name = item.filename
        item_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.st_mtime))
        item_size = f"{item.st_size} bytes"
        if S_ISDIR(item.st_mode):
            directory_display.insert(tk.END, f"[DIR]  {item_name}\t\n", "dir_tag")
        else:
            directory_display.insert(tk.END, f"[FILE] {item_name}\t\n", "file_tag")
    
    directory_display.config(state=tk.DISABLED)

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
    stream_preview_btn.config(state=tk.NORMAL)

def disable_buttons():
    upload_btn.config(state=tk.DISABLED)
    download_btn.config(state=tk.DISABLED)
    delete_btn.config(state=tk.DISABLED)
    manage_folders_btn.config(state=tk.DISABLED)
    disconnect_btn.config(state=tk.DISABLED)
    stream_preview_btn.config(state=tk.DISABLED)

class VideoPlayer(QMainWindow):
    def __init__(self, video_source):
        super().__init__()

        self.setWindowTitle('Video Preview')
        self.setGeometry(100, 100, 800, 600)

        self.video_source = video_source
        self.vid = cv2.VideoCapture(self.video_source)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.video_label = QLabel()
        self.layout.addWidget(self.video_label)

        self.play_button = QPushButton('Play')
        self.play_button.clicked.connect(self.play)
        self.layout.addWidget(self.play_button)

        self.pause_button = QPushButton('Pause')
        self.pause_button.clicked.connect(self.pause)
        self.layout.addWidget(self.pause_button)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(int(self.vid.get(cv2.CAP_PROP_FRAME_COUNT)))
        self.progress_slider.valueChanged.connect(self.set_frame)
        self.layout.addWidget(self.progress_slider)

        self.is_paused = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def play(self):
        self.is_paused = False

    def pause(self):
        self.is_paused = True

    def set_frame(self, position):
        self.vid.set(cv2.CAP_PROP_POS_FRAMES, position)

    def update_frame(self):
        if not self.is_paused:
            ret, frame = self.vid.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img)
                self.video_label.setPixmap(pixmap)
                self.progress_slider.setValue(int(self.vid.get(cv2.CAP_PROP_POS_FRAMES)))
            else:
                self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)

def cleanup(local_temp_path, remote_temp_path, client):
    """Ensure the cleanup of local and remote temporary files."""
    try:
        # Clean up the remote temporary file
        if remote_temp_path and client:
            client.exec_command(f'rm "{remote_temp_path}"')
            print(f"Remote file {remote_temp_path} deleted.")

        # Clean up the local temporary file
        if local_temp_path and os.path.exists(local_temp_path):
            os.remove(local_temp_path)
            print(f"Local file {local_temp_path} deleted.")

    except Exception as e:
        print(f"Error during cleanup: {e}")

def stream_video_preview(remote_file):
    global sftp, client
    global local_temp_path
    remote_temp_path = None

    try:
        if client is None:
            messagebox.showerror("Preview Error", "Not connected to the server.")
            return

        # Ask the user for the remote path of the video file to preview
        default_path = f"/projects/bddu/data_setup/data"        
        if not remote_file: 
            remote_file = open_popup(default_path, "Video Preview", "Preview", "Select the remote path of video to preview (root)")
        
        if remote_file:
            if '.mp4' in remote_file:
                # Define the path for the temporary file on the server
                remote_path = posixpath.join(default_path, remote_file)

                remote_temp_path = posixpath.join("/projects/bddu/data_setup", f"tmp/temp_preview_{random.getrandbits(128)}.mp4")

                # Move current directory to project
                client.exec_command(f"cd {default_path}")

                # Define the ffmpeg command to extract the first 5 seconds
                ffmpeg_cmd = (
                    f'cd {default_path} && export LD_LIBRARY_PATH=/projects/bddu/ffmpeg/lib:$LD_LIBRARY_PATH && '
                    f'/projects/bddu/ffmpeg/bin/ffmpeg -ss 00:00:00 -i "{remote_path}" -t 00:00:05 -c copy "{remote_temp_path}"'
                )

                # Execute the ffmpeg command on the remote server
                stdin, stdout, stderr = client.exec_command(ffmpeg_cmd)
                
                # Wait for the command to finish
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error_msg = stderr.read().decode()
                    raise Exception(f"FFmpeg error: {error_msg}")
                
                temp_dir = tempfile.gettempdir()  # Get a system-specific temporary directory
                local_temp_path = os.path.join(temp_dir, f"tmp_{random.getrandbits(128)}.mp4")
                
                with open(local_temp_path, 'wb') as file_handle:
                    sftp.getfo(remote_temp_path, file_handle)

                # Remove the temporary file on the remote server
                client.exec_command(f'rm "{remote_temp_path}"')
                
                atexit.register(cleanup, local_temp_path, remote_temp_path, client)

                # Initialize and start the video player
                app = QApplication([])
                player = VideoPlayer(local_temp_path)
                player.show()
                app.exec_()

                # Clean up temporary local file
                os.remove(local_temp_path)
            else:
                messagebox.showerror("Preview Error", f"Cannot preview the file {remote_file}")

    except Exception as e:
        # messagebox.showerror("Preview Error", "Invalid video input")
        print("Preview Error", str(e))
    finally:
        # Cleanup remote file in case of any error
        cleanup(local_temp_path, remote_temp_path, client)

# Initialize the main window
root = tk.Tk()

root.title("Delta HPC File Manager")

# Set the window size
root.geometry("750x700")

font_txt = ("TkDefaultFont", 11)
default_font = font.nametofont("TkDefaultFont")
default_font.configure(size=10)

# Username label and entry
username_label = tk.Label(root, text="Username:", font=font_txt)
username_label.pack(pady=5)
username_entry = tk.Entry(root, width=40, font=("TkDefaultFont", 10))
username_entry.pack(pady=5)

# Password label and entry
password_label = tk.Label(root, text="Password:", font=font_txt)
password_label.pack(pady=5)
password_entry = tk.Entry(root, show="*", width=40, font=("TkDefaultFont", 10))
password_entry.pack(pady=5)


# Connect button
connect_btn = tk.Button(root, text="Connect", width=20, command=connect_to_server, font=font_txt)
connect_btn.pack(pady=10)

# Manage Folders button
manage_folders_btn = tk.Button(root, text="List Directory Contents", width=20, state=tk.DISABLED, command=manage_folders, font=font_txt)
manage_folders_btn.pack(pady=5)

# Upload button
upload_btn = tk.Button(root, text="Upload File(s)", width=20, state=tk.DISABLED, command=upload_file, font=font_txt)
upload_btn.pack(pady=5)

# Download button
download_btn = tk.Button(root, text="Download File(s)", width=20, state=tk.DISABLED, command=download_file, font=font_txt)
download_btn.pack(pady=5)

# Delete button
delete_btn = tk.Button(root, text="Delete File(s)/Folder(s)", width=20, state=tk.DISABLED, command=delete_file_or_folder, font=font_txt)
delete_btn.pack(pady=5)


# Stream preview video button
stream_preview_btn = tk.Button(root, text="Stream Preview Video", width=20, state=tk.DISABLED, command=lambda: stream_video_preview(""), font=font_txt)
stream_preview_btn.pack(pady=5)

# Disconnect button
disconnect_btn = tk.Button(root, text="Disconnect", width=20, state=tk.DISABLED, command=disconnect_from_server, font=font_txt)
disconnect_btn.pack(pady=10)

# Progress bar
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=500)
progress_bar.pack(pady=10)

# Percentage label
percentage_label = tk.Label(root, text="0%", font=font_txt)
percentage_label.pack(pady=5)

# Directory display
directory_display = tk.Text(root, height=15, width=80, state=tk.DISABLED, font=font_txt)
directory_display.pack(pady=10)

# Start the GUI event loop
root.mainloop()
