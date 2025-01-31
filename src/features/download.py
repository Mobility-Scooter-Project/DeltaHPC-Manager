from tkinter import filedialog, messagebox
import os
from threading import Thread, Lock
import posixpath

import connection
import components.menu
import utils.threads_utils
import utils.directory_utils
import utils.progress_bar_utils
import utils.buttons_util

socket_lock = Lock()
def download_file(root, progress_var, percentage_label, directory_display, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn):
    try:
        # Check if SFTP session is active
        if connection.sftp is None:
            messagebox.showerror("Download Error", "Not connected to the server.")
            return
        
        # Default remote directory path
        default_path = f"/projects/bddu/data_setup/data"

        # Ask the user for the remote path of the file to be downloaded         
        file_string = components.menu.open_popup(root, default_path, "Remote Path", "Download", f"Select the remote path of the file to download (root):")
        if file_string == "Cancelled":
            return

        remote_files = []
        if file_string:
            remote_files = file_string.split(", ")

        threads = []
        for remote_file in remote_files:
            if remote_file:
                remote_path = posixpath.join(default_path, remote_file)
                # Check if the remote path is a directory
                if not utils.directory_utils.is_directory(remote_path):
                    # Open a file dialog to select a save location
                    file_path = filedialog.asksaveasfilename(initialfile=os.path.basename(remote_path))
                    if file_path:
                        # Initialize the progress bar and percentage label
                        progress_var.set(0)
                        percentage_label.config(text="0%")
                        # Start download in a separate thread to avoid blocking the GUI
                        thread = Thread(target=download_file_thread, args=(remote_path, file_path, root, progress_var, percentage_label))
                        utils.buttons_util.disable_buttons(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)
                        thread.start()
                        threads.append(thread)
                else:
                    messagebox.showerror("Download Error", f"Cannot download the subdirectory '{remote_file}'")

                                       
        if threads:
            utils.threads_utils.check_threads(threads, "Download", default_path, root, directory_display, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)   

    except Exception as e:
        messagebox.showerror("Download Error", str(e))

def download_file_thread(remote_path, file_path, root, progress_var, percentage_label):    
    with socket_lock:
        try:    
            # root.mainloop()            
            def progress_callback(transferred, total):
                # Calculate the progress percentage
                progress = (transferred / total) * 100
                # Update the progress on the main thread
                root.after(0, utils.progress_bar_utils.update_progress_bar, root, progress, progress_var, percentage_label)

            # Download the file
            with open(file_path, 'wb') as file_handle:
                connection.sftp.getfo(remote_path, file_handle, callback=progress_callback)
            # Reset progress bar and percentage label
            root.after(0, utils.progress_bar_utils.update_progress_bar, root, 0, progress_var, percentage_label)
        except Exception as e:
            messagebox.showerror("Download Error", str(e))