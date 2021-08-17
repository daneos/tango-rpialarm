tango-rpialarm
==============

A Tango device server for controlling an alarm device via RaspberryPi's GPIO.  
It will monitor a Tango attribute and start the alarm depending on the value.  
You can monitor if the value is too high, too low or outside defined range.  
The alarm signal is configurable as well.  
It supports two levels of alarm with distinct signalling: warning and alarm.

It was originally designed to drive a piezoelectic buzzer, but it can be used for other devices, such as LEDs as well.

Requirements
------------

* Python 3.x (it should work on 2.7, but this was not tested)
* pytango 9.2+
* `RPi.GPIO`

**Note**: If you run this DS under an user different than the default `pi` (e.g. `tango`, via Starter) make sure that this user is added to the `gpio` group! 

Installation
------------

To install, run `sudo python setup.py install` in the project's directory.  
To run, use `rpialarm <instance_name>`.

Configuration
-------------

The server is configured by following device properties:

| Property name | Description                                           | Default value |
|---------------|-------------------------------------------------------|---------------|
| gpio          | GPIO pin (BCM mode) your alarm device is connected to |               |
| monitor_attr  | Tango attribute to be monitored                       |               |
| polling_time  | Monitor thread polling time (in seconds)              |      0.2      |

and following expert mode attributes:

| Attribute name | Data type | Description                                                                                                                                                                                                                                                                                                                                                                                                 |
|----------------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| mode           | str       | Operation mode, can be on of `LOW`, `HIGH` or `RANGE`. In `LOW` mode the alarm is activated if the monitored attribute value falls below ones configured in `low_*` attributes. In `HIGH` mode the alarm is activated if the value raises above ones configured in `high_*` attributes. In `RANGE` mode the alarm is activated if the value falls outside range defined by `low_*` and `high_*` attributes. |
| low_alarm      | float     | Alarm threshold for `LOW` mode and lower alarm threshold for `RANGE` mode.                                                                                                                                                                                                                                                                                                                                  |
| low_warning    | float     | Warning threshold for `LOW` mode and lower warning threshold for `RANGE` mode.                                                                                                                                                                                                                                                                                                                              |
| high_alarm     | float     | Alarm threshold for `HIGH` mode and upper alarm threshold for `RANGE` mode.                                                                                                                                                                                                                                                                                                                                 |
| high_warning   | float     | Warning threshold for `HIGH` mode and upper warning threshold for `RANGE` mode.                                                                                                                                                                                                                                                                                                                             |
| alarm_conf     | str       | Configuration for alarm signal. It should be in the following format: `<time_active>:<time_sleep>`, e.g. `0.1:0.5`. `time_active` is the time for which GPIO output will be held high (in seconds), then it will be held low for `time_sleep` (in seconds). This sequence will be repeated in a loop as long as the alarm condition is present.                                                             |
| warning_conf   | str       | Configuration for warning signal. The format is the same as in `alarm_conf`.                                                                                                                                                                                                                                                                                                                                |

Attributes
----------

Apart from configuration attributes described above there are the following read-only operator mode attributes:

| Attribute name | Data type | Description                                                          |
|----------------|-----------|----------------------------------------------------------------------|
| alarm_flag     | bool      | Indicates that an alarm condition is present.                        |
| warning_flag   | bool      | Indicates that a warning condition is present.                       |
| test_flag      | bool      | Indicates that a test is active.                                     |
| reset_flag     | bool      | Indicates that a reset has been issued for current alarm or warning. |

Commands
--------

The server provides the following commands:

| Attribute name | Arguments | Description                                                                                                                                                                                                                                                                                                                                   |
|----------------|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| test           | str       | Tests the alarm or warning signal (enables GPIO loop without alarm/warning condition present). It requires a string argument, one of `ALARM` or `WARNING`. The test can be stopped by `reset` command.                                                                                                                                        |
| reset          |           | Stops signalling the alarm/warning (stops GPIO loop) while the alarm/warning condition is still present. The alarm/warning flag attributes are not affected. Reset is in effect until the state changes (e.g. from warning to alarm, from alarm to OK, etc.). The reset command is also used to stop the test initiated with `test` command.  |

Licensing
---------

This project is distributed under the GNU GPLv3 license. You can read the full license text in `LICENSE` file in project's directory.
