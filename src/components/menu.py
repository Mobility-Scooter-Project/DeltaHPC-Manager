import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import posixpath

import connection
import features.preview
import utils.directory_utils

def open_popup(root, default_path, title, feature, text):
    # Create a window for the dropdown popup
    top = tk.Toplevel(root)
    top.geometry("500x100")
    top.title(title)
    
    # Initialize the selected file 
    selected_file = ""

    # Get the names of the files/folders 
    folder_contents = connection.sftp.listdir_attr(default_path)
    file_names = []
    num_folder = 0

    # Get the names of folder contents
    for name in folder_contents:
        remote_path = posixpath.join(default_path, name.filename)
        if (feature == "Upload" or feature == "Display"):
            if utils.directory_utils.is_directory(remote_path):
                file_names.append(name.filename)
                num_folder += 1
        else:
            if utils.directory_utils.is_directory(remote_path):
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
            if option == "Open" and utils.directory_utils.is_directory(remote_path):
                # Display error if the user tries to open a file
                file_name = open_popup(root, remote_path, title, feature, f"Select the remote path of the file to {feature.lower()} ({path_name}): ")
                if file_name and file_name != "Cancelled":
                    selected_file += f"/{file_name}"   
                elif file_name:
                    selected_file = "Cancelled"
            elif option == "Open":
                messagebox.showerror("Open Error", f"Cannot open the file '{selected_file}'")
                selected_file = "" 
            
            if option == "View":
                features.preview.stream_video_preview(selected_file)
                selected_file = ""
        else:
            top.destroy()

    def create_subdirectory():
        nonlocal selected_file
        top.destroy()
        selected_file = simpledialog.askstring("New Subdirectory", f"Enter the subdirectory name ({default_path}):")
        if not selected_file:
            selected_file = "Cancelled"

    def cancel_popup():
        nonlocal selected_file
        top.destroy()
        selected_file = "Cancelled"

    # Add an intruction text for the popup
    tk.Label(top, text=text, font=("TkDefaultFont")).place(x=10, y=10)

    # Create the dropdown component
    dropdown = ttk.Combobox(top, state="readonly", values=file_names, width="75")
    dropdown.place(x=10, y=35)

    # A button for selecting a file/folder 
    tk.Button(top, text=feature, command=lambda: get_selection(feature)).place(x=20, y=65)

    # A button for canceling the popup
    tk.Button(top, text="Cancel", command=cancel_popup).place(x=190, y=65)
        
    # A button for opening a subdirectory 
    open_btn = tk.Button(top, text="Open", command=lambda: get_selection("Open"))
    open_btn.place(x=250, y=65)

    # A button for creating a new subdirectory (only for the upload feature)
    if feature == "Upload":
        tk.Button(top, text="Create a new subdirectory", command=lambda: create_subdirectory()).place(x=300, y=65)
    
    if feature == "Download":
        tk.Button(top, text="Preview Video", command=lambda: get_selection("View")).place(x=300, y=65)

    # If there is no subdirectories, disable the open button
    if num_folder == 0:
        open_btn.config(state=tk.DISABLED)    
    
    top.wait_window()
    return selected_file