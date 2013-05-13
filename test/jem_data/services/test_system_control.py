import mock
import nose.tools as nose

import jem_data.core.domain as domain
import jem_data.services.system_control as services
import jem_data.core.exceptions as jem_exceptions

ValidationException = jem_exceptions.ValidationException

def test_update_devices_validates_gateway_host():
    system_control = services.SystemControlService(mock.Mock())
    device = domain.Device(
            unit=1,
            gateway=domain.Gateway(host=123, port=456, label=None),
            label=None,
            tables=[])

    nose.assert_raises(ValidationException,
                  system_control.update_devices,
                  [device])

def test_update_validates_gateway_port():
    system_control = services.SystemControlService(mock.Mock())
    device = domain.Device(
            unit=1,
            gateway=domain.Gateway(host="127.0.0.1", port=-1, label=None),
            label=None,
            tables=[])

    nose.assert_raises(ValidationException,
                  system_control.update_devices,
                  [device])

def test_update_validates_device_unit():
    system_control = services.SystemControlService(mock.Mock())
    device = domain.Device(
            unit="1",
            gateway=domain.Gateway(host="127.0.0.1", port=502, label=None),
            label=None,
            tables=[])

    nose.assert_raises(ValidationException,
                  system_control.update_devices,
                  [device])

def test_update_validates_device_unit_range():
    system_control = services.SystemControlService(mock.Mock())
    device = domain.Device(
            unit=32,
            gateway=domain.Gateway(host="127.0.0.1", port=502, label=None),
            label=None,
            tables=[])

    nose.assert_raises(ValidationException,
                  system_control.update_devices,
                  [device])

def test_update_with_valid_data():
    db = mock.Mock()
    system_control = services.SystemControlService(db)
    device = domain.Device(
            unit=1,
            gateway=domain.Gateway(host="127.0.0.1", port=502, label=None),
            label=None,
            tables=[])
    system_control.update_devices([device])

    db.devices.delete_all.assert_called_once_with()
    db.devices.insert.assert_called_once_with([device])
    db.devices.all.assert_called_once_with()

def test_attached_devices():
    db = mock.Mock()
    system_control = services.SystemControlService(db)
    system_control.attached_devices()
    db.devices.all.assert_called_once_with()

def test_all_recordings():
    db = mock.Mock()
    system_control = services.SystemControlService(db)
    db.recordings.all.return_value = [
        domain.Recording(
            id=None, status=None, configured_gateways=[], end_time=None,
            start_time=i) for i in xrange(10) ]
    result = system_control.all_recordings()

    nose.assert_equal(len(result), 10)
    nose.assert_equal(result[0].start_time, 9)