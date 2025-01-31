import tkinter as tk
from tkinter import ttk, font

import connection
import features.display
import features.upload
import features.download
import features.delete
import features.preview

def server_connect():
    username = username_entry.get()
    password = password_entry.get()
    connection.connect_to_server(username, password, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)

def server_disconnect():
    connection.disconnect_from_server(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)

def display_dir():
    features.display.manage_folders(root, directory_display)

def upload():
    features.upload.upload_file(root, progress_var, percentage_label, directory_display, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)

def download():
    features.download.download_file(root, progress_var, percentage_label, directory_display, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)

def delete():
    features.delete.delete_file_or_folder(root, directory_display)

def preview():
    features.preview.stream_video_preview(root, "")

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
connect_btn = tk.Button(root, text="Connect", width=20, command=server_connect, font=font_txt)
connect_btn.pack(pady=10)

# Manage Folders button
manage_folders_btn = tk.Button(root, text="List Directory Contents", width=20, state=tk.DISABLED, command=display_dir, font=font_txt)
manage_folders_btn.pack(pady=5)

# Upload button
upload_btn = tk.Button(root, text="Upload File(s)", width=20, state=tk.DISABLED, command=upload, font=font_txt)
upload_btn.pack(pady=5)

# Download button
download_btn = tk.Button(root, text="Download File", width=20, state=tk.DISABLED, command=download, font=font_txt)
download_btn.pack(pady=5)

# Delete button
delete_btn = tk.Button(root, text="Delete File/Folder", width=20, state=tk.DISABLED, command=delete, font=font_txt)
delete_btn.pack(pady=5)

# Stream preview video button
stream_preview_btn = tk.Button(root, text="Stream Preview Video", width=20, state=tk.DISABLED, command=preview, font=font_txt)
stream_preview_btn.pack(pady=5)

# Disconnect button
disconnect_btn = tk.Button(root, text="Disconnect", width=20, state=tk.DISABLED, command=server_disconnect, font=font_txt)
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

