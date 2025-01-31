def update_progress_bar(root, progress, progress_var, percentage_label):
    """Update the progress bar and percentage label."""
    progress_var.set(progress)
    percentage_label.config(text=f"{progress:.2f}%")
    root.update_idletasks()


