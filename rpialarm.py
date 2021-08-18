from re import match
from time import sleep
from threading import Thread

from tango import AttrWriteType, DevState, DispLevel, AttributeProxy
from tango.server import run, Device, attribute, device_property, command

from RPi import GPIO


class rpialarm(Device):

	gpio = device_property(
		dtype=int,
		doc="GPIO pin for alarm device",
	)
	monitor_attr = device_property(
		dtype=str,
		doc="Attribute to be monitored"
	)
	polling_time = device_property(
		dtype=float,
		default_value=0.2,
		doc="Monitor thread polling time (in seconds)"
	)

	alarm_flag = attribute(
		label="Alarm active",
		dtype=bool,
		access=AttrWriteType.READ,
		fget="get_alarm"
	)
	warning_flag = attribute(
		label="Warning active",
		dtype=bool,
		access=AttrWriteType.READ,
		fget="get_warning"
	)
	test_flag = attribute(
		label="Test active",
		dtype=bool,
		access=AttrWriteType.READ,
		fget="get_test"
	)
	reset_flag = attribute(
		label="Reset issued",
		dtype=bool,
		access=AttrWriteType.READ,
		fget="get_reset"
	)

	mode = attribute(
		label="Operation mode",
		dtype=str,
		access=AttrWriteType.READ_WRITE,
		display_level=DispLevel.EXPERT,
		memorized=True, hw_memorized=True,
		fget="get_mode", fset="set_mode",
		doc="Possible values: LOW, RANGE, HIGH"
	)
	low_alarm = attribute(
		label="Low alarm",
		dtype=float,
		access=AttrWriteType.READ_WRITE,
		display_level=DispLevel.EXPERT,
		memorized=True, hw_memorized=True,
		fget="get_low_alarm", fset="set_low_alarm",
		doc="Alarm when lower than (in LOW or RANGE modes)"
	)
	low_warning = attribute(
		label="Low warning",
		dtype=float,
		access=AttrWriteType.READ_WRITE,
		display_level=DispLevel.EXPERT,
		memorized=True, hw_memorized=True,
		fget="get_low_warning", fset="set_low_warning",
		doc="Warning when lower than (in LOW or RANGE modes)"
	)
	high_alarm = attribute(
		label="High alarm",
		dtype=float,
		access=AttrWriteType.READ_WRITE,
		display_level=DispLevel.EXPERT,
		memorized=True, hw_memorized=True,
		fget="get_high_alarm", fset="set_high_alarm",
		doc="Alarm when greater than (in HIGH or RANGE modes)"
	)
	high_warning = attribute(
		label="High warning",
		dtype=float,
		access=AttrWriteType.READ_WRITE,
		display_level=DispLevel.EXPERT,
		memorized=True, hw_memorized=True,
		fget="get_high_warning", fset="set_high_warning",
		doc="Warning when greater than (in HIGH or RANGE modes)"
	)
	alarm_conf = attribute(
		label="Alarm configuration",
		dtype=str,
		access=AttrWriteType.READ_WRITE,
		display_level=DispLevel.EXPERT,
		memorized=True, hw_memorized=True,
		fget="get_alarm_conf", fset="set_alarm_conf",
		doc="Alarm signal configuration (<time_active>:<time_sleep>)"
	)
	warning_conf = attribute(
		label="Warning configuration",
		dtype=str,
		access=AttrWriteType.READ_WRITE,
		display_level=DispLevel.EXPERT,
		memorized=True, hw_memorized=True,
		fget="get_warning_conf", fset="set_warning_conf",
		doc="Warning signal configuration (<time_active>:<time_sleep>)"
	)

	def init_device(self):
		Device.init_device(self)
		self.set_state(DevState.INIT)

		self._monitor_thread = MonitorThread(self)
		self._hw_thread = HWThread(self)
		self._attr = None

		self._test = False
		self._reset = False

		# some defaults
		self._mode = "RANGE"
		self._low_alarm = 0
		self._low_warning = 0
		self._high_alarm = 0
		self._high_warning = 0
		self._alarm_active = 0.5
		self._alarm_sleep = 0.5
		self._warning_active = 0.1
		self._warning_sleep = 0.9

		try:
			self._attr = AttributeProxy(self.monitor_attr)
		except Exception as e:
			self.set_state(DevState.FAULT)
			self.set_status("Could not monitor attribute {attr}:\n{err}".format(attr=self.monitor_attr, err=str(e)))
		else:
			self.set_state(DevState.ON)
			self._monitor_thread.start()

	@command(dtype_in=str, doc_in="Test ALARM or WARNING")
	def test(self, v):
		v = v.upper()
		if v in ("ALARM", "WARNING"):
			self._test = True
			self._hw_thread.set(v)
			self._start_hw_thread()
		else:
			raise ValueError("Invalid value. Test \"ALARM\" or \"WARNING\".")

	@command()
	def reset(self):
		if not self._test:
			self._reset = True
		else:
			self._test = False
		self._stop_hw_thread()

	def get_alarm(self):
		return self._monitor_thread.alarm

	def get_warning(self):
		return self._monitor_thread.warning

	def get_test(self):
		return self._test

	def get_reset(self):
		return self._reset

	def get_mode(self):
		return self._mode

	def set_mode(self, v):
		v = v.upper()
		if v in ("LOW", "RANGE", "HIGH"):
			self._mode = v
		else:
			raise ValueError("Invalid value. Mode can be one of \"LOW\", \"RANGE\" or \"HIGH\".")

	def get_low_alarm(self):
		return self._low_alarm

	def set_low_alarm(self, v):
		self._low_alarm = v

	def get_low_warning(self):
		return self._low_warning

	def set_low_warning(self, v):
		self._low_warning = v

	def get_high_alarm(self):
		return self._high_alarm

	def set_high_alarm(self, v):
		self._high_alarm = v

	def get_high_warning(self):
		return self._high_warning

	def set_high_warning(self, v):
		self._high_warning = v

	def get_alarm_conf(self):
		return "{act}:{sleep}".format(act=self._alarm_active, sleep=self._alarm_sleep)

	def set_alarm_conf(self, v):
		m = match(r"(\d*\.?\d*):(\d*\.?\d*)", v)
		if m is not None:
			self._alarm_active = float(m.group(1))
			self._alarm_sleep = float(m.group(2))
		else:
			raise ValueError("Invalid format. Use \"<time_active>:<time_sleep>\".")

	def get_warning_conf(self):
		return "{act}:{sleep}".format(act=self._warning_active, sleep=self._warning_sleep)

	def set_warning_conf(self, v):
		m = match(r"(\d*\.?\d*):(\d*\.?\d*)", v)
		if m is not None:
			self._warning_active = float(m.group(1))
			self._warning_sleep = float(m.group(2))
		else:
			raise ValueError("Invalid format. Use \"<time_active>:<time_sleep>\".")

	def _start_hw_thread(self):
		if not self._hw_thread.isAlive():
			self._hw_thread.start()

	def _stop_hw_thread(self):
		if self._hw_thread.isAlive():
			self._hw_thread.stop()
			self._hw_thread.join()
			self._hw_thread = HWThread(self)


class MonitorThread(Thread):
	def __init__(self, dev):
		Thread.__init__(self)
		
		self._dev = dev
		self._quit = False
		self._warning = False
		self._alarm = False
		self._prev_warning = False
		self._prev_alarm = False

		self.alarm = False
		self.warning = False

	def run(self):
		while not self._quit:
			self._prev_warning = self._warning
			self._prev_alarm = self._alarm
			self._warning = False
			self._alarm = False

			try:
				v = self._dev._attr.read().value
			except Exception as e:
				self._dev.set_state(DevState.STANDBY)
				self._dev.set_status("Could not read value:\n{err}".format(err=str(e)))
				self._warning = self._prev_warning
				self._alarm = self._prev_alarm
				continue
			else:
				self._dev.set_state(DevState.ON)
				self._dev.set_status("Monitoring...")
			
			if self._dev._mode == "LOW":
				if v < self._dev._low_alarm:
					self._alarm = True
				elif v < self._dev._low_warning:
					self._warning = True

			elif self._dev._mode == "HIGH":
				if v > self._dev._high_alarm:
					self._alarm = True
				elif v > self._dev._high_warning:
					self._warning = True

			elif self._dev._mode == "RANGE":
				if v < self._dev._low_alarm or v > self._dev._high_alarm:
					self._alarm = True
				elif v < self._dev._low_warning or v > self._dev._high_warning:
					self._warning = True

			if self._alarm:
				self._dev.set_state(DevState.ALARM)
				self._dev.set_status("Alarm active!")
				self._dev._test = False
				if not self._dev._reset or not self._prev_alarm:
					self._dev._reset = False
					self._dev._hw_thread.set("ALARM")
					self._dev._start_hw_thread()
			elif self._warning:
				self._dev.set_state(DevState.ALARM)
				self._dev.set_status("Warning active!")
				self._dev._test = False
				if not self._dev._reset or not self._prev_warning:
					self._dev._reset = False
					self._dev._hw_thread.set("WARNING")
					self._dev._start_hw_thread()
			else:
				self._dev.set_state(DevState.ON)
				self._dev.set_status("Monitoring...")
				self._dev._reset = False
				if not self._dev._test:
					self._dev._stop_hw_thread()

			self.warning = self._warning
			self.alarm = self._alarm
			sleep(self._dev.polling_time)

	def stop(self):
		self._quit = True


class HWThread(Thread):
	def __init__(self, dev):
		Thread.__init__(self)
		
		self._dev = dev
		self._quit = False
		self._mode = None

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self._dev.gpio, GPIO.OUT)

	def run(self):
		while not self._quit:
			GPIO.output(self._dev.gpio, True)
			if self._mode == "WARNING":
				sleep(self._dev._warning_active)
			elif self._mode == "ALARM":
				sleep(self._dev._alarm_active)

			GPIO.output(self._dev.gpio, False)
			if self._mode == "WARNING":
				sleep(self._dev._warning_sleep)
			elif self._mode == "ALARM":
				sleep(self._dev._alarm_sleep)

	def set(self, mode):
		self._mode = mode

	def stop(self):
		self._quit = True


def start():
	run((rpialarm,))


if __name__ == "__main__":
	start()
