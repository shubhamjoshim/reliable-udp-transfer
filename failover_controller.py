"""
Ryu controller: automatic path failover for the diamond topology.

Switch IDs (dpid):  1 = ingress, 2 = primary path, 3 = backup path, 4 = egress

Forwarding is by destination MAC only (hosts have fixed MACs), with explicit
output ports, so there is no flooding and no loops.

  - s2 (primary) and s3 (backup) always keep their forwarding rules.
  - s1 and s4 are the "decision" switches. The controller rewrites their
    rules to point either at the primary or the backup path.
  - When any link on the active path goes down (OFPPortStatus), the
    controller moves s1 and s4 to the other path. When the primary link
    comes back, it switches back.

Run:  ryu-manager controller/failover_controller.py
"""
import time

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3

H1_MAC = '00:00:00:00:00:01'
H2_MAC = '00:00:00:00:00:02'

# dpid -> {dst_mac: out_port}
PATHS = {
    'primary': {
        1: {H2_MAC: 2, H1_MAC: 1},
        2: {H2_MAC: 2, H1_MAC: 1},
        4: {H2_MAC: 1, H1_MAC: 2},
    },
    'backup': {
        1: {H2_MAC: 3, H1_MAC: 1},
        3: {H2_MAC: 2, H1_MAC: 1},
        4: {H2_MAC: 1, H1_MAC: 3},
    },
}

# (dpid, port) pairs whose link state decides if a path is usable
PATH_PORTS = {
    'primary': {(1, 2), (2, 1), (2, 2), (4, 2)},
    'backup': {(1, 3), (3, 1), (3, 2), (4, 3)},
}

FLOW_PRIORITY = 10


class FailoverController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dps = {}            # dpid -> datapath
        self.down = set()        # (dpid, port) currently link-down
        self.current = 'primary'

    # ---------- helpers ----------

    def _rules_for(self, dpid):
        """Rules this switch should have right now."""
        if dpid == 2:
            return PATHS['primary'][2]
        if dpid == 3:
            return PATHS['backup'][3]
        return PATHS[self.current].get(dpid, {})

    def _add_flow(self, dp, dst_mac, out_port):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        match = parser.OFPMatch(eth_dst=dst_mac)
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        # OFPFC_ADD with an identical match+priority replaces the old rule
        dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=FLOW_PRIORITY,
                                      match=match, instructions=inst))

    def _install(self, dpid):
        dp = self.dps.get(dpid)
        if dp is None:
            return
        for mac, port in self._rules_for(dpid).items():
            self._add_flow(dp, mac, port)

    def _path_ok(self, name):
        return not (self.down & PATH_PORTS[name])

    def _reevaluate(self):
        if self._path_ok('primary'):
            wanted = 'primary'
        elif self._path_ok('backup'):
            wanted = 'backup'
        else:
            self.logger.error('BOTH PATHS DOWN - no change possible')
            return
        if wanted == self.current:
            return
        t0 = time.time()
        self.logger.info('[%s] FAILOVER: %s -> %s',
                         time.strftime('%H:%M:%S'), self.current, wanted)
        self.current = wanted
        for dpid in (1, 4):          # only the decision switches change
            self._install(dpid)
        self.logger.info('rules updated in %.1f ms',
                         (time.time() - t0) * 1000)

    # ---------- events ----------

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def on_switch_features(self, ev):
        dp = ev.msg.datapath
        self.dps[dp.id] = dp
        self.logger.info('switch s%d connected', dp.id)
        self._install(dp.id)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def on_port_status(self, ev):
        msg = ev.msg
        dp, ofp, desc = msg.datapath, msg.datapath.ofproto, msg.desc
        key = (dp.id, desc.port_no)
        if not any(key in ports for ports in PATH_PORTS.values()):
            return   # host-facing or local port, ignore

        is_down = (msg.reason == ofp.OFPPR_DELETE
                   or bool(desc.state & ofp.OFPPS_LINK_DOWN)
                   or bool(desc.config & ofp.OFPPC_PORT_DOWN))
        if is_down:
            self.down.add(key)
        else:
            self.down.discard(key)
        self.logger.info('s%d port %d is %s', dp.id, desc.port_no,
                         'DOWN' if is_down else 'UP')
        self._reevaluate()
