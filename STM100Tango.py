#!/usr/bin/env python3
# coding: utf8
from tango import AttrWriteType, DevState, DispLevel
from tango.server import Device, attribute, command, device_property
import stm100
import sys


class STM100Tango(Device):
    '''STM100
    Controls a Sycon STM-100 QCM controller
    '''
    visa_resource = device_property(dtype=str, default_value="ASRL/dev/ttyUSB0::INSTR")

    thickness = attribute(
        label='thickness',
        dtype=float,
        access=AttrWriteType.READ,
        unit='A',)

    setpoint = attribute(
        label='setpoint thickness',
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit='A',
        min_value=0, max_value=9999999)

    setpoint_reached = attribute(
        label="setpoint reached",
        dtype=bool,
        access=AttrWriteType.READ)
    
    rate = attribute(
        label='rate',
        dtype=float,
        access=AttrWriteType.READ,
        unit='A/s',)

    density = attribute(
        label='density',
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit='g/cm^3',
        min_value=0.5, max_value=99.99)
    
    zfactor = attribute(
        label='Z factor',
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        min_value=0.1, max_value=9.999)

    tooling = attribute(
        label='tooling factor',
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit='%',
        min_value=10, max_value=399)

    lifetime = attribute(
        label='quartz life time',
        dtype=float,
        access=AttrWriteType.READ,
        unit='%',)

    timer = attribute(
        label='timer',
        dtype=float,
        access=AttrWriteType.READ,)

    testmode = attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        display_level=DispLevel.EXPERT)

    shutter = attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE)

    def init_device(self):
        super().init_device()
        try:
            self.info_stream(f'Connecting to STM-100 on {self.visa_resource}')
            self.qcm = stm100.STM100(self.visa_resource)
            idn = self.qcm.model
            self.info_stream(f'Connection established for {idn}')
            self.set_state(DevState.ON)
        except Exception as ex:
            self.error_stream(f'Error on initialization!: {ex}')
            sys.exit(1)

    def delete_device(self):
        self.set_state(DevState.OFF)
        self.qcm.close()
        self.info_stream('A device was deleted!')

    def always_executed_hook(self):
        if self.qcm.statuscode in "AB":
            self.set_state(DevState.ON)
        else:
            self.set_state(DevState.FAULT)

    def read_thickness(self):
        return self.qcm.thickness

    def read_setpoint(self):
        return self.qcm.setpoint

    def write_setpoint(self, value):
        self.qcm.setpoint = value

    def read_setpoint_reached(self):
        return self.qcm.setpoint_reached

    def read_target(self):
        return self._target

    def write_target(self, value):
        self._target = value

    def read_rate(self):
        return self.qcm.rate

    def read_density(self):
        return self.qcm.density

    def write_density(self, value):
        self.qcm.density = value

    def read_zfactor(self):
        return self.qcm.zfactor

    def write_zfactor(self, value):
        self.qcm.zfactor = value

    def read_tooling(self):
        return self.qcm.tooling

    def write_tooling(self, value):
        self.qcm.tooling = value

    def read_lifetime(self):
        return self.qcm.lifetime

    def read_timer(self):
        return self.qcm.timer

    def read_testmode(self):
        return self.qcm.testmode

    def write_testmode(self, value):
        self.qcm.testmode = value

    def read_shutter(self):
        return self.qcm.shutter

    def write_shutter(self, value):
        self.qcm.shutter = value

    @command
    def zero(self):
        self.qcm.zero()

    @command(dtype_in="str", dtype_out="str")
    def query(self, msg):
        return self.qcm.query(msg)


# start the server
if __name__ == "__main__":
    STM100Tango.run_server()
