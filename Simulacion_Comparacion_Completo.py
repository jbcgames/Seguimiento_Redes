import simpy
import matplotlib.pyplot as plt
import pandas as pd
import random
import os

# Crear la carpeta "Resultados" si no existe
if not os.path.exists("Resultados"):
    os.makedirs("Resultados")

class TCPBase:
    def __init__(self, env, name, data_rate, max_window_size, loss_frequency):
        self.env = env
        self.name = name
        self.data_rate = data_rate
        self.window_size = 1
        self.max_window_size = max_window_size
        self.packets_sent = 0
        self.packets_lost = 0
        self.acknowledged_packets = 0
        self.total_delay = 0
        self.num_delays = 0
        self.window_sizes = []
        self.packets_sent_over_time = []
        self.times = []
        self.loss_frequency = loss_frequency
        self.env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(1 / self.data_rate)
            self.total_delay += (1 / self.data_rate)
            self.num_delays += 1
            self.packets_sent += self.window_size
            self.window_sizes.append(self.window_size)
            self.packets_sent_over_time.append(self.packets_sent / self.env.now if self.env.now > 0 else 0)
            self.times.append(self.env.now)
            print(f"{self.env.now}: {self.name} sent {self.window_size} packets (Window size: {self.window_size})")

            # Simulating packet loss based on the given frequency
            if self.env.now % self.loss_frequency == 0:
                print(f"{self.env.now}: {self.name} experienced packet loss")
                self.on_packet_loss()
            else:
                self.on_ack_received()

    def on_ack_received(self):
        pass

    def on_packet_loss(self):
        pass

    def get_metrics(self):
        utilization = (self.acknowledged_packets / self.packets_sent) if self.packets_sent > 0 else 0
        packet_loss_rate = (self.packets_lost / self.packets_sent) if self.packets_sent > 0 else 0
        avg_delay = (self.total_delay / self.num_delays) if self.num_delays > 0 else 0
        delay_stability = avg_delay  # Assuming delay stability is represented by average delay
        throughput = self.acknowledged_packets / self.env.now if self.env.now > 0 else 0

        return {
            "Name": self.name,
            "Utilization": utilization,
            "Packet Loss Rate": packet_loss_rate,
            "Throughput": throughput,
        }

class TCPTahoe(TCPBase):
    def on_ack_received(self):
        if self.window_size < self.max_window_size:
            if self.window_size < 16:
                # Slow start phase
                self.window_size *= 2
            else:
                # Congestion avoidance phase
                self.window_size += 1
        self.window_size = min(self.window_size, self.max_window_size)
        self.acknowledged_packets += self.window_size

    def on_packet_loss(self):
        self.packets_lost += 1
        self.window_size = 1

class TCPReno(TCPBase):
    def __init__(self, env, name, data_rate, max_window_size, loss_frequency):
        super().__init__(env, name, data_rate, max_window_size, loss_frequency)
        self.threshold = 16

    def on_ack_received(self):
        if self.window_size < self.threshold:
            # Slow start phase
            self.window_size *= 2
        else:
            # Congestion avoidance phase
            self.window_size += 1
        self.window_size = min(self.window_size, self.max_window_size)
        self.acknowledged_packets += self.window_size

    def on_packet_loss(self):
        self.packets_lost += 1
        self.threshold = max(self.window_size // 2, 1)
        self.window_size = self.threshold  # Fast recovery

class TCPBBR(TCPBase):
    def __init__(self, env, name, data_rate, max_window_size, loss_frequency):
        super().__init__(env, name, data_rate, max_window_size, loss_frequency)
        self.bandwidth_estimate = 20  # Initial bandwidth estimate

    def on_ack_received(self):
        # BBR adjusts window size based on estimated bandwidth and RTT
        self.bandwidth_estimate = max(self.bandwidth_estimate, self.window_size / (self.total_delay / self.num_delays if self.num_delays > 0 else 1))
        self.window_size = min(int(self.bandwidth_estimate), self.max_window_size)
        self.acknowledged_packets += self.window_size

    def on_packet_loss(self):
        self.packets_lost += 1
        # In BBR, packet loss does not directly affect the window size as in Reno or Tahoe

# Running multiple simulations with different packet loss frequencies
all_metrics = []

for loss_frequency in range(1, 26):  # Varying loss frequency from 1 to 25
    env = simpy.Environment()

    # Creating instances for TCP Tahoe, TCP Reno, and TCP BBR
    tcp_tahoe = TCPTahoe(env, "TCP Tahoe", data_rate=1, max_window_size=64, loss_frequency=loss_frequency)
    tcp_reno = TCPReno(env, "TCP Reno", data_rate=1, max_window_size=64, loss_frequency=loss_frequency)
    tcp_bbr = TCPBBR(env, "TCP BBR", data_rate=1, max_window_size=64, loss_frequency=loss_frequency)

    # Running the simulation
    env.run(until=50)

    # Collecting metrics for each TCP algorithm
    for tcp in [tcp_tahoe, tcp_reno, tcp_bbr]:
        metrics = tcp.get_metrics()
        metrics["Loss Frequency"] = loss_frequency
        all_metrics.append(metrics)

    # Plotting results with assigned colors and saving each figure
    tcp_algorithms = [tcp_tahoe, tcp_reno, tcp_bbr]
    colors = ['blue', 'green', 'orange']  # Assign different colors to each TCP variant

    plt.figure(figsize=(20, 15))
    plt.suptitle(f'TCP Algorithms Simulation Results with packet loss frequency {loss_frequency}', fontsize=16)
    plt.subplots_adjust(left=0.038, bottom=0.04, right=0.979, top=0.9, wspace=0.236, hspace=0.714)

    for idx, (tcp, color) in enumerate(zip(tcp_algorithms, colors)):
        plt.subplot(3, 3, idx + 1)
        plt.plot(tcp.times, tcp.window_sizes, label=f'{tcp.name} Window Size', color=color)
        plt.xlabel('Time (s)')
        plt.ylabel('Window Size')
        plt.title(f'{tcp.name} Window Size Over Time')
        plt.legend()

        plt.subplot(3, 3, idx + 4)
        plt.plot(tcp.times, tcp.packets_sent_over_time, label=f'{tcp.name} Packets Sent (Avg)', color=color)
        plt.xlabel('Time (s)')
        plt.ylabel('Average Packets Sent')
        plt.title(f'{tcp.name} Average Packets Sent Over Time')
        plt.legend()

        throughput_over_time = [tcp.acknowledged_packets / t if t > 0 else 0 for t in tcp.times]
        plt.subplot(3, 3, idx + 7)
        plt.plot(tcp.times, throughput_over_time, label='Throughput', color=color)
        plt.xlabel('Time (s)')
        plt.ylabel('Throughput (packets/s)')
        plt.title(f'{tcp.name} Throughput Over Time')
        plt.legend()

    # Saving each figure to an image file in the "Resultados" folder
    plt.savefig(f'Resultados/tcp_simulation_results_loss_frequency_{loss_frequency}.png')
    plt.close()

# Saving metrics to an Excel file
metrics_df = pd.DataFrame(all_metrics)
metrics_df.to_excel('Resultados/tcp_simulation_metrics.xlsx', index=False)
print("Simulation metrics saved to 'Resultados/tcp_simulation_metrics.xlsx'")