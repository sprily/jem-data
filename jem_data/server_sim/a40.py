import logging
import random
import struct
import time

import pymodbus.datastore as datastore

import jem_data.diris.registers as diris_registers
import jem_data.util as util

_log = logging.getLogger(__name__)

# Some of the registers that we simulate
_HOUR_METER = 0xC550
_FREQUENCY = 0xC55E
_PHASE_CURRENT_1 = 0xC560
_NEUTRAL_CURRENT = 0xC566

_INITIAL_REGISTER_VALUES = dict((k,0) for k in diris_registers.ALL)

def create():
    '''Create a new A40 slave

    For the timebeing this is just a stub.  But it does start the input registers
    at the correct address.
    '''
    return A40SlaveContext(
        di = datastore.ModbusSequentialDataBlock(0, [1]),
        co = datastore.ModbusSequentialDataBlock(0, [1]),
        ir = datastore.ModbusSequentialDataBlock(0, [1]),
        hr = A40HoldingRegistersDataBlock(_INITIAL_REGISTER_VALUES.copy())
    )

_ALL_REGISTERS = diris_registers.ALL

class A40SlaveContext(datastore.context.ModbusSlaveContext):
    '''
    Sub-class the standard slave context with one especially for the A40
    because the A40 refers to registers 1-16 as 1-16, and not 0-15 as it should
    according to section 4.4 of the modbus specification.  This class ensures
    that this SlaveContext behaves like an A40, and not like the standard
    modbus specification.
    '''

    def validate(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to test
        :returns: True if the request in within range, False otherwise
        '''
        ## address = address + 1  # section 4.4 of specification
        _log.debug("validate[%d] %d:%d" % (fx, address, count))
        return self.store[self.decode(fx)].validate(address, count)

    def getValues(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        ## address = address + 1  # section 4.4 of specification
        _log.debug("getValues[%d] %d:%d" % (fx, address, count))
        return self.store[self.decode(fx)].getValues(address, count)

    def setValues(self, fx, address, values):
        ''' Sets the datastore with the supplied values

        :param fx: The function we are working with
        :param address: The starting address
        :param values: The new values to be set
        '''
        ## address = address + 1  # section 4.4 of specification
        _log.debug("setValues[%d] %d:%d" % (fx, address, len(values)))
        self.store[self.decode(fx)].setValues(address, values)

class A40HoldingRegistersDataBlock(datastore.ModbusSparseDataBlock):
    '''A simulated datablock of registers for the Diris A40.

    A convenient subclass of a sparse data block, this transparantly handles
    the A40's multi-word registers upon initialization.

    It also dynamically updates its values using the twisted reactor.
    '''

    def __init__(self, values=None, dynamic=True):
        if values is None:
            values = {}
        assert set(values.keys()) <= set(_ALL_REGISTERS.keys())

        expanded_values = {}
        addrs = _ALL_REGISTERS.keys()
        for d in ( self._expand_register_value(addr, values.get(addr, 0)) \
                        for addr in addrs ):
            expanded_values.update(d)

        super(A40HoldingRegistersDataBlock, self).__init__(expanded_values)

        if dynamic:
            self._last_values = {}
            _log.debug("A40 Register Block initialised with dynamic updating")
            from twisted.internet import task
            self._start_time = time.time()
            l = task.LoopingCall(self._step)
            l.start(1.0)     # in seconds.

    def _expand_register_value(self, addr, value):
        '''Returns a dict of register addresses to register values.

        A40 registers can have register values greater than 2 bytes.  In which
        case the value is split across contiguous registers.

        This function takes a register address; looks up how wide it expects the
        value to be; and returns a mapping of register addresses to values.
        '''
        assert addr in _ALL_REGISTERS
        width = _ALL_REGISTERS[addr]

        to_return = {}
        for i, value in enumerate(util.pack_value(value, width)):
            to_return[addr + i] = value

        return to_return

    def _step(self):
        '''Step to the next set of values in this simulated datablock'''
        elapsed_time = time.time() - self._start_time
        
        # The A40 updates its hour meter every 1/100-th of an hour, ie
        # every 36 seconds.
        diris_time = int(elapsed_time / 36)
        self.setValues(_HOUR_METER, self._expand_register_value(_HOUR_METER, diris_time))

        for k in _INITIAL_REGISTER_VALUES:
            self._update_varying_register(k)

        ##self._update_varying_register(_PHASE_CURRENT_1)
        ##self._update_varying_register(_FREQUENCY)
        ##self._update_varying_register(_NEUTRAL_CURRENT)

    def _update_varying_register(self, addr):
        if addr not in self._last_values:
            self._last_values[addr] = 0
        else:
            p = random.randint(0,100)
            if p < 25:
                self._last_values[addr] = min(100, self._last_values[addr]+1)
            elif p < 50:
                self._last_values[addr] = max(-100, self._last_values[addr]-1)

        self.setValues(addr,
                       self._expand_register_value(addr, self._last_values[addr]))

