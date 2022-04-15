import asyncio
import json
import random
import socket
import ssl
import time
from enum import Enum

import aiohttp
import websockets

from .constants import (ACCEL_ACQUISITION_FREQ_HZ, ACCEL_ACQUISITION_LATENCY,
                        ACCEL_MAX_RANGE, ACCEL_SEND_RATE, JOYCON_UPDATE_RATE,
                        SHORTCUT_MAPPING, UBI_APP_ID, UBI_SKU_ID,
                        WS_SUBPROTOCOL, Command, JoyConButton)


class PairingState(Enum):
    IDLE = 0
    GETTING_TOKEN = 1
    PAIRING = 2
    CONNECTING = 3
    CONNECTED = 4
    DISCONNECTING = 5
    DISCONNECTED = 10

    ERROR_JOYCON = 101
    ERROR_CONNECTION = 102
    ERROR_INVALID_PAIRING_CODE = 103
    ERROR_PUNCH_PAIRING = 104
    ERROR_HOLE_PUNCHING = 105
    ERROR_CONSOLE_CONNECTION = 106


class JoyDance:
    def __init__(
            self,
            joycon,
            pairing_code=None,
            host_ip_addr=None,
            console_ip_addr=None,
            accel_acquisition_freq_hz=ACCEL_ACQUISITION_FREQ_HZ,
            accel_acquisition_latency=ACCEL_ACQUISITION_LATENCY,
            accel_max_range=ACCEL_MAX_RANGE,
            on_state_changed=None):
        self.joycon = joycon
        self.joycon_is_left = joycon.is_left()

        if on_state_changed:
            self.on_state_changed = on_state_changed

        self.pairing_code = pairing_code
        self.host_ip_addr = host_ip_addr
        self.console_ip_addr = console_ip_addr
        self.host_port = self.get_random_port()

        self.accel_acquisition_freq_hz = accel_acquisition_freq_hz
        self.accel_acquisition_latency = accel_acquisition_latency
        self.accel_max_range = accel_max_range

        self.number_of_accels_sent = 0
        self.should_start_accelerometer = False
        self.is_input_allowed = False
        self.available_shortcuts = set()

        self.ws = None
        self.disconnected = False

        self.headers = {
            'Ubi-AppId': UBI_APP_ID,
            'X-SkuId': UBI_SKU_ID,
        }

        self.console_conn = None

    def get_random_port(self):
        ''' Randomize a port number, to be used in hole_punching() later '''
        return random.randrange(39000, 39999)

    async def on_state_changed(state):
        pass

    async def get_access_token(self):
        ''' Log in using a guest account, pre-defined by Ubisoft '''
        headers = {
            'Authorization': 'UbiMobile_v1 t=NTNjNWRjZGMtZjA2Yy00MTdmLWJkMjctOTNhZTcxNzU1OTkyOlcwM0N5eGZldlBTeFByK3hSa2hhQ05SMXZtdz06UjNWbGMzUmZaVzB3TjJOYTpNakF5TVMweE1DMHlOMVF3TVRvME5sbz0=',
            'Ubi-AppId': UBI_APP_ID,
            'User-Agent': 'UbiServices_SDK_Unity_Light_Mobile_2018.Release.16_ANDROID64_dynamic',
            'Ubi-RequestedPlatformType': 'ubimobile',
            'Content-Type': 'application/json',
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post('https://public-ubiservices.ubi.com/v1/profiles/sessions', json={}, ssl=False) as resp:
                if resp.status != 200:
                    await self.on_state_changed(self.joycon.serial, PairingState.ERROR_CONNECTION)
                    raise Exception('ERROR: Couldn\'t get access token!')

                # Add ticket to headers
                json_body = await resp.json()
                self.headers['Authorization'] = 'Ubi_v1 ' + json_body['ticket']

    async def send_pairing_code(self):
        ''' Send pairing code to JD server '''
        url = 'https://prod.just-dance.com/sessions/v1/pairing-info'

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params={'code': self.pairing_code}, ssl=False) as resp:
                if resp.status != 200:
                    await self.on_state_changed(self.joycon.serial, PairingState.ERROR_INVALID_PAIRING_CODE)
                    raise Exception('ERROR: Invalid pairing code!')

                json_body = await resp.json()
                self.pairing_url = json_body['pairingUrl'].replace('https://', 'wss://') + 'smartphone'
                self.requires_punch_pairing = json_body.get('requiresPunchPairing', False)

    async def send_initiate_punch_pairing(self):
        ''' Tell console which IP address & port to connect to '''
        url = 'https://prod.just-dance.com/sessions/v1/initiate-punch-pairing'
        json_payload = {
            'pairingCode': self.pairing_code,
            'mobileIP': self.host_ip_addr,
            'mobilePort': self.host_port,
        }

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(url, json=json_payload, ssl=False) as resp:
                body = await resp.text()
                if body != 'OK':
                    await self.on_state_changed(self.joycon.serial, PairingState.ERROR_PUNCH_PAIRING)
                    raise Exception('ERROR: Couldn\'t initiate punch pairing!')

    async def hole_punching(self):
        ''' Open a port on this machine so the console can connect to it '''
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.bind(('0.0.0.0', self.host_port))
            conn.listen(5)

            # Accept incoming connection from console
            console_conn, addr = conn.accept()
            self.console_conn = console_conn
            print('Connected with {}:{}'.format(addr[0], addr[1]))
        except Exception as e:
            await self.on_state_changed(self.joycon.serial, PairingState.ERROR_HOLE_PUNCHING)
            raise e

    async def send_message(self, __class, data={}):
        ''' Send JSON message to server '''
        if __class != 'JD_PhoneScoringData':
            print('>>>', __class, data)

        msg = {'root': {'__class': __class}}
        if data:
            msg['root'].update(data)

        # Remove extra spaces from JSON to reduce size

        try:
            await self.ws.send(json.dumps(msg, separators=(',', ':')))
        except Exception:
            await self.disconnect(close_ws=False)

    async def on_message(self, message):
        message = json.loads(message)
        print('<<<', message)

        __class = message['__class']
        if __class == 'JD_PhoneDataCmdHandshakeContinue':
            await self.send_message('JD_PhoneDataCmdSync', {'phoneID': message['phoneID']})
        elif __class == 'JD_PhoneDataCmdSyncEnd':
            await self.send_message('JD_PhoneDataCmdSyncEnd', {'phoneID': message['phoneID']})
            await self.on_state_changed(self.joycon.serial, PairingState.CONNECTED)
        elif __class == 'JD_EnableAccelValuesSending_ConsoleCommandData':
            self.should_start_accelerometer = True
            self.number_of_accels_sent = 0
        elif __class == 'JD_DisableAccelValuesSending_ConsoleCommandData':
            self.should_start_accelerometer = False
        elif __class == 'InputSetup_ConsoleCommandData':
            if message.get('isEnabled', 0) == 1:
                self.is_input_allowed = True
        elif __class == 'EnableCarousel_ConsoleCommandData':
            if message.get('isEnabled', 0) == 1:
                self.is_input_allowed = True
        elif __class == 'JD_EnableLobbyStartbutton_ConsoleCommandData':
            if message.get('isEnabled', 0) == 1:
                self.is_input_allowed = True
        elif __class == 'ShortcutSetup_ConsoleCommandData':
            if message.get('isEnabled', 0) == 1:
                self.is_input_allowed = True
        elif __class == 'JD_PhoneUiShortcutData':
            shortcuts = set()
            for item in message.get('shortcuts', []):
                if item['__class'] == 'JD_PhoneAction_Shortcut':
                    try:
                        shortcuts.add(Command(item['shortcutType']))
                    except Exception as e:
                        print('Unknown Command: ', e)
            self.available_shortcuts = shortcuts
        elif __class == 'JD_OpenPhoneKeyboard_ConsoleCommandData':
            await asyncio.sleep(1)
            await self.send_message('JD_CancelKeyboard_PhoneCommandData')
        elif __class == 'JD_PhoneUiSetupData':
            self.is_input_allowed = True
            shortcuts = set()
            if message.get('setupData', {}).get('gameplaySetup', {}).get('pauseSlider', {}):
                self.available_shortcuts.add(Command.PAUSE)

            if message['isPopup'] == 1:
                self.is_input_allowed = True
            else:
                self.is_input_allowed = (message.get('inputSetup', {}).get('isEnabled', 0) == 1)

    async def send_hello(self):
        print('Pairing...')

        await self.send_message('JD_PhoneDataCmdHandshakeHello', {
            'accelAcquisitionFreqHz': float(self.accel_acquisition_freq_hz),
            'accelAcquisitionLatency': float(self.accel_acquisition_latency),
            'accelMaxRange': float(self.accel_max_range),
        })

        async for message in self.ws:
            await self.on_message(message)

    async def send_accelerometer_data(self):
        accel_data = []
        delta_time = 0

        end = time.time()

        while True:
            if self.disconnected:
                break

            if not self.should_start_accelerometer:
                await asyncio.sleep(0.5)
                continue

            start = time.time()
            if delta_time > ACCEL_SEND_RATE:
                delta_time = 0
                while len(accel_data) > 0:
                    accels_num = min(len(accel_data), 10)

                    await self.send_message('JD_PhoneScoringData', {
                        'accelData': accel_data[:accels_num],
                        'timeStamp': self.number_of_accels_sent,
                    })

                    self.number_of_accels_sent += accels_num
                    accel_data = accel_data[accels_num:]

            try:
                await asyncio.sleep(JOYCON_UPDATE_RATE)
                joycon_status = self.joycon.get_status()
            except OSError:
                self.disconnect()
                return

            # Accelerator axes on phone & Joy-Con are different so we need to swap some axes
            # https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/imu_sensor_notes.md
            accel = joycon_status['accel']
            x = accel['y'] * -1
            y = accel['x']
            z = accel['z']

            accel_data.append([x, y, z])

            end = time.time()
            delta_time += (end - start) * 1000

    async def send_command(self):
        ''' Capture Joycon's input and send to console '''
        while True:
            try:
                if self.disconnected:
                    return

                if not self.is_input_allowed and not self.should_start_accelerometer:
                    await asyncio.sleep(JOYCON_UPDATE_RATE * 5)
                    continue

                await asyncio.sleep(JOYCON_UPDATE_RATE * 5)

                cmd = None
                # Get pressed button
                for event_type, status in self.joycon.events():
                    if status == 0:  # 0 = pressed, 1 = released
                        continue

                    joycon_button = JoyConButton(event_type)
                    if self.should_start_accelerometer:  # Can only send Pause command while playing
                        if joycon_button == JoyConButton.PLUS or joycon_button == JoyConButton.MINUS:
                            cmd = Command.PAUSE
                    else:
                        if joycon_button == JoyConButton.A or joycon_button == JoyConButton.RIGHT:
                            cmd = Command.ACCEPT
                        elif joycon_button == JoyConButton.B or joycon_button == JoyConButton.DOWN:
                            cmd = Command.BACK
                        elif joycon_button in SHORTCUT_MAPPING:
                            # Get command depends on which button was pressed & which shortcuts are available
                            for shortcut in SHORTCUT_MAPPING[joycon_button]:
                                if shortcut in self.available_shortcuts:
                                    cmd = shortcut
                                    break

                # Get joystick direction
                if not self.should_start_accelerometer and not cmd:
                    status = self.joycon.get_status()

                    # Check which Joycon (L/R) is being used
                    stick = status['analog-sticks']['left'] if self.joycon_is_left else status['analog-sticks']['right']
                    vertical = stick['vertical']
                    horizontal = stick['horizontal']

                    if vertical < -0.5:
                        cmd = Command.DOWN
                    elif vertical > 0.5:
                        cmd = Command.UP
                    elif horizontal < -0.5:
                        cmd = Command.LEFT
                    elif horizontal > 0.5:
                        cmd = Command.RIGHT

                # Send command to server
                if cmd:
                    if cmd == Command.PAUSE:
                        __class = 'JD_Pause_PhoneCommandData'
                        data = {}
                    elif type(cmd.value) == str:
                        __class = 'JD_Custom_PhoneCommandData'
                        data = {
                            'identifier': cmd.value,
                        }
                    else:
                        __class = 'JD_Input_PhoneCommandData'
                        data = {
                            'input': cmd.value,
                        }

                    # Only send input when it's allowed to, otherwise we might get a disconnection
                    if self.is_input_allowed:
                        await self.send_message(__class, data)
                        await asyncio.sleep(0.01)
            except Exception as e:
                print(e)
                await self.disconnect()

    async def connect_ws(self):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.set_ciphers('ALL')
        ssl_context.options &= ~ssl.OP_NO_SSLv3
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        server_hostname = self.console_conn.getpeername()[0] if self.console_conn else None
        try:
            async with websockets.connect(
                    self.pairing_url,
                    subprotocols=[WS_SUBPROTOCOL],
                    sock=self.console_conn,
                    ssl=ssl_context,
                    ping_timeout=None,
                    server_hostname=server_hostname
            ) as websocket:
                try:
                    self.ws = websocket
                    await asyncio.gather(
                        self.send_hello(),
                        self.send_accelerometer_data(),
                        self.send_command(),
                    )

                except websockets.ConnectionClosed:
                    await self.on_state_changed(self.joycon.serial, PairingState.ERROR_CONSOLE_CONNECTION)
                    await self.disconnect(close_ws=False)
        except Exception:
            await self.on_state_changed(self.joycon.serial, PairingState.ERROR_CONSOLE_CONNECTION)
            await self.disconnect(close_ws=False)

    async def disconnect(self, close_ws=True):
        print('disconnected')
        self.disconnected = True
        self.joycon.__del__()

        if close_ws and self.ws:
            await self.ws.close()

    async def pair(self):
        try:
            if self.console_ip_addr:
                await self.on_state_changed(self.joycon.serial, PairingState.CONNECTING)
                self.pairing_url = 'wss://{}:8080/smartphone'.format(self.console_ip_addr)
            else:
                await self.on_state_changed(self.joycon.serial, PairingState.GETTING_TOKEN)
                print('Getting authorication token...')
                await self.get_access_token()

                await self.on_state_changed(self.joycon.serial, PairingState.PAIRING)
                print('Sending pairing code...')
                await self.send_pairing_code()

                await self.on_state_changed(self.joycon.serial, PairingState.CONNECTING)
                print('Connecting with console...')
                if self.requires_punch_pairing:
                    await self.send_initiate_punch_pairing()
                    await self.hole_punching()

            await self.connect_ws()
        except Exception as e:
            await self.disconnect()
            print(e)
