# JoyDance

![image](https://user-images.githubusercontent.com/96280/163298419-6279f338-069e-4302-971f-b9d2e5fc9f7a.png)

# How does it work?
It pretends to be the [Just Dance Controller app](https://play.google.com/store/apps/details?id=com.ubisoft.dance.justdance2015companion), sends movements of the Joy-Con to your game console.

# Features
- Play Just Dance 2017 and later on Xbox/Stadia/PS/NSW with Joy-Cons.
- Playing with a Joy-Con (+ its strap) is safer and more comfortable than holding a phone.
- No latency.
- Better score than using a phone.
- No random disconnection.
- Support up to 6 players.
- Support all platforms (in theory):
  - Xbox Series X/S
  - Nintendo Switch
  - Xbox One (not tested)
  - Stadia (not tested)
  - Playstation 4/5 (not tested)

# Tested on
- JD 2022 on Xbox Series X and JD 2020 on Nintendo Switch.
- MacOS Catalina 10.15 with [TP-Link Bluetooth 4.0 Nano USB Adapter UB400](https://www.tp-link.com/us/home-networking/usb-adapter/ub400/).
- Raspberry Pi Zero 2 W with [MPOW BH519A Bluetooth 5.1 USB Adapter](https://www.xmpow.com/products/mpow-bh519a-bluetooth-5-1-usb-adapter-for-pc).
  
Tested on Zero 2 W with 2 Joy-Cons and it worked just fine.

# Requirements
- PC/Mac/Linux with bluetooth support.
- [Python 3.7+](https://www.python.org) and [pip](https://pip.pypa.io/en/stable/installation/) installed.
- 1 to 6 Joy-Cons.
- It's **RECOMMENDED** to:
  - Use a Bluetooth dongle, because built-in Bluetooth sucks (it will disconnect constantly while playing). Make sure you buy a dongle with game controllers support, not just for audio devices. Not all dongles support Mac/Linux, so remember to check compatibility before buying.
  - Use a Nintendo Switch to update Joy-Con to the latest firmware & calibate its motion sensors. Ask your friends or bring it to the game shop if you don't have one.

# Installation

1. Download the latest version and extract it into a folder.
2. Open that folder in Terminal/Command Prompt, then run this command:
```
pip3 install -r requirements.txt
```
### Extra steps for Linux users

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

# Usage
...
