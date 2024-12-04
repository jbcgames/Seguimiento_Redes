import simpy
import matplotlib.pyplot as plt

class TCPReno:
    def __init__(self, env, name, data_rate, max_window_size):
        self.env = env
        self.name = name
        self.data_rate = data_rate
        self.window_size = 1
        self.max_window_size = max_window_size
        self.threshold = 16
        self.packets_sent = 0
        self.packets_lost = 0
        self.acknowledged_packets = 0
        self.recovery_time = []
        self.last_loss_time = None
        self.total_delay = 0
        self.num_delays = 0
        self.window_sizes = []
        self.packet_losses = []
        self.times = []
        self.env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(1 / self.data_rate)
            self.total_delay += (1 / self.data_rate)
            self.num_delays += 1
            self.packets_sent += self.window_size
            self.window_sizes.append(self.window_size)
            self.times.append(self.env.now)
            print(f"{self.env.now}: {self.name} sent {self.window_size} packets (Window size: {self.window_size})")

            # Simulating packet loss or congestion
            if self.packets_sent % 10 == 0:  # A simplistic way to introduce packet loss
                print(f"{self.env.now}: {self.name} experienced packet loss")
                self.packet_losses.append(self.env.now)
                self.on_packet_loss()
            else:
                self.on_ack_received()

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
        self.window_size = self.threshold  # Reno enters fast recovery by setting window size to threshold
        if self.last_loss_time is not None:
            recovery_duration = self.env.now - self.last_loss_time
            self.recovery_time.append(recovery_duration)
        self.last_loss_time = self.env.now

    def get_metrics(self):
        utilization = (self.acknowledged_packets / self.packets_sent) if self.packets_sent > 0 else 0
        packet_loss_rate = (self.packets_lost / self.packets_sent) if self.packets_sent > 0 else 0
        avg_delay = (self.total_delay / self.num_delays) if self.num_delays > 0 else 0
        delay_stability = avg_delay  # Assuming delay stability is represented by average delay
        avg_recovery_time = (sum(self.recovery_time) / len(self.recovery_time)) if len(self.recovery_time) > 0 else 0
        throughput = self.acknowledged_packets / self.env.now if self.env.now > 0 else 0

        return {
            "Utilization": utilization,
            "Packet Loss Rate": packet_loss_rate,
            "Average Delay": avg_delay,
            "Delay Stability": delay_stability,
            "Average Recovery Time": avg_recovery_time,
            "Throughput": throughput,
        }

# SimPy Environment
env = simpy.Environment()

# Creating TCP Reno instance
tcp_reno = TCPReno(env, "TCP Reno", data_rate=1, max_window_size=64)

# Running the simulation
env.run(until=50)

# Printing the results
metrics = tcp_reno.get_metrics()
print("\nSimulation Metrics:")
for key, value in metrics.items():
    print(f"{key}: {value}")

# Plotting results
plt.figure(figsize=(10, 6))

# Plot window size over time
plt.subplot(3, 1, 1)
plt.plot(tcp_reno.times, tcp_reno.window_sizes, label='Window Size')
plt.xlabel('Time (s)')
plt.ylabel('Window Size')
plt.title('TCP Reno Window Size Over Time')
plt.legend()

# Plot packet loss events
plt.subplot(3, 1, 2)
plt.scatter(tcp_reno.packet_losses, [1] * len(tcp_reno.packet_losses), color='red', label='Packet Loss')
plt.xlabel('Time (s)')
plt.ylabel('Packet Loss Event')
plt.title('Packet Loss Events Over Time')
plt.legend()

# Plot throughput over time
throughput_over_time = [tcp_reno.acknowledged_packets / t if t > 0 else 0 for t in tcp_reno.times]
plt.subplot(3, 1, 3)
plt.plot(tcp_reno.times, throughput_over_time, label='Throughput')
plt.xlabel('Time (s)')
plt.ylabel('Throughput (packets/s)')
plt.title('Throughput Over Time')
plt.legend()

plt.tight_layout()
plt.show()
