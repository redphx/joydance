import asyncio
import json
import logging
import platform
import re
import socket
import time
from configparser import ConfigParser
from enum import Enum

import aiohttp
import hid
from aiohttp import WSMsgType, web
from pyjoycon import ButtonEventJoyCon, JoyCon
from pyjoycon.constants import JOYCON_PRODUCT_IDS, JOYCON_VENDOR_ID

from joydance import JoyDance, PairingState
from joydance.constants import (DEFAULT_CONFIG, JOYDANCE_VERSION,
                                WsSubprotocolVersion)

logging.getLogger('asyncio').setLevel(logging.WARNING)


class WsCommand(Enum):
    GET_JOYCON_LIST = 'get_joycon_list'
    CONNECT_JOYCON = 'connect_joycon'
    DISCONNECT_JOYCON = 'disconnect_joycon'
    UPDATE_JOYCON_STATE = 'update_joycon_state'


class PairingMethod(Enum):
    DEFAULT = 'default'
    FAST = 'fast'
    STADIA = 'stadia'
    OLD = 'old'


REGEX_PAIRING_CODE = re.compile(r'^\d{6}$')
REGEX_LOCAL_IP_ADDRESS = re.compile(r'^(192\.168|10.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5]))\.((\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.)(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])$')


async def get_device_ids():
    devices = hid.enumerate(JOYCON_VENDOR_ID, 0)

    out = []
    for device in devices:
        vendor_id = device['vendor_id']
        product_id = device['product_id']
        product_string = device['product_string']
        serial = device.get('serial') or device.get('serial_number')

        if product_id not in JOYCON_PRODUCT_IDS:
            continue

        if not product_string:
            continue

        out.append({
            'vendor_id': vendor_id,
            'product_id': product_id,
            'serial': serial,
            'product_string': product_string,
        })

    return out


async def get_joycon_list(app):
    joycons = []
    devices = await get_device_ids()

    for dev in devices:
        if dev['serial'] in app['joycons_info']:
            info = app['joycons_info'][dev['serial']]
        else:
            joycon = JoyCon(dev['vendor_id'], dev['product_id'], dev['serial'])
            # Wait for initial data
            for _ in range(3):
                time.sleep(0.05)
                battery_level = joycon.get_battery_level()
                if battery_level > 0:
                    break

            color = '#%02x%02x%02x' % joycon.color_body

            # Temporary fix for Windows
            if platform.system() != 'Windows':
                joycon.__del__()

            info = {
                'vendor_id': dev['vendor_id'],
                'product_id': dev['product_id'],
                'serial': dev['serial'],
                'name': dev['product_string'],
                'color': color,
                'battery_level': battery_level,
                'is_left': joycon.is_left(),
                'state': PairingState.IDLE.value,
                'pairing_code': '',
            }

            app['joycons_info'][dev['serial']] = info

        joycons.append(info)

    return sorted(joycons, key=lambda x: (x['name'], x['color'], x['serial']))


async def connect_joycon(app, ws, data):
    async def on_joydance_state_changed(serial, state):
        print(serial, state)
        app['joycons_info'][serial]['state'] = state.value
        try:
            await ws_send_response(ws, WsCommand.UPDATE_JOYCON_STATE, app['joycons_info'][serial])
        except Exception as e:
            print(e)

    print(data)

    serial = data['joycon_serial']
    product_id = app['joycons_info'][serial]['product_id']
    vendor_id = app['joycons_info'][serial]['vendor_id']

    pairing_method = data['pairing_method']
    host_ip_addr = data['host_ip_addr']
    console_ip_addr = data['console_ip_addr']
    pairing_code = data['pairing_code']

    if not is_valid_pairing_method(pairing_method):
        return

    if pairing_method == PairingMethod.DEFAULT.value:
        if not is_valid_ip_address(host_ip_addr) or not is_valid_pairing_code(pairing_code):
            return

    if pairing_method == PairingMethod.FAST.value and not is_valid_ip_address(console_ip_addr):
        return

    config_parser = parse_config()
    config = dict(config_parser.items('joydance'))
    config['pairing_code'] = pairing_code
    config['pairing_method'] = pairing_method
    config['host_ip_addr'] = host_ip_addr
    config['console_ip_addr'] = console_ip_addr
    config_parser['joydance'] = config
    save_config(config_parser)

    if pairing_method == PairingMethod.DEFAULT.value or pairing_method == PairingMethod.STADIA.value:
        app['joycons_info'][serial]['pairing_code'] = pairing_code
        console_ip_addr = None
    else:
        app['joycons_info'][serial]['pairing_code'] = ''

    joycon = ButtonEventJoyCon(vendor_id, product_id, serial)

    if pairing_method == PairingMethod.OLD.value:
        protocol_version = WsSubprotocolVersion.V1
    else:
        protocol_version = WsSubprotocolVersion.V2

    joydance = JoyDance(
        joycon,
        protocol_version=protocol_version,
        pairing_code=pairing_code,
        host_ip_addr=host_ip_addr,
        console_ip_addr=console_ip_addr,
        on_state_changed=on_joydance_state_changed,
    )
    app['joydance_connections'][serial] = joydance

    asyncio.create_task(joydance.pair())


async def disconnect_joycon(app, ws, data):
    print(data)
    serial = data['joycon_serial']
    joydance = app['joydance_connections'][serial]
    app['joycons_info'][serial]['state'] = PairingState.IDLE.value

    await joydance.disconnect()
    try:
        await ws_send_response(ws, WsCommand.UPDATE_JOYCON_STATE, {
            'joycon_serial': serial,
            'state': PairingState.IDLE.value,
        })
    except Exception:
        pass


def parse_config():
    parser = ConfigParser()
    parser.read('config.cfg')

    if 'joydance' not in parser:
        parser['joydance'] = DEFAULT_CONFIG
    else:
        tmp_config = DEFAULT_CONFIG.copy()
        for key in tmp_config:
            if key in parser['joydance']:
                val = parser['joydance'][key]
                if key == 'pairing_method':
                    if not is_valid_pairing_method(val):
                        val = PairingMethod.DEFAULT.value
                elif key == 'host_ip_addr' or key == 'console_ip_addr':
                    if not(is_valid_ip_address(val)):
                        val = ''
                elif key == 'pairing_code':
                    if not is_valid_pairing_code(val):
                        val = ''
                elif key.startswith('accel_'):
                    try:
                        val = int(val)
                    except Exception:
                        val = DEFAULT_CONFIG[key]

                tmp_config[key] = val

        parser['joydance'] = tmp_config

    if not parser['joydance']['host_ip_addr']:
        host_ip_addr = get_host_ip()
        if host_ip_addr:
            parser['joydance']['host_ip_addr'] = host_ip_addr

    save_config(parser)
    return parser


def is_valid_pairing_code(val):
    return re.match(REGEX_PAIRING_CODE, val) is not None


def is_valid_ip_address(val):
    return re.match(REGEX_LOCAL_IP_ADDRESS, val) is not None


def is_valid_pairing_method(val):
    return val in [
        PairingMethod.DEFAULT.value,
        PairingMethod.FAST.value,
        PairingMethod.STADIA.value,
        PairingMethod.OLD.value,
    ]


def get_host_ip():
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip.startswith('192.168') or ip.startswith('10.'):
                return ip
    except Exception:
        pass

    return None


def save_config(parser):
    with open('config.cfg', 'w') as fp:
        parser.write(fp)


async def on_startup(app):
    print('''
     ░░  ░░░░░░  ░░    ░░ ░░░░░░   ░░░░░  ░░░    ░░  ░░░░░░ ░░░░░░░
     ▒▒ ▒▒    ▒▒  ▒▒  ▒▒  ▒▒   ▒▒ ▒▒   ▒▒ ▒▒▒▒   ▒▒ ▒▒      ▒▒
     ▒▒ ▒▒    ▒▒   ▒▒▒▒   ▒▒   ▒▒ ▒▒▒▒▒▒▒ ▒▒ ▒▒  ▒▒ ▒▒      ▒▒▒▒▒
▓▓   ▓▓ ▓▓    ▓▓    ▓▓    ▓▓   ▓▓ ▓▓   ▓▓ ▓▓  ▓▓ ▓▓ ▓▓      ▓▓
 █████   ██████     ██    ██████  ██   ██ ██   ████  ██████ ███████

Open http://localhost:32623 in your browser.''')

    # Check for update
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.github.com/repos/redphx/joydance/releases/latest', ssl=False) as resp:
            json_body = await resp.json()
            latest_version = json_body['tag_name'][1:]
            print('Running version {}.'.format(JOYDANCE_VERSION))
            if JOYDANCE_VERSION != latest_version:
                print('\033[93m{}\033[00m'.format('Version {} is available: https://github.com/redphx/joydance'.format(latest_version)))


async def html_handler(request):
    config = dict((parse_config()).items('joydance'))
    with open('static/index.html', 'r') as f:
        html = f.read()
        html = html.replace('[[CONFIG]]', json.dumps(config))
        html = html.replace('[[VERSION]]', JOYDANCE_VERSION)
        return web.Response(text=html, content_type='text/html')


async def ws_send_response(ws, cmd, data):
    resp = {
        'cmd': 'resp_' + cmd.value,
        'data': data,
    }
    await ws.send_json(resp)


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            msg = msg.json()
            try:
                cmd = WsCommand(msg['cmd'])
            except ValueError:
                print('Invalid cmd:', msg['cmd'])
                continue

            if cmd == WsCommand.GET_JOYCON_LIST:
                joycon_list = await get_joycon_list(request.app)
                await ws_send_response(ws, cmd, joycon_list)
            elif cmd == WsCommand.CONNECT_JOYCON:
                await connect_joycon(request.app, ws, msg['data'])
                await ws_send_response(ws, cmd, {})
            elif cmd == WsCommand.DISCONNECT_JOYCON:
                await disconnect_joycon(request.app, ws, msg['data'])
                await ws_send_response(ws, cmd, {})
        elif msg.type == WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    return ws


def favicon_handler(request):
    return web.FileResponse('static/favicon.png')


app = web.Application()
app['joydance_connections'] = {}
app['joycons_info'] = {}

app.on_startup.append(on_startup)
app.add_routes([
    web.get('/', html_handler),
    web.get('/favicon.png', favicon_handler),
    web.get('/ws', websocket_handler),
    web.static('/css', 'static/css'),
    web.static('/js', 'static/js'),
])

web.run_app(app, port=32623)
