from stat import S_ISDIR
import posixpath

import connection

def calculate_directory_size(remote_path):
    """Calculate total size of all files in the directory recursively."""
    total_size = 0
    try:
        for item in connection.sftp.listdir_attr(remote_path):
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
        return S_ISDIR(connection.sftp.stat(remote_path).st_mode)
    except IOError:
        return False