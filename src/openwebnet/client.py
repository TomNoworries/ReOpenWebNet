# -*- coding: utf-8 -*-
import socket
from logging import getLogger
import threading

from openwebnet import messages
from openwebnet.password import calculate_password

_LOGGER = getLogger(__name__)

class CommandClient:
    def __init__(self, host, port, password):
        self._host = host
        self._port = int(port)
        self._password = password
        self._session = False
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._lock = threading.Lock()

    def connect(self):
        _LOGGER.info("connecting with %s:%s",self._host, self._port)
        try:
            self._socket.connect((self._host, self._port))
            return True
        except IOError:
            _LOGGER.exception("Could not connect")
            self._socket.close()
            return False

    def send_data(self, data):
        _LOGGER.debug("---> %s", data)
        self._socket.send(data.encode())

    def read_data(self):
        data = str(self._socket.recv(1024).decode())
        _LOGGER.debug("<--- %s", data)
        return data

    def cmd_session(self):
        connected = self.connect()
        if not connected:
            return

        if self.read_data() == messages.NACK:
            _LOGGER.exception("Could not initialize connection with the gateway")

        self.send_data(messages.CMD_SESSION)

        answer = self.read_data()
        if answer == messages.NACK:
            _LOGGER.exception("The gateway refused the session command")
            return False

        self.send_password(answer)

        if self.read_data() == messages.NACK:
            _LOGGER.exception("Password refused")
        else:
            self._session = True

    def send_password(self, nonce):
        psw_open = '*#' + str(calculate_password(self._password, nonce)) + '##'
        self.send_data(psw_open)

    def extract_values(self, answer):
        value_list = []
        index = 0
        while index <= len(answer) - 1:
            if answer[index] != '*' and answer[index] != '#':
                length = 0
                val = ''
                while length <= len(answer) - 1 - index:
                    if answer[index + length] != '*' and answer[index + length] != '#':
                        length = length + 1
                    else:
                        break
                val = val + answer[index:index + length]
                value_list.append(val)
                index = index + length
            index = index + 1
        return value_list

    # Check that bus sent all the data
    def check_answer(self, message):
        if message[len(message) - 6:] != messages.ACK and message[len(message) - 6:] != messages.NACK:
            # the answer is not completed, read again from bus
            end_message = self.read_data()
            return message + end_message

        if message[len(message) - 6:] == messages.NACK:
            _LOGGER.exception("Error: command execuction failed")

        return message

    def normal_request(self, who, where, what):
        with self._lock:
            if not self._session:
                self.cmd_session()

            normal_request = '*' + who + '*' + what + '*' + where + '##'
            self.send_data(normal_request)

            message = self.read_data()
            if message == messages.NACK:
                _LOGGER.exception("Error: command execution failed")

    def request_state(self, who, where):
        with self._lock:
            if not self._session:
                self.cmd_session()

            request = '*#' + who + '*' + where + '##'

            self.send_data(request)
            response = self.read_response_values()
            attempts_left=3
            while response[2] != where and attempts_left > 0:
                logger.debug("asked for status of %s, but got status of %s, trying again"%(where, response[2]))
                self.send_data(request)
                response = self.read_response_values()
                attempts_left -= 1

            if response[2] != where:
                logger.warn("Oh-oh, did not get desired response after 3 tries:", where, response)
                return False
            return response[1] == '1'

    def read_response_values(self):
        message = self.read_data()
        check_message = self.check_answer(message)
        if message[len(message) - 6:] == messages.NACK:
            return None
        else:
            extracted = self.extract_values(check_message[:len(check_message) - 6])
            return extracted

    def dimension_read_request(self, who, where, dimension):
        if not self._session:
            self.cmd_session()

        dimension_request = '*#' + who + '*' + where + '*' + dimension + '##'
        self.send_data(dimension_request)

        return self.read_response_values()

    def dimension_write_request(self, who, where, dimension, values):
        if not self._session:
            self.cmd_session()

        write_values = ''.join(['*%s'%item for item in values])
        write_request = '*#' + who + '*' + where + '*#' + dimension + write_values + '##'
        self.send_data(write_request)

        return self.read_data()

    def light_on(self, where):
        self.normal_request('1', where, '1')

    def light_off(self, where):
        self.normal_request('1', where, '0')

    def light_status(self, where):
        state = self.request_state('1', where)

        #if state[1] == '1':
        #    return True
        #else:
        #    return False

        return state

    def read_temperature(self, where):
        temperature = self.dimension_read_request('4', where, '0')
        return float(temperature[3]) / 10.0

    def read_set_temperature(self, where):
        temperature = self.dimension_read_request('4', where, '14')
        return float(temperature[3]) / 10.0

    def read_valve_status(self, where):
        valve_status = self.dimension_read_request('4', where, '19')
        if valve_status[4] == '0':
            return 'OFF'
        else:
            return 'ON'

