
from .common import I2cComponent
from ..accessors.temp import TempImpl
from ..core.component import Priority
from ..drivers.max6658 import Max6658KernelDriver
from ..drivers.sysfs import TempSysfsDriver

class Max6658(I2cComponent):
   def __init__(self, addr, drivers=None,
                priority=Priority.THERMAL, sensors=None, **kwargs):
      drivers = drivers or [Max6658KernelDriver(addr=addr),
                            TempSysfsDriver(addr=addr)]
      self.sensors = []
      super(Max6658, self).__init__(addr=addr, drivers=drivers, priority=priority,
                                    **kwargs)
      if sensors:
         self.addTempSensors(sensors)

   def addTempSensors(self, sensors):
      self.sensors.extend(sensors)
      for sensor in sensors:
         self.inventory.addTemp(TempImpl(sensor, self.drivers['TempSysfsDriver']))
