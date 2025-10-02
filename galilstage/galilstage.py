import serial
import time
import toml

class GalilStage:
    def __init__(self, config_file, port='/dev/ttyUSB0', baudrate=9600, timeout=1):
        """Initialize GalilStage with config file and comm settings."""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

        # Load galil config immediately
        full_config = toml.load(config_file)
        if 'galil' not in full_config:
            raise ValueError(f"[galil] section not found in {config_file}")
        self.config = full_config['galil']
        print(f"Loaded config from {config_file}")

    def connect(self):
        """Open serial connection."""
        if self.ser and self.ser.is_open:
            print("Already connected.")
            return
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        print(f"Connected to Galil on {self.port}")

    def disconnect(self):
        """Close serial connection."""
        if self.ser:
            self.ser.close()
            print("Disconnected.")
            self.ser = None

    def send_command(self, cmd, wait=0.05):
        """Send command string to Galil and return response."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Not connected to Galil")
        self.ser.write((cmd.strip() + '\r').encode())
        time.sleep(wait)
        resp = self.ser.read(1000).decode(errors='ignore').strip()
        return resp

    def command_config(self):
        """Send all relevant Galil config commands from loaded TOML."""
        # 1. Global confcomm
        confcomm = self.config.get('confcomm', "").strip()
        if confcomm:
            print(f"Sending confcomm: {confcomm}")
            self.send_command(confcomm)

        print('in command_config method, sleeping for 2 sec')
        time.sleep(2)

        # 2. Per-axis init commands
        for axis in ['A', 'B', 'C', 'D']:
            self.initialize_axis(axis)
            print(f"Initialized axis {axis}, sleeping for 2 secs...")
            time.sleep(2)

        # 3. Optional maxspeed
        if 'maxspeed' in self.config:
            maxspeed = self.config['maxspeed']
            comm = ''
            for a in self.config.get('linaxis', '').split():
                comm += f"SP{a}={maxspeed};"
            for a in self.config.get('angaxis', '').split():
                comm += f"SP{a}={maxspeed};"
            if comm:
                print(f"Setting maxspeed: {comm}")
                self.send_command(comm[:-1])

        print("Config commands sent.")
        return True

    def initialize_axis(self, axis, volts=3):
        """Use BZ command to initialize axis."""
        cmd = f"BZ{axis}={volts}"
        return self.send_command(cmd)


    def send_command(self, cmd):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Not connected.")
        self.ser.write((cmd.strip() + '\r').encode())
        resp = self.ser.read(1000).decode().strip()
        return resp

    # ---- Convenience wrappers ----
    def move_absolute(self, axis, pos):
        """Move an axis to an absolute position (pos in encoder counts or units)."""
        cmd = f"PA {axis}={pos};BG {axis}"
        return self.send_command(cmd)

    def move_relative(self, axis, delta):
        """Move an axis by delta relative units."""
        cmd = f"PR {axis}={delta};BG {axis}"
        return self.send_command(cmd)

    def home_axis(self, axis):
        """Home an axis."""
        cmd = f"HM {axis}"
        return self.send_command(cmd)

    def stop(self, axis=None):
        """Stop motion. If axis is None, stop all."""
        cmd = "ST" if axis is None else f"ST {axis}"
        return self.send_command(cmd)

    def get_position(self, axis):
        """Query position of an axis."""
        cmd = f"TP {axis}"
        return self.send_command(cmd)

    def enable_axis(self, axis):
        """Enable servo for an axis (e.g. A, B, C, D)."""
        return self.send_command(f"SH{axis}")

    def disable_axis(self, axis):
        """Motor off for an axis."""
        return self.send_command(f"MO{axis}")

    def set_gearing(self, lead, follow):
        """Set gearing: lead axis drives follow axis."""
        return self.send_command(f"GA {lead},{follow}")

    def set_gearing_ratio(self, *ratios):
        """Set gearing ratios, e.g. GR -1,1 for axes B and D."""
        args = ",".join(str(r) for r in ratios)
        return self.send_command(f"GR {args}")

    def jog_axis(self, axis, speed):
        """Set jog speed for axis and begin jogging."""
        cmd = f"JG{axis}={speed}")
        return self.send_command(cmd)

    def query_status(self, code):
        """Send MG query, e.g. query_status('_MOA')."""
        return self.send_command(f"MG {code}")

    def change_gain(self, axis, gain):
        """Change gain of axis."""
        cmd = f"AG{axis}={gain}"
        return self.send_command(cmd)

    def query_param(self, code):
        """Send a generic MG query and return the value."""
        return self.send_command(f"MG {code}")

    def disable_limit_switch(self, axis):
        """Disable limit switch detection on a given axis (LDx=3)."""
        cmd = f"LD{axis}=3"
        return self.send_command(cmd)

    def flip_limitswitch_polarity(self, pol=1):
        """CN -1 means active low, CN +1 is active high. And we want active high"""
        cmd = f"CN {pol}"
        return self.send_command(cmd)
    
    def command_rawsignal(self, command=None, axis=None, value=None):
        "for just getting some commands with raw functions"
        if axis is not None:
            cmd = f'{command}{axis}'
        if axis is not None and value is not None:
            cmd =  f'{command}{axis} = {value}'
        elif command and value:
            cmd = f'{command} = {value}'
        else:
            cmd = f'{command}'
        return self.send_command(cmd)
    
    def begin_axis_motion(self, axis):
        """Set jog speed for axis and begin jogging."""
        cmd = f"BG{axis}"
        return self.send_command(cmd)
