# JoyDance

![image](https://user-images.githubusercontent.com/96280/163298419-6279f338-069e-4302-971f-b9d2e5fc9f7a.png)

## Demo
https://youtu.be/f_1IkUHFdH8

## Features
- Play Just Dance 2016 and later on all platforms with Joy-Cons.
- Playing with a Joy-Con (+ its strap) is safer and more comfortable than holding a phone.
- No latency.
- Better score than using a phone (hopefully).
- No random disconnection.
- Support up to 6 players.
- Support all platforms (in theory):

|              | Xbox Series | Xbox One | PS4/5 | NSW | Stadia | PC | Wii U |
|--------------|:-----------:|:--------:|:-----:|:---:|:------:|:--:|:-----:|
| 2020-2022    | ✅          | ❓       | ❓    | ✅  | [#2](../../issues/2) |    |    |
| 2016-2019 ⚠️ |             | ❓       | ❓    | ✅  |                      | ✅ | ✅ |

✅ = confirmed working  
❓ = not tested, but expected to work  
⚠️ **Important**: Can't use buttons on Joy-Con to navigate the UI in JD 2016-2019 (you'll have to use controllers/keyboard). [#6](../../issues/6).

  
## How does it work?
It pretends to be the [Just Dance Controller app](https://play.google.com/store/apps/details?id=com.ubisoft.dance.justdance2015companion), sends movements of the Joy-Con to your game console.

## Tested on
- MacOS Catalina 10.15 with [TP-Link Bluetooth 4.0 Nano USB Adapter UB400](https://www.tp-link.com/us/home-networking/usb-adapter/ub400/).
- Raspberry Pi Zero 2 W (Bulleye, kernel 5.15) with [MPOW BH519A Bluetooth 5.1 USB Adapter](https://www.xmpow.com/products/mpow-bh519a-bluetooth-5-1-usb-adapter-for-pc). Tested with 2 Joy-Cons and it worked just fine.
  

## Requirements
- PC/Mac/Linux with bluetooth support.
- [Python 3.7+](https://www.python.org) and [pip](https://pip.pypa.io/en/stable/installation/) installed.
- 1 to 6 Joy-Cons.
- It's **RECOMMENDED** to:
  - Use a Bluetooth dongle, because built-in Bluetooth sucks (or you will get disconnected constantly while playing). Make sure you buy a dongle with game controllers support, not just for audio devices. Not all dongles support Mac/Linux, so remember to check compatibility before buying.
  - Use a Nintendo Switch to update Joy-Con to the latest firmware & calibate its motion sensors. Ask your friends or bring it to the game shop if you don't have one.

## Installation

1. Download [the latest version](https://github.com/redphx/joydance/releases/latest/) and extract it into a folder.
2. Open that folder in Terminal/Command Prompt, then run this command:
```
pip3 install -r requirements.txt
```

#### Extra step for Windows users
Please make [this change](../../issues/3#issuecomment-1101087415). It's only a temporary fix, and will be patched in future versions.
  
#### Extra steps for Linux users
<details>
  <summary>Click to expand!</summary>

  1. Linux users may need to use [`hid`](https://github.com/apmorton/pyhidapi) instead of [`hidapi`](https://github.com/trezor/cython-hidapi) (not sure why `hidapi` couldn't find Joy-Cons on Linux).
  ```
  pip3 uninstall hidapi

  sudo apt install libhidapi-dev
  pip3 install hid
  ```

  2. Create a new udev rule file at `/etc/udev/rules.d/50-nintendo-switch.rules` ([Source](https://www.reddit.com/r/Stadia/comments/egcvpq/using_nintendo_switch_pro_controller_on_linux/fc5s7qm/))
  ```
  # Switch Joy-con (L) (Bluetooth only)
  KERNEL=="hidraw*", SUBSYSTEM=="hidraw", KERNELS=="0005:057E:2006.*", MODE="0666"

  # Switch Joy-con (R) (Bluetooth only)
  KERNEL=="hidraw*", SUBSYSTEM=="hidraw", KERNELS=="0005:057E:2007.*", MODE="0666"

  # Switch Pro controller (USB and Bluetooth)
  KERNEL=="hidraw*", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="057e", ATTRS{idProduct}=="2009", MODE="0666"
  KERNEL=="hidraw*", SUBSYSTEM=="hidraw", KERNELS=="0005:057E:2009.*", MODE="0666"

  # Switch Joy-con charging grip (USB only)
  KERNEL=="hidraw*", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="057e", ATTRS{idProduct}=="200e", MODE="0666"
  ```

  Reload udev rules:
  ```
  sudo udevadm control --reload-rules
  sudo udevadm trigger
  ```

  3. Install [`dkms-hid-nintendo`](https://github.com/nicman23/dkms-hid-nintendo) (Joy-Con driver) if you're running Linux kernel older than 5.16.
</details>

## Usage

1. Open the phone pairing screen on Just Dance.

2. Connect your PC/Mac/Linux to the same Wi-Fi or LAN network as your game console.

3. Run this command:
  ```
  python3 dance.py
  ```

4. Open http://localhost:32623 (not https://...) in a web browser (32623 = DANCE). You can also open JoyDance on another device (connected to the same network) with this link: `http://[JOYDANCE_DEVICE_IP]:32623` (for example: `http://192.168.1.100:32623`).

5. Turn on Bluetooth and pair with Joy-Con by holding down the [SYNC button](https://en-americas-support.nintendo.com/app/answers/detail/a_id/22634) until the light move up and down. Press the "Refresh" button until your Joy-Con shows up.

6. Fill the form.

    - **Pairing Method**:
      - Fast:
        - Only for Xbox One, PlayStation 4/5 and Nintendo Switch.
        - Connect instantly.
        - Doesn't require pairing code.
        - Requires console's private IP address.
      - Default:
        - Slower, but supports all platforms (including Xbox Series and Stadia).
        - Requires pairing code.
        - Requires host's private IP address.
      - Old:
        - For JD 2016-2019 only (including Wii U, PC).
        - Connect instantly.
        - Doesn't require pairing code.
        - Requires PC/console's private IP address.
        - ⚠️ **Important**: Can't use buttons on Joy-Con to navigate the UI (you'll have to use controllers/keyboard).

    - **Host's Private IP Address**:
      - The private IP address of your PC/Mac/Linux. Find this in the Wi-Fi settings.
      - Starts with `192.168`.
    - **Console's Private IP Address**:
      - The private IP address of your console. Find this in the Wi-Fi settings on console.
      - Starts with `192.168`.
    - **Pairing Code**: get this from the game.

7. Press the "Connect" button next to Joy-Con to start the pairing process.

8. 💃🕺

## FAQ
1. **What is the correct way to hold a Joy-Con?**  
  Hold the Joy-Con (L)/(R) in your right hand, with your palm touching the back of Joy-Con.
  
2. **How to control with Joy-Con (L)?**
    - Up = X
    - Right = A
    - Down = B
    - Left = Y
    - L = R
    - ZL = ZR
    - Minus = Plus

3. **How to exit JoyDance?**  
  Press `Ctrl + C` two times or close the Terminal window.

4. **Is it possible to port JoyDance to wearable devices like smart watches (Wear OS, watchOS...)?**  
  Yes. I tested on a tiny [M5StickC Plus](https://shop.m5stack.com/collections/stick-series/products/m5stickc-plus-esp32-pico-mini-iot-development-kit) and it worked! But remember, some movements require you to move only the palm of your hand won't be recognized correctly.

5. **Can I play Just Dance 2017 (PC) and run JoyDance on the same PC?**  
  Yes, you can.

## Acknowledgements
-  [dekuNukem/Nintendo_Switch_Reverse_Engineering](https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering)
-  [tocoteron/joycon-python](https://github.com/tocoteron/joycon-python)
-  [Davidobot/BetterJoy](https://github.com/Davidobot/BetterJoy)
