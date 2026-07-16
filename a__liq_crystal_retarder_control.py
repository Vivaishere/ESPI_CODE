import os
import time
import tkinter as tk

# Try importing serial for real device support
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

LOG_FILE = "retarder_log.txt"


# ==========================================================
# Logging
# ==========================================================
def log_message(message):
    """Log messages to console and file."""
    print(message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")


# ==========================================================
# Real + Mock Serial Communication Functions
# ==========================================================
def send_cmd(ser, cmd):
    """Send a command to LC device or mock response."""
    if ser is None:
        log_message(f"[MOCK] Sent: {cmd} | Response: OK (mock)")
        return f"MOCK: {cmd} → OK"

    try:
        ser.write((cmd + "\r").encode("ascii"))
        time.sleep(0.1)
        response = ser.read_all().decode("ascii", errors="ignore").strip()
        log_message(f"Sent: {cmd} | Response: {response}")
        return response or "OK"
    except Exception as e:
        log_message(f"[ERROR] send_cmd failed: {e}")
        return ""


def verify_connection(ser):
    """Check if LC device responds to *idn? command."""
    if ser is None:
        log_message("[MOCK] verify_connection → False (no serial)")
        return False

    try:
        ser.write(b"\x05")
        response = send_cmd(ser, "*idn?")
        if "LCC2415" in response:
            log_message(f"[OK] Connected to device: {response}")
            return True
        else:
            log_message(f"[WARN] Could not verify LC connection. Response: {response}")
            return False
    except Exception as e:
        log_message(f"[ERROR] verify_connection failed: {e}")
        return False


def find_device_port():
    """Detect serial port of LCC2415 device. Returns None if not found."""
    if not SERIAL_AVAILABLE:
        log_message("[MOCK] pyserial not available — LC will run in mock mode.")
        return None

    available_ports = list(serial.tools.list_ports.comports())
    if not available_ports:
        log_message("[WARN] No serial ports detected.")
        return None

    for port in available_ports:
        log_message(f"Trying port: {port.device}")
        try:
            ser = serial.Serial(
                port=port.device,
                baudrate=115200,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=0.5
            )
            if verify_connection(ser):
                log_message(f"[OK] LC Retarder found at {port.device}")
                return ser
            ser.close()
        except Exception as e:
            log_message(f"[ERROR] Failed to open {port.device}: {e}")
            continue

    log_message("[ERROR] No LCC2415 device found on any serial port.")
    return None


# ==========================================================
# Retardance Control GUI (Optional)
# ==========================================================
class RetardanceGUI:
    """Small standalone GUI for manual retardance control."""
    def __init__(self, root, ser):
        self.root = root
        self.ser = ser
        self.current_val = None

        root.title("LCC2415 Retardance Control")

        self.retardance_values = [0, int(0.25 * 633), int(0.5 * 633), int(0.75 * 633)]

        self.buttons = {}
        for i, val in enumerate(self.retardance_values):
            btn = tk.Button(root, text=f"{val} nm", width=12,
                            command=lambda v=val: self.set_retardance(v))
            btn.grid(row=0, column=i, padx=5, pady=5)
            self.buttons[val] = btn

        self.status_label = tk.Label(root, text="Current Retardance: Unknown", font=("Arial", 12))
        self.status_label.grid(row=1, column=0, columnspan=4, pady=10)

        self.exit_button = tk.Button(root, text="Exit", width=15, command=root.destroy)
        self.exit_button.grid(row=2, column=1, columnspan=2, pady=10)

        # Force to retardance = 0 nm at startup
        send_cmd(self.ser, "RE=0")
        self.query_retardance()

    def set_retardance(self, value):
        send_cmd(self.ser, f"RE={value}")
        self.query_retardance()

    def query_retardance(self):
        response = send_cmd(self.ser, "RE?")
        log_message(f"Now at: {response}")

        response = response.replace(">", "").strip()
        if "RE=" in response:
            try:
                nm_value = int(response.split("=")[1])
                self.status_label.config(text=f"Current Retardance: {nm_value} nm")
                self.current_val = nm_value
            except ValueError:
                self.status_label.config(text="Current Retardance: Unknown")
        else:
            self.status_label.config(text="Current Retardance: Unknown")

        self.highlight_current()

    def highlight_current(self):
        for val, btn in self.buttons.items():
            if val == self.current_val:
                btn.config(bg="lightgreen")
            else:
                btn.config(bg="SystemButtonFace")


# ==========================================================
# Standalone Test GUI Launcher
# ==========================================================
def main():
    # Clear previous log file
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    log_message("=== LCC2415 Retarder Control Started ===")
    ser = find_device_port()
    if ser is None:
        log_message("[MOCK] Running LC GUI in mock mode (no serial device).")

    # Initialize device to retardance mode
    send_cmd(ser, "OM=1")
    send_cmd(ser, "WL=635")

    root = tk.Tk()
    app = RetardanceGUI(root, ser)
    root.mainloop()

    try:
        if ser:
            ser.close()
    except Exception:
        pass

    log_message("[OK] Program closed by user")


if __name__ == "__main__":
    main()
