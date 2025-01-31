from tkinter import filedialog, messagebox
import os
from threading import Thread, Lock
import posixpath

import components.menu
import features.display
import utils.progress_bar_utils
import utils.threads_utils
import connection
import utils.buttons_util

socket_lock = Lock()
def upload_file(root, progress_var, percentage_label, directory_display, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn):
    try:
        # Check if SFTP session is active
        if connection.sftp is None:
            messagebox.showerror("Upload Error", "Not connected to the server.")
            return
        
        # Default remote directory path
        default_path = f"/projects/bddu/data_setup/data"
        Thread(target=features.display.display_directories, args = (default_path, directory_display)).start()

        # Open a file dialog to select a file
        file_paths = filedialog.askopenfilename(multiple = True)
        if file_paths: 
            # Ask the user for a subdirectory where the file will be uploaded, appended to the default path
            subdir = components.menu.open_popup(root, default_path, "Upload Directory", "Upload", "Select the subdirectory path (root)")
            if subdir == "Cancelled":
                return
            elif subdir:
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
                    connection.sftp.stat(remote_path)  # Check if the remote file exists
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
                thread = Thread(target=upload_file_thread, args=(file, remote_path, file_size, root, progress_var, percentage_label))
                utils.buttons_util.disable_buttons(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)
                thread.start()
                threads.append(thread)

        if threads:
            utils.threads_utils.check_threads(threads, "Upload", remote_dir, root, directory_display, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)                

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
                connection.sftp.stat(path)
            except FileNotFoundError:
                connection.sftp.mkdir(path)

def upload_file_thread(file_path, remote_path, file_size, root, progress_var, percentage_label):
    with socket_lock:
        try:
            def progress_callback(transferred, total):
                # Calculate the progress percentage
                progress = (transferred / file_size) * 100
                # Update the progress on the main thread
                root.after(0, utils.progress_bar_utils.update_progress_bar, root, progress, progress_var, percentage_label)

            with open(file_path, 'rb') as file_handle:
                connection.sftp.putfo(file_handle, remote_path, callback=progress_callback)
            # Reset progress bar and percentage label
            root.after(0, utils.progress_bar_utils.update_progress_bar, root, 0, progress_var, percentage_label)
        
        except Exception as e:
            root.after(0, messagebox.showerror, "Upload Error", str(e))