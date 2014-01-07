import os, sys
import time, socket
sys.path.insert(0, os.path.abspath('../'))

try:
    from libopenttd.query.master import send as m_send, recv as m_recv, MasterServerSocket
    from libopenttd.query.server import send as s_send, recv as s_recv
    from libopenttd.packets import constants
except ImportError:
    print "Somehow we were unable to load libopenttd, please make sure it's in python's path."
    raise

from collections import defaultdict

def millis():
    return int(round(time.time() * 1000))

USES_POLL = USES_EPOLL = False
try:
    from select import epoll as poll, EPOLLIN as POLLIN, \
                       EPOLLOUT as POLLOUT, EPOLLERR as POLLERR, \
                       EPOLLHUP as POLLHUP, EPOLLPRI as POLLPRI
    POLL_MOD   = 1.0
    USES_EPOLL = True
except ImportError:
    try:
        from select import poll, POLLIN, POLLOUT, POLLERR, POLLHUP, POLLPRI
        POLL_MOD   = 1000.0
        USES_POLL  = True
    except ImportError:
        raise
POLL_MOD = 1000.0 / POLL_MOD

from optparse import OptionParser

PARSER = OptionParser()
PARSER.add_option("-t", "--timeout", action="store", type="float", dest="timeout", default=5000, 
    help="The amount of time (in ms) to wait (in total) for packets to arrive")
PARSER.add_option("-d", "--debug", action="store_true", dest="debug", default=False)

def debug(msg, *args):
    print msg % args
def nodebug(*args):
    pass
log = nodebug
options = object()

def quick_info():
    log("EPOLL Available: %r", USES_EPOLL)
    log("Timeout        : %s", options.timeout)

def statistics(servers):
    noinfo = [x for x in servers if not x.has_info]
    info = [x.info for x in servers if x.has_info]
    responding_servers = len(info)

    clientcount = [x.clients_on for x in info]
    companycount = [x.companies_on for x in info]
    spectatorcount = [x.spectators_on for x in info]

    total_players = sum(clientcount)
    average_players = float(total_players) / float(responding_servers)
    max_players = max(clientcount)
    
    total_companies = sum(companycount)
    average_companies = float(total_companies) / float(responding_servers)
    max_companies = max(companycount)

    total_spectators = sum(spectatorcount)
    average_spectators = float(total_spectators) / float(responding_servers)
    max_spectators = max(spectatorcount)

    dedicated = len([x for x in info if x.dedicated])
    passworded = len([x for x in info if x.passworded])

    versions = defaultdict(int)
    map_set = defaultdict(int)
    net_versions = defaultdict(int)

    for server in info:
        versions[server.revision] += 1
        map_set[server.map_set] += 1
        net_versions[server.version] += 1

    debug("Statistics:")
    debug("       Total servers: %d", len(servers))
    debug("           Responded: %d", responding_servers)
    debug("         No response: %d", len(noinfo))
    debug("           Dedicated: %d", dedicated)
    debug("          Passworded: %d", passworded)
    debug("Players:")
    debug("               Total: %d", total_players)
    debug("             Average: %d", average_players)
    debug("                 Max: %d", max_players)
    debug("Spectators:")
    debug("               Total: %d", total_spectators)
    debug("             Average: %d", average_spectators)
    debug("                 Max: %d", max_spectators)
    debug("Companies:")
    debug("               Total: %d", total_companies)
    debug("             Average: %d", average_companies)
    debug("                 Max: %d", max_companies)
    debug("Versions:")
    for version, amt in versions.items():
        debug("%20s: %d", version, amt)
    debug("Map Sets:")
    for mset, amt in map_set.items():
        debug("%20s: %d", mset, amt)
    debug("Net Versions:")
    for version, amt in net_versions.items():
        debug("%20s: %d", version, amt)


def main():
    global log, options
    opts, _ = PARSER.parse_args()
    options = opts
    options.timeout = float(options.timeout)
    log = debug if options.debug else nodebug
    quick_info()
    listing = ServerList(options.timeout, log)
    log("Querying master server for servers")
    listing.run()
    statistics(listing.serverlist.values())



class ServerInfo(object):
    def __init__(self, addr):
        self.addr = addr
        self.info = None

    @property
    def has_info(self):
        return self.info is not None

class ServerList(object):
    def __init__(self, timeout = 5000.0, logger = nodebug):
        self.poll = poll()
        self.sock = MasterServerSocket()
        self.poll.register(self.sock.fileno(), POLLIN | POLLOUT | POLLHUP | POLLERR | POLLPRI)

        self.msu_addr = (socket.gethostbyname(constants.NETWORK_MASTER_SERVER_HOST), 
                        constants.NETWORK_MASTER_SERVER_PORT)

        self.serverlist = {}
        self.max_wait = float(timeout)
        self.log = logger

    def run(self):
        start = now = millis()
        timeout = self.max_wait
        self.sock.send_packet(self.msu_addr, m_send.ServerList())
        left = int(self.max_wait / 1000) - 1
        while timeout > 0:
            now = millis()
            timeout = self.max_wait - (now - start)
            seconds = int(timeout / 1000)
            if seconds < left:
                left = seconds
                self.log("Progress:")
                self.log("  %d servers in listing", len(self.serverlist))
                self.log("  %d still to check", len([x for x in self.serverlist.values() if not x.has_info]))
            timeleft = min(timeout, 10)
            events = self.poll.poll(timeleft / POLL_MOD)
            for fileno, event in events:
                if fileno != self.sock.fileno():
                    continue
                if (event & POLLIN) or (event & POLLPRI):
                    self.sock.process_recv()
                if (event & POLLOUT):
                    self.sock.process_send()
                if (event & POLLERR) or (event & POLLHUP):
                    break
            packets = self.sock.process_packets()
            self.process_packets(packets)

    def process_msu_packet(self, packet):
        if isinstance(packet, m_recv.ServerList):
            addr_list = [(str(item['ip']), item['port']) for item in packet.addresses]
            for addr in addr_list:
                if addr not in self.serverlist:
                    self.serverlist[addr] = ServerInfo(addr)
                    self.sock.send_packet(addr, s_send.ServerInformation())

    def process_server_packet(self, addr, packet):
        info = self.serverlist.get(addr, None)
        if not info:
            print "Unknown addr: %s:%s" % info
            return
        if not isinstance(packet, s_recv.GameInformation):
            print "Unwanted packet received: %s" % packet
            return
        info.info = packet

    def process_packets(self, packets):
        for addr, packet in packets:
            if addr == self.msu_addr:
                self.process_msu_packet(packet)
            else:
                self.process_server_packet(addr, packet)


if __name__ == "__main__":
    main()