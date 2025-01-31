from tkinter import messagebox

import features.display
import utils.buttons_util

def check_threads(threads, action, remote_dir, root, directory_display, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn):
    alive_threads = []
    for thread in threads:
        if thread.is_alive():
            alive_threads.append(thread)

    if alive_threads:
        # If the thread is still running, check again after 100ms
        root.after(100, check_threads, alive_threads, action, remote_dir, root, directory_display, upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)
    else:
        root.after(0, messagebox.showinfo, action, f"File(s) successfully {action.lower()}ed")
        features.display.display_directories(remote_dir, directory_display)
        utils.buttons_util.enable_buttons(upload_btn, download_btn, delete_btn, manage_folders_btn, disconnect_btn, stream_preview_btn)