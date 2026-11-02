from mininet.net import Mininet
from mininet.node import Node
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class LinuxRouter(Node):
    """A Node with IP forwarding enabled."""
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

def customNet():
    net = Mininet(link=TCLink)

    print("*** Adding Linux Routers")
    r1 = net.addHost('r1', cls=LinuxRouter, ip='10.0.1.254/24')
    r2 = net.addHost('r2', cls=LinuxRouter, ip='10.0.1.253/24')

    print("*** Adding Hosts")
    h1 = net.addHost('h1', ip='10.0.1.1/24', defaultRoute='via 10.0.1.254')
    # h2 will get its specific IPs during link creation below
    h2 = net.addHost('h2') 

    print("*** Creating Links (Subnets A, B, and C)")
    # Subnet A (10.0.1.0/24)
    net.addLink(h1, r1, intfName1='h1-eth0', intfName2='r1-eth0')
    net.addLink(h1, r2, intfName1='h1-eth1', intfName2='r2-eth0')
    
    # Subnet B (10.0.2.0/24) - Path 1 with 5% loss
    net.addLink(r1, h2, intfName1='r1-eth1', intfName2='h2-eth0', params1={'ip': '10.0.2.254/24'}, params2={'ip': '10.0.2.2/24'}, loss=5)
    
    # Subnet C (10.0.3.0/24) - Path 2 (Failover)
    net.addLink(r2, h2, intfName1='r2-eth1', intfName2='h2-eth1', params1={'ip': '10.0.3.254/24'}, params2={'ip': '10.0.3.2/24'})

    print("*** Starting network")
    net.start()

    print("*** Applying custom routing from Kathara startups")
    # h1 routes
    h1.cmd('ip route add 10.0.4.2/32 via 10.0.1.254')
    h1.cmd('ip route add 10.0.2.2/32 via 10.0.1.254')
    h1.cmd('ip route add 10.0.3.2/32 via 10.0.1.253')

    # h2 routes and dummy loopback
    h2.cmd('ip addr add 10.0.4.2/32 dev lo')
    h2.cmd('ip route add 10.0.1.0/24 via 10.0.2.254')

    # r1 & r2 routes
    r1.cmd('ip route add 10.0.4.2/32 via 10.0.2.2')
    r2.cmd('ip route add 10.0.4.2/32 via 10.0.3.2')

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    customNet()
