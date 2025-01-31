from tkinter import messagebox
from threading import Thread
from stat import S_ISDIR
import posixpath

import connection
import components.menu
import features.display
import utils.directory_utils

def delete_file_or_folder(root, directory_display):
    try:
        # Check if SFTP session is active
        if connection.sftp is None:
            messagebox.showerror("Deletion Error", "Not connected to the server.")
            return

        # Default remote directory path
        default_path = f"/projects/bddu/data_setup/data"
        
        # Ask the user for the path of the file/folder to be deleted    
        paths_string = components.menu.open_popup(root, default_path, "Remote Path", "Delete", f"Select the remote path of the file to delete (root)")
        if paths_string == "Cancelled":
            return

        paths_to_delete = []
        if paths_string:
            paths_to_delete = paths_string.split(", ")

        for path_to_delete in paths_to_delete:
            if path_to_delete:
                remote_path = posixpath.join(default_path, path_to_delete)
                file_stat = connection.sftp.stat(remote_path)

                # Ask for user confirmation
                confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{remote_path}'?")
                if not confirm:
                    continue  # User canceled the deletion

                # If it's a directory, delete it recursively
                if S_ISDIR(file_stat.st_mode):
                    delete_directory_recursive(remote_path)
                else:
                    connection.sftp.remove(remote_path)  # If it's a file, delete it directly
                
                # Display the parent directory after deleting a file/folder
                updated_directory = "/".join(remote_path.rsplit("/", 1)[:-1])
                Thread(target=features.display.display_directories, args = (updated_directory, directory_display)).start()
                messagebox.showinfo("Deletion Complete", f"Successfully deleted '{remote_path}'")
    
    except Exception as e:
        messagebox.showerror("Deletion Error", str(e))

def delete_directory_recursive(remote_path):
    """Recursively delete a directory and all its contents."""
    for item in connection.sftp.listdir(remote_path):
        item_path = posixpath.join(remote_path, item)
        try:
            if utils.directory_utils.is_directory(item_path):
                delete_directory_recursive(item_path)  # Recursively delete subdirectory
            else:
                connection.sftp.remove(item_path)  # Delete file
        except Exception as e:
            messagebox.showerror("Deletion Error", f"Error deleting {item_path}: {str(e)}")
    connection.sftp.rmdir(remote_path)  # Delete the now-empty directory