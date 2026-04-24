from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.topo import Topo


class TrafficClassificationTopo(Topo):
    def build(self):
        s1 = self.addSwitch("s1")

        h1 = self.addHost("h1", ip="10.0.0.1/24")
        h2 = self.addHost("h2", ip="10.0.0.2/24")
        h3 = self.addHost("h3", ip="10.0.0.3/24")

        self.addLink(h1, s1, cls=TCLink, bw=10, delay="5ms")
        self.addLink(h2, s1, cls=TCLink, bw=10, delay="5ms")
        self.addLink(h3, s1, cls=TCLink, bw=10, delay="5ms")


def run():
    topo = TrafficClassificationTopo()
    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip="127.0.0.1", port=6653),
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True,
    )

    net.start()
    print("\nMininet topology is running.")
    print("Hosts: h1, h2, h3")
    print("Use the commands below inside the Mininet CLI to generate traffic:")
    print("  pingall")
    print("  h1 ping -c 4 h2")
    print("  h1 iperf -s -u &")
    print("  h2 iperf -c 10.0.0.1 -u -t 5")
    print("  h3 iperf -s &")
    print("  h2 iperf -c 10.0.0.3 -t 5")
    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run()
