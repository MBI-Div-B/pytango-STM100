import pyvisa
import logging
from math import nan


class STM100:
    """
    Class representing a Sycon STM-100 quartz crystal balance controller.
    Most settings and parameters are directly available as attributes.
    """

    def __init__(self, resource: str):
        """Open serial connection to controller.

        Parameters
        ==========
        resource : pyvisa resource name
        """
        self.rm = pyvisa.ResourceManager("@py")
        self.inst = self.rm.open_resource(resource)
        self.inst.timeout = 200
        self.log = logging.getLogger("STM100")
        self.statuscode = None
        self._films = None

    @property
    def model(self):
        """Returns controller model and software revision."""
        return self.query('@')

    @property
    def testmode(self):
        """Returns whether device is in test mode.

        In test mode, opening/closing the shutter relay simulates
        deposition with a constant rate.
        """
        return self._query_bool("K?")

    @testmode.setter
    def testmode(self, enable: bool):
        c = '!' if enable else '@'
        self.query(f"K{c}")

    @property
    def thickness(self):
        """Returns thickness (in Angstrom) of the current film."""
        return self._query_float('S')

    @property
    def setpoint(self):
        """Returns current thickness setpoint (A)."""
        return self._query_float("G?")

    @setpoint.setter
    def setpoint(self, value):
        assert (value >=0) and (value <= 9999999), "Setpoint out of range"
        self.query(f"G={int(value):d}")

    @property
    def setpoint_reached(self):
        return self._query_bool('P')

    @property
    def rate(self):
        """Returns current deposition rate in Angstrom/s."""
        return self._query_float('T')

    @property
    def density(self):
        """Returns current film density (g/cm^3)."""
        return self._query_float("E?")

    @density.setter
    def density(self, value: float):
        assert (value >= 0.5) and (value <= 99.99)
        self.query(f"E={value:.3f}")

    @property
    def zfactor(self):
        """Returns current film Z factor."""
        return self._query_float("F?")

    @zfactor.setter
    def zfactor(self, value: float):
        self.query(f"F={value:.3f}")

    @property
    def tooling(self):
        """Returns current film tooling factor."""
        return self._query_float("J?")

    @tooling.setter
    def tooling(self, value: float):
        assert (value >= 10) and (value <= 399)
        self.query(f"J={value:.1f}")

    @property
    def frequency(self):
        """Returns quartz crystal frequency (Hz)."""
        return self._query_float('U')

    @property
    def lifetime(self):
        """Returns remaining quartz crystal lifetime in percent."""
        return self._query_float('V')

    @property
    def crystal_fail(self):
        """Returns whether quartz crystal has failed."""
        return self._query_bool('M')

    @property
    def timer(self):
        """Timer value in seconds. Returns nan if greater than 99:59"""
        ans = self.query('W')
        if ans[0] == '>':
            return nan
        minutes, seconds = ans.split(':')
        return 60 * int(minutes) + int(seconds)

    @property
    def films(self):
        """List of all saved film parameters"""
        # if self._films is None:
        self.query_films()
        return self._films

    @property
    def shutter(self):
        """Shutter relay state (True=on)"""
        return self._query_bool("A?")

    @shutter.setter
    def shutter(self, enable: bool):
        v = '!' if enable else '@'
        self.query(f"A{v}")

    @property
    def poweron_status(self):
        """Return power-on status bits

        Bits represent
        - reset occurred
        - brownout occurred
        - non-volatile memory fault
        """
        ans = ord(self.query('a'))
        return [bool(ans & i) for i in [1, 2, 4]]

    def reset_poweron_status(self):
        """Send power-on status acknowledgement and reset status bits."""
        self.query('L')

    def zero(self, what="both"):
        """Zeros the timer and/or thickness.

        Parameters
        ==========
        what: "both", "timer", "thickness"
        """
        if what == "both":
            cmd = 'B'
        elif what == "thickness":
            cmd = 'C'
        elif what == "timer":
            cmd = 'D'
        else:
            raise ValueError("Parameter 'what' needs to be both/thickness/timer")
        self.query(cmd)

    def query_films(self):
        """Queries all saved film parameters."""
        params = dict(density='j', zfactor='k', tooling='o')
        self._films = []
        for f in range(1, 10):
            self._films.append(
                {k: self._query_float(f"{v}{f}?") for k, v in params.items()}
            )
        return self._films

    def _query_float(self, cmd):
        try:
            return float(self.query(cmd))
        except ValueError:
            return nan

    def _query_bool(self, cmd):
        """Query command that returns boolean reply, i.e., '@' or '!' character"""
        ans = self.query(cmd)
        assert ans in "!@", f"Unexpected response to query ({cmd})"
        return ans == '!'

    def _calc_checksum(self, msg):
        return sum(ord(c) for c in msg) % 256

    def _send(self, msg):
        if len(msg) > 10:
            raise ValueError("maximum message length is 10!")
        chksum = self._calc_checksum(msg)
        cmd = bytes([2, len(msg)] + [ord(c) for c in msg] + [chksum])
        self.log.debug(f"Send command: {msg} ({cmd})")
        return self.inst.write_raw(cmd)

    def _read(self):
        s = self.inst.read_bytes(1).decode()
        if s == '\x02':
            msgsize = ord(self.inst.read_bytes(1))
            msg = self.inst.read_bytes(msgsize).decode()
            chksum = ord(self.inst.read_bytes(1))
            msg_ok = chksum == self._calc_checksum(msg)
            if not msg_ok:
                self.log.error("Checksum mismatch")
                pass
            return msg[0], msg[1:]
        else:
            error_msg = "Received message without start byte"
            self.log.error(error_msg)
            self.inst.flush(pyvisa.constants.BufferOperation.discard_read_buffer)
            raise RuntimeError(error_msg)

    def query(self, msg: str):
        """
        Send command to controller and return reply.

        All commands return at least an empty string as reply.
        Check 'statuscode' attribute for automatically returned
        status.

        Parameters
        ==========
        msg:
            Command or query to send

        Returns
        =======
        reply: str
            
        """
        self._send(msg)
        ret, ans = self._read()
        self.statuscode = ret
        return ans

    def close(self):
        """Close pyvisa session."""
        self.inst.close()
        self.rm.close()

