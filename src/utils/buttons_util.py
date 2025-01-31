import tkinter as tk

def enable_buttons(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn):
    upload_btn.config(state=tk.NORMAL)
    download_btn.config(state=tk.NORMAL)
    delete_btn.config(state=tk.NORMAL)
    manage_folders_btn.config(state=tk.NORMAL)
    disconnect_btn.config(state=tk.NORMAL)
    stream_preview_btn.config(state=tk.NORMAL)

def disable_buttons(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn):
    upload_btn.config(state=tk.DISABLED)
    download_btn.config(state=tk.DISABLED)
    delete_btn.config(state=tk.DISABLED)
    manage_folders_btn.config(state=tk.DISABLED)
    disconnect_btn.config(state=tk.DISABLED)
    stream_preview_btn.config(state=tk.DISABLED)

