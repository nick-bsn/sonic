import json
import time

from .sonic_ceos_utils import runCliCmd, ceosManagesXcvrs
from .sonic_utils import parsePortConfig
from ..core import platform as core_platform
from .. import platforms

try:
    from sonic_sfp.sfputilbase import SfpUtilBase
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))


def getSfpUtil():
    platform = core_platform.getPlatform()
    inventory = platform.getInventory()

    class SfpUtilCommon(SfpUtilBase):
        @property
        def port_start(self):
            return inventory.portStart

        @property
        def port_end(self):
            return inventory.portEnd

        @property
        def qsfp_ports(self):
            return inventory.qsfpRange

        # XXX: defining the sfp_ports property currently can't be done as
        #      it affect the code logic of the sfputil tool by preventing
        #      the qsfp ports from being detected
        #@property
        #def sfp_ports(self):
        #    return inventory.sfpRange

        @property
        def port_to_eeprom_mapping(self):
            return inventory.getPortToEepromMapping()

        @property
        def port_to_i2cbus_mapping(self):
            return inventory.getPortToI2cAdapterMapping()

        def __init__(self):
            SfpUtilBase.__init__(self)

    class SfpUtilNative(SfpUtilCommon):
        """Native Sonic SfpUtil class"""
        def get_presence(self, port_num):
            if not self._is_valid_port(port_num):
                return False

            return inventory.getXcvr(port_num).getPresence()

        def get_low_power_mode(self, port_num):
            if not self._is_valid_port(port_num):
                return False

            return inventory.getXcvr(port_num).getLowPowerMode()

        def set_low_power_mode(self, port_num, lpmode):
            if not self._is_valid_port(port_num):
                return False

            try:
               return inventory.getXcvr(port_num).setLowPowerMode(lpmode)
            except:
               #print('failed to set low power mode for xcvr %d' % port_num)
               return False

        def reset(self, port_num):
            if not self._is_valid_port(port_num):
                return False

            xcvr = inventory.getXcvr(port_num)
            try:
               if not xcvr.reset(True):
                  return False
            except:
               #print('failed to put xcvr %d in reset' % port_num)
               return False

            # Sleep 1 second to allow it to settle
            time.sleep(1)

            try:
               if not xcvr.reset(False):
                  return False
            except:
               #print('failed to take xcvr %d out of reset' % port_num)
               return False

            return True

    class SfpUtilCeos(SfpUtilCommon):
        def __init__(self):
           self.portMapping = parsePortConfig()
           # Using a different command to get presentXcvrs as it takes care of
           # the port mapping for us.
           cliCmd = ['show interface transceiver hardware | json']
           self.presentXcvrs = json.loads(runCliCmd(cliCmd))['interfaces']
           cliCmd = ['show idprom interface extended | json']
           self.eepromIntfMap = json.loads(runCliCmd(cliCmd))['interfaces']
           SfpUtilBase.__init__(self)

        def _read_eeprom_devid(self, port_num, devid, offset):
           num_bytes = 256
           registers = []
           eeprom_raw = ['0x00'  for _ in range(num_bytes)]
           for port in self.portMapping.values():
              if port.portNum == port_num:
                  break

           if port.alias not in self.presentXcvrs:
              return None

           for intf in self.eepromIntfMap:
              if intf in port.alias:
                 break

           pages = self.eepromIntfMap[intf]['pages']
           for page in pages.values():
              registers += page['registers']
           idx = 0
           for reg in registers:
              eeprom_raw[idx] = hex(reg)[2:].zfill(2)
              idx = idx + 1
           return eeprom_raw

        def get_presence(self, port_num):
           if not self._is_valid_port(port_num):
              return False
           for port in self.portMapping.values():
              if port.portNum == port_num:
                 break
           return port.alias in self.presentXcvrs

        def get_low_power_mode(self, port_num):
           return False

        def set_low_power_mode(self, port_num, lpmode):
           return False

        def reset(self, port_num):
           return False

    if ceosManagesXcvrs():
       return SfpUtilCeos
    else:
       return SfpUtilNative
