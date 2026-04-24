# Traffic Classification System using SDN

This is a simple college-project implementation of a traffic classification system using:

- `Mininet` for SDN network emulation
- `os-ken` as the SDN controller
- `OpenFlow 1.3` for switch-controller communication

The controller classifies packets by protocol type and maintains live traffic statistics for:

- `TCP`
- `UDP`
- `ICMP`

It also prints:

- packet classification results
- packet/byte counters
- traffic distribution percentages

## Project Files

- `controller.py` - os-ken controller for packet classification and statistics
- `topology.py` - Mininet topology with 1 switch and 3 hosts

## Ubuntu Setup

Install dependencies:

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch python3-pip iperf
python3 -m venv .venv
source .venv/bin/activate
pip install os-ken
```

## How to Run

Open 2 terminals and go to the project folder in both:

```bash
cd ~/Desktop/traffic-cl
```

In terminal 1, start the os-ken controller:

```bash
python3.10 -m os_ken.cmd.manager controller.py
```

In terminal 2, clean any old Mininet state and start the topology:

```bash
sudo mn -c
sudo python3 topology.py
```

Inside the Mininet CLI, run the following commands.

### ICMP traffic

```bash
pingall
```

### UDP traffic

```bash
h1 pkill iperf
h2 pkill iperf
h3 pkill iperf
h1 iperf -s -u -p 5001 &
h2 iperf -c 10.0.0.1 -u -p 5001 -b 1M -t 5
```

### TCP traffic

```bash
h3 iperf -s -p 5002 &
h2 iperf -c 10.0.0.3 -p 5002 -t 5
```

### Clean demo flow

```bash
pingall
h1 pkill iperf
h2 pkill iperf
h3 pkill iperf
h1 iperf -s -u -p 5001 &
h2 iperf -c 10.0.0.1 -u -p 5001 -b 1M -t 5
h3 iperf -s -p 5002 &
h2 iperf -c 10.0.0.3 -p 5002 -t 5
```

## Expected Output

In the os-ken controller terminal, you will see log lines such as:

- packet classification for each incoming packet
- summary of total packets and bytes per protocol
- traffic distribution percentage

Example categories:

- `ARP`
- `TCP`
- `UDP`
- `ICMP`
- `OTHER`

## Demo Flow for Presentation

1. Start the controller.
2. Start the Mininet topology.
3. Run `pingall` to show ICMP classification.
4. Run UDP `iperf` to show UDP classification.
5. Run TCP `iperf` to show TCP classification.
6. Show the controller log summary as proof of statistics and distribution analysis.

## Notes

- This project is designed for Ubuntu/Linux because Mininet runs natively there.
- Run Mininet with `sudo`.
- The controller uses port `6653`; if that port is busy, change it in `topology.py` and in the controller launch command if needed.
