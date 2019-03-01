import json
import logging
import os
import time
import common_strings
import sas
import sas_testcase
from datetime import datetime
from threading import Timer


class server:
  def __init__ (self):
    self._sas, self._sas_admin = sas.GetTestingSas()
    self.reg_id = 0
    self.t_reg_fail_retry = 10
    self.reg_retry_timer = None
    self.suggested_channel = []
    self.error_code = error_code ()


class error_code:
  def __init__ (self):
    self.general_ec = 0
    self.reg_ec = 0
    self.inq_ec = 0

class channel:
  def __init__ (self):
    self.low_freq = 0
    self.high_freq = 0
    self.channel_type = None

class grant_info:
  def __init__ (self):
    self.channel = channel ()
    self.grant_id = 0
    self.grant_error_code = 0
    self.heartbeat_error_code = 0
    self.grant_state = 0
    self.grant_renew = False
    self.transmission = False

    self.t_heartbeat_int = 0
    self.heartbeat_interval = None

    self.t_grant_exp_timer = 0
    self.grant_expire_timer = None

    self.t_transmit_exp_timer = 0
    self.transmit_expire_timer = None

    self.t_grant_renew_timer = 0

    #back pointer to the client
    self.cbsd = None

  def release_grant (self):
    self.grant_id = 0
    self.grant_state = 0
    self.t_heartbeat_int = 0
    self.heartbeat_interval = None

    self.t_grant_exp_timer = 0
    self.grant_expire_timer = None

    self.t_transmit_exp_timer = 0
    self.transmit_expire_timer = None
    

  def grant_timer_expiry_handler (self):
    if (self.grant_renew == True):
        self.t_grant_exp_timer = self.t_grant_renew_timer
        self.grant_expire_timer = Timer (self.t_grant_exp_timer,
                                  self.grant_timer_expiry_handler)

        self.grant_expire_timer.start()

    else:
      self.release_grant ()


  def transmit_time_expiry_handler (self):
    if (self.grant_state == 2):
      #stop transmitting within 60 seconds
      self.transmission = False

      #Granted state
      self.grant_state = 1
    

  def heartbeat (self):
    cbsd = self.cbsd
    cbsd_id = cbsd.server.reg_id
    grant_id = self.grant_id

    heartbeat_request = {
        'cbsdId': cbsd_id,
        'grantId': grant_id,
        'operationState': 'GRANTED'
    }

    # Send heartbeat request
    request = {'heartbeatRequest': [heartbeat_request]}
    response = cbsd.server._sas.Heartbeat(request)['heartbeatResponse'][0]

    #Success or Suspended_Grant
    if (response['response']['responseCode'] == 0 or
        response['response']['responseCode'] == 501):

      if (response['response']['responseCode'] == 0):
        #Authorized
        self.grant_state = 2

      if (response['transmitExpireTime']):
        #If the transmit timer is not started
        if (self.t_transmit_exp_timer == 0):
          self.t_transmit_exp_timer = datetime.strptime(response['transmitExpireTime'],
                                             '%Y-%m-%dT%H:%M:%SZ')

          #change it later (Hardcoded for now)
          self.transmit_expire_timer = Timer (1000,
                                          self.transmit_time_expiry_handler)
          self.transmit_expire_timer.start()

      if (self.grant_renew == True):
        if (response['grantExpireTime']):
          self.t_grant_renew_timer = response['grantExpireTime']

      if ('heartBeatInterval' in response):
        if (response['heartBeatInterval']):
          self.t_heartbeat_int = response['heartBeatInterval']

      #schedule for the next heartbeat
      self.heartbeat_interval = Timer (self.t_heartbeat_int - 5,
                                              self.heartbeat)
      self.heartbeat_interval.start()

      if (self.transmission == False and
          response['response']['responseCode'] == 0):
        #start transmission
        self.transmission = True

    #Terminated Grant
    elif (response['response']['responseCode'] == 500):
      self.grant_state = 0

      if (response['transmitExpireTime']):
        #If the transmit timer is not started
        if (self.t_transmit_exp_timer == 0):
          self.t_transmit_exp_timer = datetime.strptime(response['transmitExpireTime'],
                                             '%Y-%m-%dT%H:%M:%SZ')

          #change it later (Hardcoded for now)
          self.transmit_expire_timer = Timer (1000,
                                          self.transmit_time_expiry_handler)
          self.transmit_expire_timer.start()

    #Unsync_op_param
    elif (response['response']['responseCode'] == 502):

      #stop transmission within 60 sec
      self.transmission = False

      #send relinqishmentrequest object

    #Faulty parameters
    else:
      if ('heartBeatInterval' in response):
        if (response['heartBeatInterval']):
          self.t_heartbeat_int = response['heartBeatInterval']

      #schedule for the next heartbeat
      self.heartbeat_interval = Timer (self.t_heartbeat_int - 5,
                                              self.heartbeat)
      self.heartbeat_interval.start()



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
      if (response['registrationResponse'][0]['response']['responseCode'] == 0):
        
        #Client state changed to registered
        self.client_state = 1
        self.server.reg_id = response['registrationResponse'][0]['cbsdId']
        return True

      #Not Blacklisted
      elif (response['registrationResponse'][0]['response']['responseCode'] != 101):
        error = response['registrationResponse'][0]['response']['responseCode']
        if (error <= 199):
          self.server.error_code.general_ec = error

        elif (error >= 200 and error <= 299):
          self.server.error_code.reg_ec = error

        self.server.reg_retry_timer = Timer (self.server.t_reg_fail_retry, self.registration)
        self.server.reg_retry_timer.start()
        return False

      #Blacklisted
      else:
        return False

  #Grant function
  def grant (self):
    cbsd_id = self.server.reg_id

    if (cbsd_id == 0):
      return

    temp_grant = grant_info()

    #init state
    temp_grant.grant_state = 0

    #Fix frequency for now
    low_frequency = 3600000000
    high_frequency = 3610000000

    grant = json.load(
        open(os.path.join('configs', 'grant_0.json')))

    grant['cbsdId'] = cbsd_id
    grant['operationParam']['operationFrequencyRange']['lowFrequency'] \
        = low_frequency
    grant['operationParam']['operationFrequencyRange']['highFrequency'] \
        = high_frequency

    request = {'grantRequest': [grant]}
    response = self.server._sas.Grant(request)['grantResponse'][0]

    response_code = response['response']['responseCode']

    #success
    if (response_code == 0):

      temp_grant.grant_id = response['grantId']

      #granted state
      temp_grant.grant_state = 1

      temp_grant.channel.low_freq = low_frequency
      temp_grant.channel.high_freq = high_frequency
      temp_grant.channel.channel_type = response['channelType']

      if (response['grantExpireTime']):
        temp_grant.t_grant_exp_timer = response['grantExpireTime']
        temp_grant.grant_expire_timer = Timer (temp_grant.t_grant_exp_timer,
                                        temp_grant.grant_timer_expiry_handler)
        temp_grant.grant_expire_timer.start()

      if (response['heartBeatInterval']):
        temp_grant.t_heartbeat_int = response['heartBeatInterval']
        temp_grant.heartbeat_interval = Timer (temp_grant.t_heartbeat_int - 5,
                                               temp_grant.heartbeat)
        temp_grant.heartbeat_interval.start()

      #back pointer      
      temp_grant.cbsd = self

      self.grant_list.append (temp_grant) 
