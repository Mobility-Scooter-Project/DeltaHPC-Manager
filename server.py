from flask import Flask, jsonify, request, session
import paramiko
from paramiko.sftp_client import SFTPClient
from stat import S_ISDIR
from flask_session import Session
from paramiko.ssh_exception import SSHException

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

def duo_authentication_handler(title, instructions, fields):
    responses = []
    for field in fields:
        prompt = field[0].strip()
        if "password" in prompt.lower():
            responses.append(session.get('password'))  # Get password from session
        elif "passcode or option" in prompt.lower():
            responses.append("1")  # Adjust based on actual Duo prompts
        else:
            raise SSHException(f"Unexpected prompt: {prompt}")
    return responses

def connect_to_server(username, password):
    global client, sftp, transport
    try:
        # Fixed hostname for Delta HPC server
        hostname = "login.delta.ncsa.illinois.edu"

        # Initialize Paramiko Transport object
        transport = paramiko.Transport((hostname, 22))
        transport.connect(username=username, password=password)

        # Perform interactive authentication with Duo MFA
        transport.auth_interactive(username, duo_authentication_handler)

        # Initialize Paramiko SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client._transport = transport

        # Initialize the SFTP session
        sftp = client.open_sftp()

        # Store sftp in session
        session['sftp'] = True
        return True
    except paramiko.ssh_exception.AuthenticationException as e:
        return f"Authentication failed: {str(e)}"
    except paramiko.ssh_exception.SSHException as e:
        return f"SSH Error: {str(e)}"
    except Exception as e:
        return f"Connection Error: {str(e)}"

@app.route('/connect', methods=['POST'])
def connect():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    session['username'] = username
    session['password'] = password

    result = connect_to_server(username, password)
    if result is True:
        return jsonify({"message": "Successfully connected to the server!"})
    else:
        return jsonify({"error": result}), 500

def list_files_and_folders(remote_dir):
    """Lists files and folders in a remote directory."""
    try:
        connected = session.get('sftp')
        if not connected:
            return {'error': 'Not connected to SFTP server'}
        global sftp
        if sftp is None:
            return {'error': 'SFTP session not initialized'}
        
        items = sftp.listdir_attr(remote_dir)
        result = []
        for item in items:
            item_info = {
                'name': item.filename,
                'type': 'directory' if S_ISDIR(item.st_mode) else 'file',
                'size': item.st_size,
                'modified_time': item.st_mtime
            }
            result.append(item_info)
        return result
    except Exception as e:
        return {'error': str(e)}

@app.route('/files', methods=['GET'])
def get_files():
    if 'sftp' not in session:
        return jsonify({'error': 'Not connected'}), 401

    folder = request.args.get('folder', '/projects/bddu/data')
    files_and_folders = list_files_and_folders(folder)
    return jsonify(files_and_folders)



@app.route('/disconnect', methods=['POST'])
def disconnect():
    global client, sftp, transport
    try:
        if sftp:
            sftp.close()
            session.pop('sftp', None)
        if client:
            client.close()
        if transport:
            transport.close()
        return jsonify({"message": "Successfully disconnected from the server!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
