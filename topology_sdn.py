#!/usr/bin/env python3
"""
Diamond topology for the Reliable UDP Transfer project (OpenFlow / SDN version).

        primary (5% loss)
      +------ s2 ------+
h1 -- s1                s4 -- h2
      +------ s3 ------+
        backup (clean)

s1 = ingress switch, s2 = primary-path switch, s3 = backup-path switch,
s4 = egress switch. All links are point-to-point. h1 and h2 are in ONE
subnet (10.0.0.0/24) and have ONE interface each, so no IP/route juggling.

Port numbers are fixed on purpose - the Ryu controller relies on them.

  s1: 1=h1   2=s2   3=s3
  s2: 1=s1   2=s4
  s3: 1=s1   2=s4
  s4: 1=h2   2=s2   3=s3

Run (controller first, in another terminal):
  ryu-manager controller/failover_controller.py
  sudo python3 topology_sdn.py
"""
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

H1_MAC = '00:00:00:00:00:01'
H2_MAC = '00:00:00:00:00:02'


def build():
    net = Mininet(controller=None, switch=OVSKernelSwitch,
                  link=TCLink, autoSetMacs=False)

    info('*** Adding controller (Ryu on 127.0.0.1:6653)\n')
    net.addController('c0', controller=RemoteController,
                      ip='127.0.0.1', port=6653)

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac=H1_MAC)
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac=H2_MAC)

    info('*** Adding switches\n')
    sw = {}
    for i in range(1, 5):
        sw[i] = net.addSwitch('s%d' % i, protocols='OpenFlow13',
                              dpid='%016x' % i)
    s1, s2, s3, s4 = sw[1], sw[2], sw[3], sw[4]

    info('*** Adding links (explicit port numbers)\n')
    net.addLink(h1, s1, port2=1)
    # Primary path, 5% artificial loss (applied on this link)
    net.addLink(s1, s2, port1=2, port2=1, loss=5)
    net.addLink(s2, s4, port1=2, port2=2)
    # Backup path
    net.addLink(s1, s3, port1=3, port2=1)
    net.addLink(s3, s4, port1=2, port2=3)
    net.addLink(h2, s4, port2=1)

    return net, h1, h2


def main():
    net, h1, h2 = build()
    net.start()

    # Static ARP: the diamond has loops, so we must never flood ARP.
    h1.cmd('arp -s 10.0.0.2 %s' % H2_MAC)
    h2.cmd('arp -s 10.0.0.1 %s' % H1_MAC)

    # sender.c option 2 ("Network Transfer") sends to 10.0.4.2, so give h2
    # that extra address. Then sender.c / receiver.c need NO changes.
    h2.cmd('ip addr add 10.0.4.2/32 dev h2-eth0')
    h1.cmd('ip route add 10.0.4.2/32 dev h1-eth0')
    h1.cmd('arp -s 10.0.4.2 %s' % H2_MAC)

    info('\n*** Useful CLI commands:\n')
    info('    h1 ping -c 3 h2\n')
    info('    link s1 s2 down     (kill primary path)\n')
    info('    link s1 s2 up       (restore primary path)\n')
    info('    sh ovs-ofctl -O OpenFlow13 dump-flows s1\n\n')
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    main()
