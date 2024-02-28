import tkinter as tk
from tkinter import ttk, scrolledtext
from paramiko import SSHClient, AutoAddPolicy, AuthenticationException, SSHException
from threading import Thread
from queue import Queue
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class ServerMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Server Monitor")
        self.root.state('zoomed')
        # Input fields, button, and output text
        self.hostname_label = ttk.Label(root, text="Hostname:")
        self.hostname_entry = ttk.Entry(root)
        self.port_label = ttk.Label(root, text="Port:")
        self.port_entry = ttk.Entry(root)
        self.username_label = ttk.Label(root, text="Username:")
        self.username_entry = ttk.Entry(root)
        self.password_label = ttk.Label(root, text="Password:")
        self.password_entry = ttk.Entry(root, show="*")
        self.monitor_button = ttk.Button(root, text="Start Monitoring", command=self.start_monitoring)
        self.stop_button = ttk.Button(root, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.show_process_button = ttk.Button(root, text="Show Process List", command=self.show_process_list)
        self.exit_button = ttk.Button(root, text="Exit", command=self.exit_program)

        # Create a Figure and set it up for plotting
        self.fig, (self.ax_cpu, self.ax_memory, self.ax_network, self.ax_disk, self.ax_process) = plt.subplots(1, 5, figsize=(20, 4),
                                                                                                      tight_layout=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=6, column=0, columnspan=5, padx=5, pady=5, sticky="nsew")

        # Store metrics data
        self.time_points = []
        self.cpu_usage_data = []
        self.memory_usage_data = []
        self.network_data_sent = []
        self.network_data_received = []
        self.disk_usage_data = []
        self.process_count_data = []

        # SSH Client
        self.ssh_client = None

        # Monitor thread
        self.monitor_thread = None

        # Queue for communication between threads
        self.queue = Queue()

        # Flag to indicate whether the monitoring thread is running
        self.monitoring_running = False

        # Configure grid row and column weights for dynamic resizing
        for i in range(7):
            self.root.grid_rowconfigure(i, weight=1)
        for i in range(5):
            self.root.grid_columnconfigure(i, weight=1)

        # Grid layout
        self.hostname_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.hostname_entry.grid(row=0, column=1, padx=5, pady=5)
        self.port_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)
        self.username_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.username_entry.grid(row=2, column=1, padx=5, pady=5)
        self.password_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.password_entry.grid(row=3, column=1, padx=5, pady=5)
        self.monitor_button.grid(row=4, column=0, pady=10)
        self.stop_button.grid(row=4, column=1, pady=10)
        self.show_process_button.grid(row=4, column=2, pady=10)
        self.exit_button.grid(row=5, column=0, columnspan=3, pady=10)

    def start_monitoring(self):
        hostname = self.hostname_entry.get()
        port = int(self.port_entry.get())
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not self.monitoring_running:
            # Tạo một luồng mới cho quá trình giám sát
            self.monitor_thread = Thread(target=self.monitor_server, args=(hostname, port, username, password))
            self.monitor_thread.start()

            # Enable Stop Monitoring button and disable Start Monitoring button
            self.stop_button["state"] = tk.NORMAL
            self.monitor_button["state"] = tk.DISABLED
            self.monitoring_running = True
            print("Monitoring started...")
        else:
            print("Monitoring is already running.")

    def stop_monitoring(self):
        # Gửi thông điệp để dừng giám sát
        self.queue.put("STOP_MONITORING")

    def show_process_list(self):
        if self.ssh_client:
            stdin, stdout, stderr = self.ssh_client.exec_command("ps aux")
            process_list = stdout.read().decode()
            self.show_result_window(process_list)


    def show_result_window(self, result_text):
        result_window = tk.Toplevel(self.root)
        result_window.title("Process List")

        text_area = scrolledtext.ScrolledText(result_window, wrap=tk.WORD, width=80, height=30)
        text_area.insert(tk.INSERT, result_text)
        text_area.grid(row=0, column=0, padx=10, pady=10)

    def exit_program(self):
        # Kiểm tra xem luồng giám sát đang chạy không
        if self.monitor_thread and self.monitor_thread.is_alive():
            # Gửi thông điệp để dừng giám sát
            self.queue.put("STOP_MONITORING")

            # Đợi cho đến khi luồng giám sát kết thúc
            self.monitor_thread.join()

        # Dừng chương trình hoàn toàn và thoát
        import sys
        sys.exit()

    def monitor_server(self, hostname, port, username, password):
        self.ssh_client = SSHClient()
        self.ssh_client.set_missing_host_key_policy(AutoAddPolicy())

        try:
            self.ssh_client.connect(hostname, port, username, password)
            commands = ['uptime', 'df -h', 'free -m', 'cat /proc/net/dev']

            while True:
                if not self.queue.empty():
                    command = self.queue.get()
                    if command == "STOP_MONITORING":
                        break

                cpu_usage = self.get_cpu_usage(self.ssh_client)
                memory_usage = self.get_memory_usage(self.ssh_client)
                network_sent, network_received = self.get_network_data(self.ssh_client)
                disk_usage = self.get_disk_usage(self.ssh_client)
                process_count = self.get_process_count(self.ssh_client)

                self.time_points.append(time.strftime("%H:%M:%S"))
                self.cpu_usage_data.append(cpu_usage)
                self.memory_usage_data.append(memory_usage)
                self.network_data_sent.append(network_sent)
                self.network_data_received.append(network_received)
                self.disk_usage_data.append(disk_usage)
                self.process_count_data.append(process_count)

                self.update_graph()
                print(f"CPU Usage: {cpu_usage}%\nMemory Usage: {memory_usage} MB\n"
                      f"Network Sent: {network_sent} bytes\nNetwork Received: {network_received} bytes\n"
                      f"Disk Usage: {disk_usage}%\nNumber of Processes: {process_count}")

                time.sleep(5)

        except AuthenticationException:
            print("Authentication failed. Please check your credentials.")
        except SSHException as e:
            print(f"Error connecting to the server: {str(e)}")
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")

        finally:
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None

            self.monitor_button["state"] = tk.NORMAL
            self.stop_button["state"] = tk.DISABLED
            self.show_process_button["state"] = tk.NORMAL

            self.monitoring_running = False
            print("Monitoring stopped.")

    def get_network_data(self, ssh):
        stdin, stdout, stderr = ssh.exec_command("cat /proc/net/dev")
        network_data = stdout.read().decode().strip().split()

        try:
            if len(network_data) >= 1:
                network_sent = int(network_data[9])
                network_received = int(network_data[1])
                return network_sent, network_received
        except ValueError:
            pass

        return 0, 0

    def get_cpu_usage(self, ssh):
        stdin, stdout, stderr = ssh.exec_command("top -bn1 | awk 'NR>7{s+=$9} END {print s}'")
        return float(stdout.read().decode().strip())

    def get_memory_usage(self, ssh):
        stdin, stdout, stderr = ssh.exec_command("free -m | awk 'NR==2{print $3}'")
        return int(stdout.read().decode().strip())

    def get_disk_usage(self, ssh):
        stdin, stdout, stderr = ssh.exec_command("df -h / | awk 'NR==2{printf \"%s,%s\", $3, $4}'")
        disk_usage_str = stdout.read().decode().strip()

        try:
            used_gb, free_gb = map(str, disk_usage_str.split(','))
            return used_gb, free_gb
        except ValueError:
            pass

        return "0", "0"

    def get_process_count(self, ssh):
        stdin, stdout, stderr = ssh.exec_command("ps aux | wc -l")
        return int(stdout.read().decode().strip())

    def plot_network_chart(self):
        self.ax_network.clear()
        network_sent = max(0, self.network_data_sent[-1])
        network_received = max(0, self.network_data_received[-1])
        self.ax_network.bar(['Sent'], [network_sent], color='orange', label='Sent')
        self.ax_network.bar(['Received'], [network_received], color='lightblue', label='Received', bottom=network_sent)
        self.ax_network.set_ylabel('Network Usage (Bytes)')
        self.ax_network.set_title('Network Usage')
        self.ax_network.legend()
        self.canvas.draw()

    def plot_disk_chart(self):
        self.ax_disk.clear()

        used_gb, free_gb = self.disk_usage_data[-1]

        used_gb_value = float(used_gb[:-1]) if used_gb[-1] == 'G' else float(used_gb)
        free_gb_value = float(free_gb[:-1]) if free_gb[-1] == 'G' else float(free_gb)

        self.ax_disk.bar(['Used'], [used_gb_value], color='lightcoral', label='Used')
        self.ax_disk.bar(['Free'], [free_gb_value], color='lightblue', label='Free', bottom=used_gb_value)

        self.ax_disk.set_ylabel('Disk Usage (GB)')
        self.ax_disk.set_title('Disk Usage')
        self.ax_disk.legend()
        self.canvas.draw()

    def plot_process_chart(self):
        self.ax_process.clear()
        process_count = self.process_count_data[-1]
        self.ax_process.bar(['Process Count'], [process_count], color='gold')
        self.ax_process.set_ylabel('Number of Processes')
        self.ax_process.set_title('Process Count')
        self.canvas.draw()

    def update_graph(self):
        self.root.after(0, self.plot_pie_chart)
        self.root.after(0, self.plot_network_chart)
        self.root.after(0, self.plot_disk_chart)
        self.root.after(0, self.plot_process_chart)


    def plot_pie_chart(self):
        cpu_values = [max(0, float(100 - self.cpu_usage_data[-1])), max(0, float(self.cpu_usage_data[-1]))]
        self.ax_cpu.clear()
        try:
            self.ax_cpu.pie(cpu_values, labels=['', f'Usage: {self.cpu_usage_data[-1]:.1f}%'], autopct='%1.1f%%',
                            startangle=90, colors=['lightgray', 'lightblue'])
        except ValueError:
            pass
        self.ax_cpu.set_title('CPU Usage')

        self.ax_memory.clear()
        memory_value = max(0, float(self.memory_usage_data[-1]))
        self.ax_memory.bar(['Memory Usage'], [memory_value], color='lightgreen')
        self.ax_memory.set_ylabel('Memory Usage (MB)')
        self.ax_memory.set_title('Memory Usage')

        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = ServerMonitorApp(root)
    root.geometry("800x600")
    root.mainloop()
