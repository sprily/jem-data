import logging

from twisted.internet import defer

_log = logging.getLogger(__name__)

def read_registers(client, unit, registers):
    '''Make a request for the given registers.

    :param client: the pymodbus client to send the request to.
    :param unit: the unit identifier if the client is a gateway.
    :param registers: a dict of register addresses to register value widths

    When using this function, you should address the registers as they are
    named on the device (and therefore in the device's specification), rather
    than the 0-indexed naming required by the modbus request message.  (Modbus
    defines the addresses to the 1-indexed when naming them on the device, but
    when constructing a modbus request, they need to be 0-indexed.  This
    function handles the 1-indexed form, in order to keep the interface
    uniform).

    The registers on the device may actually be wider than 1 register value.
    For example, the register named `0xC550` may actually have a value that
    is 32 bits wide.  This means the lower half of the value is stored in
    register `0xC551`.  And the next "meaningful" register address would be
    `0xC552`.  That is what the `registers` param is used for: the width of
    the register values can be specified, and this function will ensure that
    the correct range of registers is requested.  And will also (upon success)
    return the response in the form of a `RegisterResponse` object which
    will transparently read the required number of register values in order to
    contruct the composite value -- ie in the example above, when asked for
    the value of the register named `0xC550`, the response will transparently
    also read the value in `0xC551` and combine the two values.

    Returns a Deferred which contains the result of the request.
    '''
    min_register = min(registers.keys())
    max_register = max(registers.keys())
    register_range = max_register + registers[max_register] - min_register

    if register_range > 125:
        return defer.fail(ValueError('Unable to create request of such a '
                                     'large range'))

    # The `- 1` is because the registers are *named* [1..n], but when making
    # a request they are reference as [0,n)
    d = client.read_input_registers(min_register - 1,
                                    register_range,
                                    unit=unit)

    # Map the result of the deferred to a more manageable response type.
    map_to_register_response(d, registers)

    return d

def map_to_register_response(d, requested_registers):
    def _f(response):
        return RegisterResponse(response, requested_registers)
    d.addCallback(_f)

class RegisterResponse(object):
    '''Wraps a pymodbus response object to provide access to the registers
    with values more than 1 register wide.

    For example, it may be that the register named `0xC550` is actually stored
    across `0xC550` *and* `0xC551` on the device.  Knowing this, this response
    class can, when asked for the value of the register named `0xC550`,
    combine the two values.

    The most significant bytes are assumed to be stored in the lower address.
    '''

    def __init__(self, pymodbus_response, requested_registers):
        self._requested_registers = requested_registers
        self._response = pymodbus_response
        self._min_addr = min(self._requested_registers.keys())

    def read_register(self, addr):
        assert addr in self._requested_registers
        values = [ self._response.getRegister(addr + i - self._min_addr) \
                        for i in range(self._requested_registers[addr]) ]
        return reduce(lambda acc, x: (acc << 16) + x, values, 0)

