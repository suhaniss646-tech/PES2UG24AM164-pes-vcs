from collections import defaultdict
from datetime import datetime

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.lib.packet import arp
from os_ken.lib.packet import ethernet
from os_ken.lib.packet import ether_types
from os_ken.lib.packet import icmp
from os_ken.lib.packet import ipv4
from os_ken.lib.packet import ipv6
from os_ken.lib.packet import packet
from os_ken.lib.packet import tcp
from os_ken.lib.packet import udp
from os_ken.ofproto import ofproto_v1_3


class TrafficClassifier(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficClassifier, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.proto_stats = defaultdict(lambda: {"packets": 0, "bytes": 0})
        self.packet_log = []
        self.monitor_thread = hub.spawn(self._print_stats_periodically)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)
        self.logger.info("Switch %s connected. Table-miss flow installed.", datapath.id)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        instructions = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]

        if buffer_id is not None:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                buffer_id=buffer_id,
                priority=priority,
                match=match,
                instructions=instructions,
            )
        else:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                priority=priority,
                match=match,
                instructions=instructions,
            )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        dst = eth.dst
        src = eth.src

        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        protocol_name = self.classify_packet(pkt)
        if protocol_name in ("IPV6", "NOISE"):
            return

        packet_length = len(msg.data)
        self.update_stats(protocol_name, packet_length)
        self.record_packet(protocol_name, src, dst, packet_length)

        self.logger.info(
            "Packet classified: switch=%s src=%s dst=%s protocol=%s size=%sB",
            dpid,
            src,
            dst,
            protocol_name,
            packet_length,
        )

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    def classify_packet(self, pkt):
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        if eth_pkt and eth_pkt.dst.startswith("33:33:"):
            return "NOISE"

        if pkt.get_protocol(arp.arp):
            return "ARP"

        if pkt.get_protocol(ipv6.ipv6):
            return "IPV6"

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return "OTHER"

        if pkt.get_protocol(tcp.tcp):
            return "TCP"
        if pkt.get_protocol(udp.udp):
            return "UDP"
        if pkt.get_protocol(icmp.icmp):
            return "ICMP"
        return "IP_OTHER"

    def update_stats(self, protocol_name, packet_length):
        self.proto_stats[protocol_name]["packets"] += 1
        self.proto_stats[protocol_name]["bytes"] += packet_length

    def record_packet(self, protocol_name, src, dst, packet_length):
        self.packet_log.append(
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "protocol": protocol_name,
                "src": src,
                "dst": dst,
                "bytes": packet_length,
            }
        )
        if len(self.packet_log) > 20:
            self.packet_log.pop(0)

    def _print_stats_periodically(self):
        while True:
            hub.sleep(10)
            total_packets = sum(item["packets"] for item in self.proto_stats.values())
            if total_packets == 0:
                self.logger.info("No classified traffic seen yet.")
                continue

            self.logger.info("========== Traffic Classification Summary ==========")
            for protocol_name, stats in sorted(self.proto_stats.items()):
                percentage = (stats["packets"] / float(total_packets)) * 100
                self.logger.info(
                    "%s -> packets=%s bytes=%s distribution=%.2f%%",
                    protocol_name,
                    stats["packets"],
                    stats["bytes"],
                    percentage,
                )

            self.logger.info("Recent packet classifications:")
            for entry in self.packet_log[-5:]:
                self.logger.info(
                    "[%s] %s %s -> %s (%sB)",
                    entry["time"],
                    entry["protocol"],
                    entry["src"],
                    entry["dst"],
                    entry["bytes"],
                )
