import tkinter as tk
from tkinter import messagebox
from stat import S_ISDIR
import time
import posixpath

import components.menu
import connection

def manage_folders(root, directory_display):
    try:
        # Check if SFTP session is active
        if connection.sftp is None:
            messagebox.showerror("Folder Management Error", "Not connected to the server.")
            return

        # Default remote directory path
        default_path = f"/projects/bddu/data_setup/data"
        
        # Ask the user for the subdirectory to manage, appende  d to the default path
        subdir = components.menu.open_popup(root, default_path, "Remote Directory", "Display", "Select the subdirectory path (root)")
        if subdir == "Cancelled":
            return
        elif subdir:
            remote_dir = posixpath.join(default_path, subdir)
        else:
            remote_dir = default_path

        # Check if the directory exists
        try:
            connection.sftp.stat(remote_dir)
        except FileNotFoundError:
            messagebox.showerror("Folder Management Error", "The specified directory does not exist.")
            return

        display_directories(remote_dir, directory_display)

    except Exception as e:
        messagebox.showerror("Folder Management Error", str(e))

def display_directories(remote_dir, directory_display):
    # List directory contents
    folder_contents = connection.sftp.listdir_attr(remote_dir)

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
