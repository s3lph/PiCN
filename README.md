*This is work in progress! Everything can change at any moment! :-)*

# PiCN 

[![Build Status](https://semaphoreci.com/api/v1/cn-unibas/picn/branches/master/badge.svg)](https://semaphoreci.com/cn-unibas/picn)

PiCN is a...
* prototyping-friendly, modular and extensible library for content-centric networkig (CCN).
* a set of tools and network nodes.
* our platform to build the next generation of NFN.

PiCN is written in Python 3.6+ and tested on Linux, Mac OS X and Windows. More than 200 unit tests are included.

## Features

#### Library

* Link Layer (UDP faces)
* Packet Encoding Layer (NDN packet format + link protocol)
* CCN Layer (basic forwarding logic, data structs)
* Chunking Layer
* Computation Layer (next-gen NFN implementation)
* Management interface to each layer

#### Tools

* Forwarder
* Setup Tool to start, connect, configure and inspect multiple nodes (with NDN testbed access)
* Peek Tool
* Management Tool

## Getting Started!
Let us setup a simple network which consists of a data repository and a forwarding node:

![Hands On: Topology](https://raw.githubusercontent.com/cn-uofbasel/PiCN/master/docs/img/initial-hands-on.png "Hands On: Topology")
             
Clone PiCN from github:
```console
you@machine:~$ git clone https://github.com/cn-uofbasel/PiCN.git
```

Add the PiCN-tools to your PATH (bash):
```console
you@machine:~$ PATH=$PATH:`pwd`/PiCN/starter
```
or config python library:
```console
you@machine:~$ cd PiCN && export PYTHONPATH=${PYTHONPATH}:`pwd`
```

Prepare content for a repository:
```console
you@machine:~$ mkdir /tmp/repo
you@machine:~$ touch /tmp/repo/example && echo "HELLO WORLD" > /tmp/repo/example
...
```

Start a repository node and a forwarder:
```console
you@machine:~$ picn-repo --format ndntlv /tmp/repo /the/prefix 10000 &
you@machine:~$ picn-relay --format ndntlv --port 9000 &  
...
```

Configure a forwarding rule from the forwarder to the repository:
```console
you@machine:~$ picn-mgmt --ip 127.0.0.1 --port 9000 newface 127.0.0.1:10000:0
you@machine:~$ picn-mgmt --ip 127.0.0.1 --port 9000 newforwardingrule /the:0
...
```

Fetch content from the repository via the forwarding node:
```console
you@machine:~$ picn-fetch --format ndntlv 127.0.0.1 9000 /the/prefix/example 
HELLO WORLD
```

## More about...

### Operational Matters

* [PiCN Toolbox](docs/toolbox.md)
* [Setting up a Network](docs/network_setup.md)
* [Packet Formats](docs/packet_formats.md)

### Internals

* [Architecture](docs/architecture.md)
* [Project Structure](docs/project_structure.md)
* [Management Interface](docs/management_interface.md)


### The Project

* [Licensing](docs/licensing.md)
* [Mailinglist](https://www.maillist.unibas.ch/mailman/listinfo/picn)
