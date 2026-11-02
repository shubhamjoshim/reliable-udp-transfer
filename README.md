Reliable UDP Transfer with SDN Failover

This project implements a reliable data transfer protocol over UDP using Stop-and-Wait ARQ and demonstrates a dynamic SDN-style network failover using a custom C-based controller. Originally designed for Kathara, this lab has been successfully ported to Mininet to allow for strict, namespace-isolated point-to-point link control.

Features

Stop-and-Wait ARQ: Custom C implementation of a reliable UDP file transfer mechanism that handles packet loss, timeouts, and ACKs.

Mininet Emulation: A custom Python script (topology.py) that builds an isolated diamond-shaped network topology with direct ethernet links.

Dynamic Failover: A C-based controller that monitors network health and dynamically rewrites Linux IP routing tables to failover to a backup path when the primary link drops.

Simulated Packet Loss: The primary path enforces an artificial 5% packet drop rate to stress-test the Stop-and-Wait ARQ retransmission logic.

Network Topology

The network consists of two hosts (h1, h2) and two routers (r1, r2) arranged in a diamond topology:

       [ Primary Path: r1 ]
      /                    \
   (h1)                    (h2)
      \                    /
       [ Backup Path: r2  ]


h1 (Sender): Initiates the file transfer.

h2 (Receiver): Receives data and acknowledges via a custom loopback interface (10.0.4.2).

r1 (Router 1): Primary routing path (subject to 5% packet loss).

r2 (Router 2): Backup routing path.

Prerequisites

To run this simulation, you will need an Ubuntu/Debian Linux environment (WSL is supported) with the following installed:

mininet (Network Emulator)

xterm (For host terminal windows)

gcc (To compile the C programs)

Mininet m utility installed in /usr/local/bin/

How to Run the Failover Demonstration

1. Start the Mininet Topology

Open a terminal and start the Mininet environment:

sudo python3 topology.py


Leave this terminal open. You will use the mininet> prompt to trigger the failover later.

2. Compile the Code

Open a second, separate terminal and compile the C source files:

gcc kathara_lab/controller.c -o controller
gcc kathara_lab/h1/sender.c -o sender
gcc kathara_lab/h2/receiver.c -o receiver


3. Start the Network Controller

In the same second terminal, run the SDN controller with root privileges so it can modify network namespaces:

sudo ./controller


4. Initiate the File Transfer

Return to your first terminal (the mininet> prompt) and open terminal windows for the hosts:

mininet> xterm h1 h2


In the h2 (Receiver) window, run: ./receiver

In the h1 (Sender) window, create a test file and run the sender:

dd if=/dev/urandom of=large.txt bs=1024 count=50
./sender


(Select option 2 for Network Transfer, and input large.txt)

5. Trigger the Failover

While the file is transferring and you see occasional timeout/retransmission messages in h1, quickly return to the mininet> prompt and sever the primary physical link:

mininet> link r1 h2 down


Observation: The sender (h1) will temporarily stall with timeouts. The controller will detect the broken path, kill the stuck processes, and dynamically update the routing tables on h1 and h2 to route traffic through r2.

Simply restart ./receiver on h2 and ./sender on h1 to watch the file transfer successfully complete over the newly established backup path!
