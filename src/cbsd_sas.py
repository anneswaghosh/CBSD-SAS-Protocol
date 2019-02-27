import json
import logging
import os
import time
import common_strings
import sas
import sas_testcase


class server:
  def __init__ (self):
    self._sas, self._sas_admin = sas.GetTestingSas()
    self.reg_id = 0
    self.t_reg_fail_retry = 0
    self.suggested_channel = []
    self.error_code = error_code ()


class error_code:
  def __init__ (self):
    self.general_ec = 0
    self.reg_ec = 0
    self.inq_ec = 0

class client:
  def __init__ (self):
    self.server = server ()
    self.client_state = 0
    self.grant_list = []

  #Registration function
  def registration (self):
    #Load Device
    device = json.load (open(os.path.join('configs', 'device.json')))

    # Pre-load conditionals
    conditionals = {
        'cbsdCategory': device['cbsdCategory'],
        'fccId': device['fccId'],
        'cbsdSerialNumber': device['cbsdSerialNumber'],
        'airInterface': device['airInterface'],
        'installationParam': device['installationParam'],
        'measCapability': device['measCapability']
    }

    # Inject FCC ID
    self.server._sas_admin.InjectFccId({'fccId': device['fccId']})

    # Inject User IDs
    self.server._sas_admin.InjectUserId({'userId': device['userId']})

    self.server._sas_admin.PreloadRegistrationData(conditionals)

    # Remove conditionals from registration
    del device['cbsdCategory']
    del device['airInterface']
    del device['installationParam']
    del device['measCapability']

    # Register the devices
    devices = [device]
    request = {'registrationRequest': devices}
    response = self.server._sas.Registration(request)

    if (response):
      if (response['registrationResponse'][0]['response']['responseCode'] == 0)
        
        #Client state changed to registered
        self.client_state = 1
        self.server.reg_id = response['registrationResponse'][0]['cbsdId']
        return True


