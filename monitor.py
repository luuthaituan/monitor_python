import paramiko

def monitor_server(hostname, port, username, password):
    # Khởi tạo kết nối SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect using password authentication
        ssh.connect(hostname, port, username, password)

        # Danh sách các lệnh để giám sát hệ thống
        commands = ['uptime', 'df -h', 'free -m']

        for command in commands:
            stdin, stdout, stderr = ssh.exec_command(command)
            print(f'Output for {command}:')
            print(stdout.read().decode())
            print(stderr.read().decode())

    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your credentials.")

    finally:
        # Đóng kết nối SSH
        ssh.close()

# Sử dụng hàm với thông tin máy chủ của bạn
monitor_server('192.168.241.31', 22, 'thaituan', 'tuan89')
