import serial
import time
import toml

class GalilStage:
    def __init__(self, config, port='/dev/ttyUSB0', baudrate=115200, timeout=3):
        """Initialize GalilStage object (no connection yet)."""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.config = config
        self.ser = None

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

    def command(self, command):
        """ Marc: Function to send commands and returns response.
            Uses write and read, checks if comm is open.
        """
        # If no connection
        if self.port is None:
            return "Unable to send command, no open connection"
        # Long command - split it
        comsplit = command.split(';')
        if len(comsplit) > 3:
            retmsg = self.command(';'.join(comsplit[:3]))
            time.sleep(3*float(self.config['galil']['waittime']))
            retmsg += self.command(';'.join(comsplit[1:]))
            return retmsg
        # Send the command
        self.write((command+'\n\r'), verbose = bool(self.config['galil']['verbose']))
        time.sleep(float(self.config['galil']['waittime']))
        retmsg = self.read()
        if self.config['galil']['verbose']:
            self.log.debug('Read: %s' % retmsg)
        return retmsg

    def setvalue(self, section, key, value):
        """ Marc: Sets the [section] key = value converting to correct type

            Returns a string which is empty unless there's an error.
            HELPS UPDATE THE CONFIG FILE IN A TYPE-SAFE WAY
            FOR OCS, NOT PREFERRED
        """
        booltrue = ['t', 'true', 'yes', 'on', '1']
        boolfalse = ['f', 'false', 'no', 'off', '0']
        valorig = self.config[section][key]
        retmsg = ''
        if isinstance(valorig, bool):
            if value.lower() in booltrue:
                self.config[section][key] = True
            elif value.lower() in boolfalse:
                self.config[section][key] = False
            else:
                retmsg = f'"{value}" is invalid for type bool'
        else:
            try:
                self.config[section][key] = type(valorig)(value)
            except:
                retmsg = f'"{value}" is invalid type for {type(valorig).__name__}'
        return retmsg


    def load_config(self, path="labconfig.toml"):
        """Load galil config from TOML and send startup commands."""
        self.config = toml.load(path)
        galil_cfg = self.config.get('galil', {})
        print(f"Loaded config from {path}")

        # 1. Send global confcomm string (if defined)
        confcomm = galil_cfg.get('confcomm', "").strip()
        if confcomm:
            print(f"Sending confcomm: {confcomm}")
            self.send_command(confcomm)

        # 2. Send per-axis init commands
        for axis in ['A', 'B', 'C', 'D']:
            key = f'initcomm{axis}'
            if key in galil_cfg and galil_cfg[key].strip():
                cmd = galil_cfg[key].strip()
                print(f"Initializing axis {axis} with: {cmd}")
                self.send_command(cmd)

        # 3. (Optional) apply brakes / maxspeed / other params
        if 'maxspeed' in galil_cfg:
            print(f"Configured maxspeed = {galil_cfg['maxspeed']} (not directly sent)")

        return True

    def initialize_axis(self, axis, volts=3):
        """Send initcomm strings from config for each axis (A–D)."""
        if not hasattr(self, 'config'):
            raise RuntimeError("Config not loaded. Run load_config() first.")
        cmd = f"BZ{axis} = {volts}"
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
        self.send_command(f"JG{axis}={speed}")
        return self.send_command(f"BG{axis}")

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

    def command_config(self):
        """Send all relevant Galil config commands from loaded TOML."""
        if not hasattr(self, 'config') or 'galil' not in self.config:
            raise RuntimeError("No Galil config loaded. Run load_config() first.")
        galil_cfg = self.config['galil']

        # 1. Global confcomm
        confcomm = galil_cfg.get('confcomm', "").strip()
        if confcomm:
            print(f"Sending confcomm: {confcomm}")
            self.send_command(confcomm)

        # 2. Per-axis init commands
        for axis in ['A', 'B', 'C', 'D']:
            key = f'initcomm{axis}'
            if key in galil_cfg and galil_cfg[key].strip():
                cmd = galil_cfg[key].strip()
                print(f"Initializing axis {axis} with: {cmd}")
                self.send_command(cmd)

        # 3. Index command (if defined)
        if 'indexcomm' in galil_cfg and galil_cfg['indexcomm'].strip():
            print(f"Indexing: {galil_cfg['indexcomm']}")
            self.send_command(galil_cfg['indexcomm'])

        # 4. Speed (if defined)
        if 'maxspeed' in galil_cfg:
            maxspeed = galil_cfg['maxspeed']
            comm = ''
            for a in galil_cfg.get('linaxis', '').split():
                comm += f"SP{a}={maxspeed};"
            for a in galil_cfg.get('angaxis', '').split():
                comm += f"SP{a}={maxspeed};"
            if comm:
                print(f"Setting maxspeed: {comm}")
                self.send_command(comm[:-1])

        print("Config commands sent.")
        return True

