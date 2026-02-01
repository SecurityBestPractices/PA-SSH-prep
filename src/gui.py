"""tkinter GUI components for PA-SSH-prep."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from dataclasses import dataclass

from src.network_detect import NetworkSettings, detect_network_settings
from src.utils import validate_ip_address, validate_password, validate_panos_version


@dataclass
class SetupConfig:
    """Configuration collected from the GUI."""
    new_ip: str
    new_password: str
    target_version: str
    subnet_mask: str
    gateway: str
    dns_servers: list[str]


class PASSHPrepGUI:
    """Main GUI window for PA-SSH-prep application."""

    def __init__(self, on_start: Optional[Callable[[SetupConfig], None]] = None):
        """
        Initialize the GUI.

        Args:
            on_start: Callback when OK button is clicked with SetupConfig
        """
        self.on_start = on_start
        self.root: Optional[tk.Tk] = None
        self.running = False
        self.cancelled = False

        # GUI variables
        self.new_ip_var: Optional[tk.StringVar] = None
        self.password_var: Optional[tk.StringVar] = None
        self.version_var: Optional[tk.StringVar] = None
        self.subnet_var: Optional[tk.StringVar] = None
        self.gateway_var: Optional[tk.StringVar] = None
        self.dns1_var: Optional[tk.StringVar] = None
        self.dns2_var: Optional[tk.StringVar] = None
        self.status_var: Optional[tk.StringVar] = None
        self.progress_var: Optional[tk.DoubleVar] = None

        # Widgets
        self.ok_button: Optional[ttk.Button] = None
        self.cancel_button: Optional[ttk.Button] = None
        self.progress_bar: Optional[ttk.Progressbar] = None

    def create_window(self) -> tk.Tk:
        """Create and configure the main window."""
        self.root = tk.Tk()
        self.root.title("PA-SSH-prep - Firewall Initial Setup")
        self.root.geometry("450x400")
        self.root.resizable(False, False)

        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

        # Initialize variables
        self.new_ip_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.version_var = tk.StringVar()
        self.subnet_var = tk.StringVar(value="255.255.255.0")
        self.gateway_var = tk.StringVar(value="192.168.1.254")
        self.dns1_var = tk.StringVar(value="8.8.8.8")
        self.dns2_var = tk.StringVar(value="8.8.4.4")
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        self._create_widgets()
        self._detect_network()

        return self.root

    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        if not self.root:
            return

        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        row = 0

        # New Firewall IP
        ttk.Label(main_frame, text="New Firewall IP:").grid(
            row=row, column=0, sticky="w", pady=(0, 5)
        )
        ip_entry = ttk.Entry(main_frame, textvariable=self.new_ip_var, width=30)
        ip_entry.grid(row=row, column=1, sticky="w", pady=(0, 5))
        ip_entry.focus()
        row += 1

        # New Admin Password
        ttk.Label(main_frame, text="New Admin Password:").grid(
            row=row, column=0, sticky="w", pady=(0, 5)
        )
        ttk.Entry(main_frame, textvariable=self.password_var, width=30, show="*").grid(
            row=row, column=1, sticky="w", pady=(0, 5)
        )
        row += 1

        # Target PAN-OS Version
        ttk.Label(main_frame, text="Target PAN-OS Version:").grid(
            row=row, column=0, sticky="w", pady=(0, 5)
        )
        version_frame = ttk.Frame(main_frame)
        version_frame.grid(row=row, column=1, sticky="w", pady=(0, 5))
        ttk.Entry(version_frame, textvariable=self.version_var, width=20).pack(side="left")
        ttk.Label(version_frame, text="(e.g., 11.2.4 or 11.2.10-h2)", font=("", 8)).pack(side="left", padx=5)
        row += 1

        # Separator
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=5
        )
        row += 1

        # Detected Network Settings label
        ttk.Label(main_frame, text="Detected Network Settings:", font=("", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(5, 5)
        )
        row += 1

        # Subnet Mask
        ttk.Label(main_frame, text="  Subnet Mask:").grid(
            row=row, column=0, sticky="w"
        )
        ttk.Entry(main_frame, textvariable=self.subnet_var, width=20).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # Gateway
        ttk.Label(main_frame, text="  Gateway:").grid(
            row=row, column=0, sticky="w"
        )
        ttk.Entry(main_frame, textvariable=self.gateway_var, width=20).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # DNS 1
        ttk.Label(main_frame, text="  DNS 1:").grid(
            row=row, column=0, sticky="w"
        )
        ttk.Entry(main_frame, textvariable=self.dns1_var, width=20).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # DNS 2
        ttk.Label(main_frame, text="  DNS 2:").grid(
            row=row, column=0, sticky="w"
        )
        ttk.Entry(main_frame, textvariable=self.dns2_var, width=20).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        # Spacer
        ttk.Frame(main_frame, height=15).grid(row=row, column=0, columnspan=2)
        row += 1

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        self.ok_button = ttk.Button(
            button_frame, text="OK", command=self._on_ok, width=12
        )
        self.ok_button.pack(side="left", padx=5)

        self.cancel_button = ttk.Button(
            button_frame, text="Cancel", command=self._on_cancel, width=12
        )
        self.cancel_button.pack(side="left", padx=5)
        row += 1

        # Separator
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=5
        )
        row += 1

        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        ttk.Label(status_frame, text="Status:").pack(side="left")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left", padx=5)
        row += 1

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            mode="determinate",
            length=400
        )
        self.progress_bar.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(5, 0))

    def _detect_network(self) -> None:
        """Detect and populate network settings."""
        settings = detect_network_settings()
        if settings:
            self.subnet_var.set(settings.subnet_mask)
            self.gateway_var.set(settings.gateway)
            if len(settings.dns_servers) >= 1:
                self.dns1_var.set(settings.dns_servers[0])
            if len(settings.dns_servers) >= 2:
                self.dns2_var.set(settings.dns_servers[1])

    def _validate_inputs(self) -> Optional[str]:
        """
        Validate all input fields.

        Returns:
            Error message or None if valid
        """
        # Validate IP
        new_ip = self.new_ip_var.get().strip()
        if not new_ip:
            return "New Firewall IP is required"
        if not validate_ip_address(new_ip):
            return "Invalid IP address format"

        # Validate password
        password = self.password_var.get()
        if not password:
            return "Admin password is required"
        valid, msg = validate_password(password)
        if not valid:
            return msg

        # Validate version
        version = self.version_var.get().strip()
        if not version:
            return "Target PAN-OS version is required"
        valid, msg = validate_panos_version(version)
        if not valid:
            return msg

        # Validate subnet
        subnet = self.subnet_var.get().strip()
        if not validate_ip_address(subnet):
            return "Invalid subnet mask format"

        # Validate gateway
        gateway = self.gateway_var.get().strip()
        if not validate_ip_address(gateway):
            return "Invalid gateway format"

        # Validate DNS
        dns1 = self.dns1_var.get().strip()
        if dns1 and not validate_ip_address(dns1):
            return "Invalid DNS 1 format"

        dns2 = self.dns2_var.get().strip()
        if dns2 and not validate_ip_address(dns2):
            return "Invalid DNS 2 format"

        return None

    def _on_ok(self) -> None:
        """Handle OK button click."""
        if self.running:
            return

        # Validate inputs
        error = self._validate_inputs()
        if error:
            messagebox.showerror("Validation Error", error)
            return

        # Build config
        dns_servers = []
        if self.dns1_var.get().strip():
            dns_servers.append(self.dns1_var.get().strip())
        if self.dns2_var.get().strip():
            dns_servers.append(self.dns2_var.get().strip())

        config = SetupConfig(
            new_ip=self.new_ip_var.get().strip(),
            new_password=self.password_var.get(),
            target_version=self.version_var.get().strip(),
            subnet_mask=self.subnet_var.get().strip(),
            gateway=self.gateway_var.get().strip(),
            dns_servers=dns_servers
        )

        # Confirm action
        msg = (
            f"This will configure the firewall with:\n\n"
            f"  IP: {config.new_ip}\n"
            f"  Subnet: {config.subnet_mask}\n"
            f"  Gateway: {config.gateway}\n"
            f"  DNS: {', '.join(config.dns_servers)}\n"
            f"  Target PAN-OS: {config.target_version}\n\n"
            f"The firewall will be rebooted multiple times.\n"
            f"Continue?"
        )

        if not messagebox.askyesno("Confirm Setup", msg):
            return

        # Start the process
        self.running = True
        self._disable_inputs()

        if self.on_start:
            self.on_start(config)

    def _on_cancel(self) -> None:
        """Handle Cancel button click."""
        if self.running:
            if messagebox.askyesno("Cancel", "Setup is in progress. Are you sure you want to cancel?"):
                self.cancelled = True
                self.update_status("Cancelling...")
        else:
            self.root.quit()

    def _disable_inputs(self) -> None:
        """Disable input fields during operation."""
        for child in self.root.winfo_children():
            self._disable_widget(child)

        # Keep cancel button enabled
        if self.cancel_button:
            self.cancel_button.configure(state="normal")

    def _disable_widget(self, widget: tk.Widget) -> None:
        """Recursively disable widgets."""
        try:
            widget.configure(state="disabled")
        except tk.TclError:
            pass

        for child in widget.winfo_children():
            self._disable_widget(child)

    def _enable_inputs(self) -> None:
        """Re-enable input fields."""
        for child in self.root.winfo_children():
            self._enable_widget(child)

    def _enable_widget(self, widget: tk.Widget) -> None:
        """Recursively enable widgets."""
        try:
            if isinstance(widget, (ttk.Entry, ttk.Button, ttk.Combobox)):
                widget.configure(state="normal")
            elif isinstance(widget, ttk.Combobox):
                widget.configure(state="readonly")
        except tk.TclError:
            pass

        for child in widget.winfo_children():
            self._enable_widget(child)

    def update_status(self, message: str) -> None:
        """Update status message (thread-safe)."""
        if self.root and self.status_var:
            self.root.after(0, lambda: self.status_var.set(message))

    def update_progress(self, value: float) -> None:
        """Update progress bar (thread-safe). Value is 0-100."""
        if self.root and self.progress_var:
            self.root.after(0, lambda: self.progress_var.set(value))

    def show_error(self, title: str, message: str) -> None:
        """Show error dialog (thread-safe)."""
        if self.root:
            self.root.after(0, lambda: messagebox.showerror(title, message))

    def show_info(self, title: str, message: str) -> None:
        """Show info dialog (thread-safe)."""
        if self.root:
            self.root.after(0, lambda: messagebox.showinfo(title, message))

    def complete(self, success: bool = True) -> None:
        """Mark operation as complete."""
        self.running = False

        if self.root:
            self.root.after(0, self._enable_inputs)

            if success:
                self.update_status("Complete!")
                self.update_progress(100)
            else:
                self.update_status("Failed")
                self.update_progress(0)

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled."""
        return self.cancelled

    def run(self) -> None:
        """Start the GUI event loop."""
        if self.root:
            self.root.mainloop()

    def quit(self) -> None:
        """Close the application."""
        if self.root:
            self.root.quit()
            self.root.destroy()
