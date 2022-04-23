import { h, Component, render } from '/js/preact.module.js';
import htm from '/js/htm.module.js';

// Initialize htm with Preact
const html = htm.bind(h);
window.mitty = mitt()

const SVG_BATTERY_LEVEL = html`<svg style="enable-background:new 0 0 16 16" viewBox="0 0 16 16" xml:space="preserve" xmlns="http://www.w3.org/2000/svg"><path d="M15 4H0v8h15V9h1V7h-1V4zm-1 3v4H1V5h13v2z"/><rect class="battery-bar-4" height="4" width="2" x="11" y="6"/><rect class="battery-bar-3" height="4" width="2" x="8" y="6"/><rect class="battery-bar-2" height="4" width="2" x="5" y="6"/><rect class="battery-bar-1" height="4" width="2" x="2" y="6"/></svg>`

const BATTERY_LEVEL = {
    4: 'full',
    3: 'medium',
    2: 'low',
    1: 'critical',
    0: 'critical',
}

const PairingMethod = {
    DEFAULT: 'default',
    FAST: 'fast',
    STADIA: 'stadia',
    OLD: 'old',
}

const WsCommand = {
    GET_JOYCON_LIST: 'get_joycon_list',
    CONNECT_JOYCON: 'connect_joycon',
    DISCONNECT_JOYCON: 'disconnect_joycon',
    UPDATE_JOYCON_STATE: 'update_joycon_state',
}

const PairingState = {
    IDLE: 0,
    GETTING_TOKEN: 1,
    PAIRING: 2,
    CONNECTING: 3,
    CONNECTED: 4,
    DISCONNECTING: 5,
    DISCONNECTED: 10,

    ERROR_JOYCON: 101,
    ERROR_CONNECTION: 102,
    ERROR_INVALID_PAIRING_CODE: 103,
    ERROR_PUNCH_PAIRING: 104,
    ERROR_HOLE_PUNCHING: 105,
    ERROR_CONSOLE_CONNECTION: 106,
}

const PairingStateMessage = {
    [PairingState.IDLE]: 'Idle',
    [PairingState.GETTING_TOKEN]: 'Getting auth token...',
    [PairingState.PAIRING]: 'Sending pairing code...',
    [PairingState.CONNECTING]: 'Connecting with console...',
    [PairingState.CONNECTED]: 'Connected!',
    [PairingState.DISCONNECTED]: 'Disconnected',

    [PairingState.ERROR_JOYCON]: 'Joy-Con problem!',
    [PairingState.ERROR_CONNECTION]: 'Couldn\'t get auth token!',
    [PairingState.ERROR_INVALID_PAIRING_CODE]: 'Invalid pairing code!',
    [PairingState.ERROR_PUNCH_PAIRING]: 'Couldn\'t punch pairing!',
    [PairingState.ERROR_HOLE_PUNCHING]: 'Couldn\'t connect with console!',
    [PairingState.ERROR_CONSOLE_CONNECTION]: 'Couldn\'t connect with console!',
}

class PairingMethodPicker extends Component {
    constructor(props) {
        super()
        this.state = {
            pairing_method: props.pairing_method,
        }

        this.onChange = this.onChange.bind(this)
    }

    onChange(e) {
        const pairing_method = e.target.value
        this.setState({
            pairing_method: pairing_method,
        })

        window.mitty.emit('update_method', pairing_method)
    }

    render(props) {
        return html`
            <label for="stacked-state">Pairing Method</label>
            <select id="stacked-state" onChange=${this.onChange} value=${props.pairing_method}>
                <optgroup label="JD 2020 and later">
                    <option value="${PairingMethod.DEFAULT}">Default: All platforms except Stadia</option>
                    <option value="${PairingMethod.FAST}">Fast: Xbox One/PlayStation/Nintendo Switch</option>
                    <option value="${PairingMethod.STADIA}">Stadia: for Stadia, obviously</option>
                </optgroup>
                <optgroup label="JD 2016-2019">
                    <option value="${PairingMethod.OLD}">Old: All platforms (incl. PC)</option>
                </optgroup>
            </select>
        `
    }
}

class PrivateIpAddress extends Component {
    constructor(props) {
        super(props)

        let lock_host = false
        let host_ip_addr = props.host_ip_addr
        let console_ip_addr = props.console_ip_addr

        let hostname = window.location.hostname
        if (hostname.startsWith('192.168.')) {
            host_ip_addr = hostname
            lock_host = true
        }

        this.state = {
            host_ip_addr: host_ip_addr,
            console_ip_addr: console_ip_addr,
            lock_host: lock_host,
        }

        this.onKeyPress = this.onKeyPress.bind(this)
        this.onChange = this.onChange.bind(this)
    }

    onChange(e) {
        const key = this.props.pairing_method == PairingMethod.DEFAULT ? 'host_ip_addr' : 'console_ip_addr'
        const value = e.target.value
        this.setState({
            [key]: value,
        })

        window.mitty.emit('update_addr', value)
    }

    onKeyPress(e) {
        if (!/[0-9\.]/.test(e.key)) {
            e.preventDefault()
            return
        }
    }

    componentDidMount() {
        let addr = this.props.pairing_method == PairingMethod.DEFAULT ? this.state.host_ip_addr : this.state.console_ip_addr
        window.mitty.emit('update_addr', addr)
    }

    render(props, state) {
        const pairing_method = props.pairing_method
        const addr = pairing_method == PairingMethod.DEFAULT ? state.host_ip_addr : state.console_ip_addr
        return html`
            <label>
                ${[PairingMethod.DEFAULT, PairingMethod.STADIA].indexOf(pairing_method) > -1 && html`Host's Private IP Address`}
                ${[PairingMethod.DEFAULT, PairingMethod.STADIA].indexOf(pairing_method) == -1 && html`Console's Private IP Address`}
            </label>

            ${(pairing_method == PairingMethod.STADIA) && html`
                <input readonly id="ipAddr" type="text" size="15" placeholder="Not Required" />
            `}

            ${(pairing_method == PairingMethod.DEFAULT && state.lock_host) && html`
                <input readonly id="ipAddr" type="text" size="15" placeholder="${addr}" />
            `}

            ${([PairingMethod.FAST, PairingMethod.OLD].indexOf(pairing_method) > -1 || (pairing_method == PairingMethod.DEFAULT && !state.lock_host)) && html`
                <input required id="ipAddr" type="text" inputmode="decimal" size="15" maxlength="15" placeholder="192.168.x.x" pattern="^192\\.168\\.((\\d{1,2}|1\\d\\d|2[0-4]\\d|25[0-5])\\.)(\\d{1,2}|1\\d\\d|2[0-4]\\d|25[0-5])$" value=${addr} onKeyPress=${this.onKeyPress} onChange="${this.onChange}" />
            `}

        `
    }
}

class PairingCode extends Component {
    constructor(props) {
        super(props)
        this.state = {
            pairing_code: props.pairing_code,
        }

        this.onChange = this.onChange.bind(this)
    }

    onChange(e) {
        const value = e.target.value
        this.setState({
            pairing_code: value,
        })

        window.mitty.emit('update_code', value)
    }

    render(props, state) {
        const pairing_method = props.pairing_method
        return html`
            <label>Pairing Code</label>
            ${[PairingMethod.DEFAULT, PairingMethod.STADIA].indexOf(pairing_method) > -1 && html`
                <input required id="pairingCode" type="text" inputmode="decimal" value=${state.pairing_code} placeholder="000000" maxlength="6" size="6" pattern="[0-9]{6}" onKeyPress=${(e) => !/[0-9]/.test(e.key) && e.preventDefault()} onChange=${this.onChange} />
            `}
            ${[PairingMethod.DEFAULT, PairingMethod.STADIA].indexOf(pairing_method) == -1 && html`
                <input type="text" id="pairingCode" value="" readonly placeholder="Not Required" size="12" />
            `}
        `
    }
}

class JoyCon extends Component {
    constructor(props) {
        super(props)

        this.connect = this.connect.bind(this)
        this.disconnect = this.disconnect.bind(this)
        this.onStateUpdated = this.onStateUpdated.bind(this)

        this.state = {
            ...props.joycon,
        }

        window.mitty.on('resp_' + WsCommand.DISCONNECT_JOYCON, this.onDisconnected)
        window.mitty.on('resp_' + WsCommand.UPDATE_JOYCON_STATE, this.onStateUpdated)
    }

    connect() {
        window.mitty.emit('req_' + WsCommand.CONNECT_JOYCON, this.props.joycon.serial)
    }

    disconnect() {
        window.mitty.emit('req_' + WsCommand.DISCONNECT_JOYCON, this.props.joycon.serial)
    }

    onStateUpdated(data) {
        if (data['serial'] != this.props.joycon.serial) {
            return
        }

        const state = data['state']
        if (PairingStateMessage.hasOwnProperty(state)) {
            this.setState({
                ...data,
            })
        }
    }

    render(props, { name, state, pairing_code, is_left, color, battery_level }) {
        const joyconState = state
        const stateMessage = PairingStateMessage[joyconState]
        let showButton = true
        if ([PairingState.GETTING_TOKEN, PairingState.PAIRING, PairingState.CONNECTING].indexOf(joyconState) > -1) {
            showButton = false
        }

        let joyconSvg
        if (is_left) {
            joyconSvg = html`<svg class="joycon-color" viewBox="0 0 171 453" xmlns="http://www.w3.org/2000/svg" xml:space="preserve" style="fill-rule:evenodd;clip-rule:evenodd"><path d="M219.594 33.518v412.688c0 1.023-.506 1.797-1.797 1.797h-49.64c-51.68 0-85.075-45.698-85.075-85.075V114.987c0-57.885 56.764-84.719 84.719-84.719h48.79c2.486 0 3.003 1.368 3.003 3.25zm-32.123 105.087c0 17.589-14.474 32.062-32.063 32.062-17.589 0-32.062-14.473-32.062-32.062s14.473-32.063 32.062-32.063 32.063 14.474 32.063 32.063z" style="fill:${color};stroke:#000;stroke-width:8.33px" transform="translate(-65.902 -13.089)"/></svg>`
        } else {
            joyconSvg = html`<svg class="joycon-color" viewBox="0 0 171 453" xmlns="http://www.w3.org/2000/svg" xml:space="preserve" style="fill-rule:evenodd;clip-rule:evenodd"><path d="M324.763 40.363v412.688c0 1.023.506 1.797 1.797 1.797h49.64c51.68 0 85.075-45.698 85.075-85.075V121.832c0-6.774-.777-13.123-2.195-19.054-10.696-44.744-57.841-65.665-82.524-65.665h-48.79c-2.486 0-3.003 1.368-3.003 3.25zm96 218.094c0 17.589-14.473 32.063-32.062 32.063s-32.063-14.474-32.063-32.063c0-17.589 14.474-32.062 32.063-32.062 17.589 0 32.062 14.473 32.062 32.062z" style="fill:${color};fill-rule:nonzero;stroke:#000;stroke-width:8.33px" transform="translate(-307.583 -19.934)"/></svg>`
        }

        const batteryLevel = BATTERY_LEVEL[battery_level]

        return html`
            <li>
                <div class="pure-g">

                    <div class="pure-u-2-24 flex">${joyconSvg}</div>
                    <div class="pure-u-12-24 joycon-info">
                        <div class="flex">
                            <span class="joycon-name">${name}</span>
                            <span class="battery-level ${batteryLevel}">${SVG_BATTERY_LEVEL}</span>
                        </div>
                        <span class="joycon-state">${stateMessage}</span>
                    </div>
                    <div class="pure-u-4-24 flex">
                        ${pairing_code && html`
                            <span class="pairing-code">${pairing_code}</span>
                        `}
                    </div>
                    <div class="pure-u-6-24">
                        ${showButton && joyconState == PairingState.CONNECTED && html`
                            <button type="button" onClick=${this.disconnect} class="pure-button pure-button-error">Disconnect</button>
                        `}
                        ${showButton && joyconState != PairingState.CONNECTED && html`
                            <button type="button" onClick=${this.connect} class="pure-button pure-button-primary">Connect</button>
                        `}
                    </div>
                </div>
            </li>
        `
    }
}

class JoyCons extends Component {
    constructor() {
        super()
        this.state = {
            isRefreshing: false,
        }

        this.refreshJoyconList = this.refreshJoyconList.bind(this)
    }

    refreshJoyconList() {
        this.setState({
            isRefreshing: false,
        })
        window.mitty.emit('req_' + WsCommand.GET_JOYCON_LIST)
    }

    componentDidMount() {
    }

    render(props, state) {
        return html`
            <div class="pure-g">
                <h2 class="pure-u-18-24">Joy-Cons</h2>
                    ${state.isRefreshing && html`
                        <button type="button" disabled class="pure-button btn-refresh pure-u-6-24">Refresh</a>
                    `}
                    ${!state.isRefreshing && html`
                        <button type="button" class="pure-button btn-refresh pure-u-6-24" onClick=${this.refreshJoyconList}>Refresh</button>
                    `}
            </div>
            <div class="joycons-wrapper">
                ${props.joycons.length == 0 && html`
                    <p class="empty">No Joy-Cons found!</p>
                `}


                ${props.joycons.length > 0 && html`
                    <ul class="joycons-list">
                        ${props.joycons.map(item => (
                            html`<${JoyCon} joycon=${item} key=${item.serial} />`
                        ))}
                    </ul>
                `}
            </div>
        `
    }
}

class App extends Component {
    constructor(props) {
        super()

        this.state = {
            pairing_method: window.CONFIG.pairing_method,
            host_ip_addr: window.CONFIG.host_ip_addr,
            console_ip_addr: window.CONFIG.console_ip_addr,
            pairing_code: window.CONFIG.pairing_code,
            joycons: [],
        }

        this.connectWs = this.connectWs.bind(this)
        this.sendRequest = this.sendRequest.bind(this)
        this.requestGetJoyconList = this.requestGetJoyconList.bind(this)
        this.requestConnectJoycon = this.requestConnectJoycon.bind(this)
        this.requestDisconnectJoycon = this.requestDisconnectJoycon.bind(this)
        this.handleMethodChange = this.handleMethodChange.bind(this)
        this.handleAddrChange = this.handleAddrChange.bind(this)
        this.handleCodeChange = this.handleCodeChange.bind(this)

        window.mitty.on('req_' + WsCommand.GET_JOYCON_LIST, this.requestGetJoyconList)
        window.mitty.on('req_' + WsCommand.CONNECT_JOYCON, this.requestConnectJoycon)
        window.mitty.on('req_' + WsCommand.DISCONNECT_JOYCON, this.requestDisconnectJoycon)
        window.mitty.on('update_method', this.handleMethodChange)
        window.mitty.on('update_addr', this.handleAddrChange)
        window.mitty.on('update_code', this.handleCodeChange)
    }

    sendRequest(cmd, data) {
        if (!data) {
            data = {}
        }
        const msg = {
            cmd: cmd,
            data: data,
        }
        console.log('send', msg)
        this.socket.send(JSON.stringify(msg))
    }

    requestGetJoyconList() {
        this.sendRequest(WsCommand.GET_JOYCON_LIST);
    }

    requestConnectJoycon(serial) {
        const state = this.state
        const pairing_method = state.pairing_method
        let addr = pairing_method == PairingMethod.DEFAULT ? state.host_ip_addr : state.console_ip_addr
        if (!addr.match(/^192\.168\.((\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.)(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])$/)) {
            alert('ERROR: Invalid IP address!')
            document.getElementById('ipAddr').focus()
            return
        }

        if (pairing_method == PairingMethod.DEFAULT) {
            const pairing_code = state.pairing_code
            if (!pairing_code.match(/^\d{6}$/)) {
                alert('ERROR: Invalid pairing code!')
                document.getElementById('pairingCode').focus()
                return
            }
        }

        this.sendRequest(WsCommand.CONNECT_JOYCON, {
            pairing_method: state.pairing_method,
            host_ip_addr: state.host_ip_addr,
            console_ip_addr: state.console_ip_addr,
            pairing_code: state.pairing_code,
            joycon_serial: serial,
        })
    }

    requestDisconnectJoycon(serial) {
        this.sendRequest(WsCommand.DISCONNECT_JOYCON, {
            joycon_serial: serial,
        })
    }

    connectWs() {
        const that = this
        this.socket = new WebSocket('ws://' + window.location.host + '/ws')

        this.socket.onopen = function(e) {
            console.log('[open] Connection established')
            that.requestGetJoyconList()
        }

        this.socket.onmessage = function(event) {
            const msg = JSON.parse(event.data)
            console.log(msg)
            const cmd = msg['cmd']
            const shortCmd = msg['cmd'].slice(5)  // Remove "resp_" prefix

            switch (shortCmd) {
                case WsCommand.GET_JOYCON_LIST:
                    that.setState({
                        joycons: msg['data'],
                    })
                    break

                default:
                    window.mitty.emit(cmd, msg['data'])
            }
        }

        this.socket.onclose = function(event) {
            if (event.wasClean) {
                console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
            } else {
                console.log('[close] Connection died');
            }
        }

        this.socket.onerror = function(error) {
            console.log(`[error] ${error.message}`);
        }
    }

    handleMethodChange(pairing_method) {
        this.setState({
            pairing_method: pairing_method,
        })
    }

    handleAddrChange(addr) {
        const key = this.state.pairing_method == PairingMethod.DEFAULT ? 'host_ip_addr' : 'console_ip_addr'
        this.setState({
            [key]: addr,
        })
    }

    handleCodeChange(pairing_code) {
        this.setState({
            pairing_code: pairing_code,
        })
    }

    componentDidMount() {
        this.connectWs()
    }

    render(props, state) {
        return html`
            <div class="container">
                <div class="ascii">
                    <pre>     ░░  ░░░░░░  ░░    ░░ ░░░░░░   ░░░░░  ░░░    ░░  ░░░░░░ ░░░░░░░
     ▒▒ ▒▒    ▒▒  ▒▒  ▒▒  ▒▒   ▒▒ ▒▒   ▒▒ ▒▒▒▒   ▒▒ ▒▒      ▒▒
     ▒▒ ▒▒    ▒▒   ▒▒▒▒   ▒▒   ▒▒ ▒▒▒▒▒▒▒ ▒▒ ▒▒  ▒▒ ▒▒      ▒▒▒▒▒
▓▓   ▓▓ ▓▓    ▓▓    ▓▓    ▓▓   ▓▓ ▓▓   ▓▓ ▓▓  ▓▓ ▓▓ ▓▓      ▓▓
 █████   ██████     ██    ██████  ██   ██ ██   ████  ██████ ███████
                    </pre>
                </div>

                <form class="pure-form pure-form-stacked">
                    <fieldset>
                        <div class="pure-g">
                            <h2 class="pure-u-1">Config</h2>
                            <div class="pure-u-1">
                                <${PairingMethodPicker} pairing_method=${state.pairing_method}/>
                            </div>
                            <div class="pure-u-1-2">
                                <${PrivateIpAddress} pairing_method=${state.pairing_method} host_ip_addr=${state.host_ip_addr} console_ip_addr=${state.console_ip_addr} />
                            </div>
                            <div class="pure-u-1-2">
                                <${PairingCode} pairing_method=${state.pairing_method} pairing_code=${state.pairing_code} />
                            </div>
                        </div>
                    </fieldset>
                </form>

                <div class="pure-u-1 joycons">
                    <${JoyCons} pairing_method=${state.pairing_method} joycons=${state.joycons} />
                </div>
            </div>
            <div class="footer">
                <a href="https://github.com/redphx/joydance" target="_blank">${window.VERSION}</a>
            </div>
        `
    }
}

render(html`<${App} />`, document.body)
