"""Settings dialog UI for EBI application.

Provides a tkinter-based dialog for configuring application settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Optional
from equella_settings import SettingsManager


class SettingsDialog:
    """Settings configuration dialog."""

    def __init__(self, parent=None, settings_manager: Optional[SettingsManager] = None):
        """Initialize settings dialog.

        Args:
            parent: Parent tkinter window
            settings_manager: SettingsManager instance
        """
        self.settings = settings_manager or SettingsManager()
        self.result = None

        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("EBI Settings")
        self.root.geometry("600x650")
        self.root.resizable(False, False)

        self._create_widgets()
        self._load_current_settings()

        if parent:
            self.root.transient(parent)
            self.root.grab_set()

    def _create_widgets(self):
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            main_frame,
            text="EBI Application Settings",
            font=("Arial", 14, "bold"),
        )
        title.pack(pady=(0, 20))

        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Institution tab
        self.institution_frame = self._create_institution_tab(notebook)
        notebook.add(self.institution_frame, text="Institution")

        # OAuth tab
        self.oauth_frame = self._create_oauth_tab(notebook)
        notebook.add(self.oauth_frame, text="OAuth")

        # Manual Token tab
        self.token_frame = self._create_token_tab(notebook)
        notebook.add(self.token_frame, text="Manual Token")

        # Advanced tab
        self.advanced_frame = self._create_advanced_tab(notebook)
        notebook.add(self.advanced_frame, text="Advanced")

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 0))

        ttk.Button(button_frame, text="Save", command=self._on_save).pack(
            side=tk.RIGHT, padx=(5, 0)
        )
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Test Connection", command=self._on_test).pack(
            side=tk.LEFT
        )

    def _create_institution_tab(self, parent):
        """Create Institution configuration tab."""
        frame = ttk.Frame(parent, padding="15")

        # Institution URL
        ttk.Label(frame, text="Institution URL:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(
            frame,
            text="e.g., https://equella.your-institution.edu",
            foreground="gray",
            font=("Arial", 9),
        ).pack(anchor=tk.W, pady=(0, 10))

        self.institution_url = ttk.Entry(frame, width=50, font=("Arial", 10))
        self.institution_url.pack(anchor=tk.W, pady=(0, 20), fill=tk.X)

        # Info box
        info_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=1)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        info_text = scrolledtext.ScrolledText(
            info_frame,
            height=10,
            width=50,
            font=("Arial", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
        )
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_text.insert(
            tk.END,
            "Enter the base URL of your openEQUELLA institution.\n\n"
            "Do NOT include:\n"
            "  • /logon.do\n"
            "  • /apidocs.do\n"
            "  • trailing slashes\n\n"
            "Examples:\n"
            "  ✓ https://equella.institution.edu\n"
            "  ✓ https://learning.university.org/equella\n"
            "  ✗ https://equella.institution.edu/\n"
            "  ✗ https://equella.institution.edu/logon.do",
        )
        info_text.config(state=tk.DISABLED)

        return frame

    def _create_oauth_tab(self, parent):
        """Create OAuth configuration tab."""
        frame = ttk.Frame(parent, padding="15")

        # OAuth Client ID
        ttk.Label(frame, text="OAuth Client ID:", font=("Arial", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )
        ttk.Label(
            frame,
            text="Get this from Settings → Integration → OAuth → Registered client applications",
            foreground="gray",
            font=("Arial", 9),
        ).pack(anchor=tk.W, pady=(0, 10))

        self.oauth_client_id = ttk.Entry(frame, width=50, font=("Arial", 10))
        self.oauth_client_id.pack(anchor=tk.W, pady=(0, 20), fill=tk.X)

        # OAuth Redirect URI
        ttk.Label(frame, text="OAuth Redirect URI:", font=("Arial", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )
        ttk.Label(
            frame,
            text="Leave empty to use default (recommended)",
            foreground="gray",
            font=("Arial", 9),
        ).pack(anchor=tk.W, pady=(0, 10))

        self.oauth_redirect_uri = ttk.Entry(frame, width=50, font=("Arial", 10))
        self.oauth_redirect_uri.pack(anchor=tk.W, pady=(0, 20), fill=tk.X)

        # Info box
        info_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=1)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        info_text = scrolledtext.ScrolledText(
            info_frame,
            height=10,
            width=50,
            font=("Arial", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
        )
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_text.insert(
            tk.END,
            "OAuth 2.0 Implicit Grant Flow\n\n"
            "Steps:\n"
            "1. Log in to your openEQUELLA institution\n"
            "2. Go to Settings → Integration → OAuth\n"
            "3. Click 'Register new client application'\n"
            "4. Select 'Implicit Grant' as the OAuth flow\n"
            "5. Copy the Client ID shown after saving\n"
            "6. Paste the Client ID here\n\n"
            "When you run the application, it will open your browser "
            "to request authorization. Simply log in and approve access.",
        )
        info_text.config(state=tk.DISABLED)

        return frame

    def _create_token_tab(self, parent):
        """Create manual token configuration tab."""
        frame = ttk.Frame(parent, padding="15")

        ttk.Label(
            frame,
            text="Use this tab only if you have a pre-existing OAuth token",
            font=("Arial", 10, "bold"),
            foreground="darkblue",
        ).pack(anchor=tk.W, pady=(0, 20))

        # REST Access Token
        ttk.Label(frame, text="REST Access Token:", font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(
            frame,
            text="For regular user access",
            foreground="gray",
            font=("Arial", 9),
        ).pack(anchor=tk.W, pady=(0, 10))

        self.rest_access_token = ttk.Entry(frame, width=50, font=("Arial", 10), show="•")
        self.rest_access_token.pack(anchor=tk.W, pady=(0, 20), fill=tk.X)

        # REST Admin Token
        ttk.Label(frame, text="REST Admin Token:", font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(
            frame,
            text="For administrator/import access",
            foreground="gray",
            font=("Arial", 9),
        ).pack(anchor=tk.W, pady=(0, 10))

        self.rest_admin_token = ttk.Entry(frame, width=50, font=("Arial", 10), show="•")
        self.rest_admin_token.pack(anchor=tk.W, pady=(0, 20), fill=tk.X)

        # Info box
        info_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=1)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        info_text = scrolledtext.ScrolledText(
            info_frame,
            height=8,
            width=50,
            font=("Arial", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
        )
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_text.insert(
            tk.END,
            "If you already have a valid OAuth token UUID, you can paste it here.\n\n"
            "Access tokens are usually UUIDs like:\n"
            "1d031eef-185a-4c22-a922-b996391b9f4f\n\n"
            "This bypasses the browser-based OAuth flow.",
        )
        info_text.config(state=tk.DISABLED)

        return frame

    def _create_advanced_tab(self, parent):
        """Create advanced settings tab."""
        frame = ttk.Frame(parent, padding="15")

        # Debug mode
        self.debug_var = tk.BooleanVar()
        ttk.Checkbutton(
            frame,
            text="Enable Debug Mode",
            variable=self.debug_var,
            font=("Arial", 10),
        ).pack(anchor=tk.W, pady=(0, 20))

        ttk.Label(
            frame,
            text="Troubleshooting & Logging",
            font=("Arial", 10, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))

        info_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=1)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        info_text = scrolledtext.ScrolledText(
            info_frame,
            height=12,
            width=50,
            font=("Arial", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
        )
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_text.insert(
            tk.END,
            "Settings Storage Location:\n"
            "  Windows: %APPDATA%\\EBI\\settings.json\n"
            "  macOS/Linux: ~/.config/ebi/settings.json\n\n"
            "Debug Mode:\n"
            "  When enabled, detailed logging is printed to the console.\n"
            "  Useful for troubleshooting authentication and API issues.\n\n"
            "Configuration File:\n"
            "  You can manually edit the settings.json file if needed.\n"
            "  Close the application before editing the file.\n\n"
            "Token Management:\n"
            "  View and revoke tokens in openEQUELLA:\n"
            "  Settings → Integration → OAuth → Generated tokens",
        )
        info_text.config(state=tk.DISABLED)

        return frame

    def _load_current_settings(self):
        """Load current settings into dialog fields."""
        settings = self.settings.get_all()

        self.institution_url.insert(0, settings.get("institution_url", ""))
        self.oauth_client_id.insert(0, settings.get("oauth_client_id", ""))
        self.oauth_redirect_uri.insert(0, settings.get("oauth_redirect_uri", "default"))
        self.rest_access_token.insert(0, settings.get("rest_access_token", ""))
        self.rest_admin_token.insert(0, settings.get("rest_admin_token", ""))
        self.debug_var.set(settings.get("debug", False))

    def _on_test(self):
        """Test connection to institution."""
        institution_url = self.institution_url.get().strip()
        if not institution_url:
            messagebox.showwarning("Validation", "Please enter an Institution URL")
            return

        try:
            import urllib.request

            request = urllib.request.Request(
                institution_url + "/api/collection?start=0&length=1",
                headers={"Accept": "application/json"},
                method="GET",
            )
            response = urllib.request.urlopen(request, timeout=5)
            if response.status == 200:
                messagebox.showinfo(
                    "Success",
                    f"Successfully connected to:\n{institution_url}",
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"Server returned status: {response.status}",
                )
        except Exception as e:
            messagebox.showerror(
                "Connection Failed",
                f"Could not connect to institution:\n\n{str(e)}\n\n"
                "Please check:\n"
                "  • Institution URL is correct\n"
                "  • Server is accessible\n"
                "  • Network/firewall settings",
            )

    def _on_save(self):
        """Save settings and close dialog."""
        institution_url = self.institution_url.get().strip()

        if not institution_url:
            messagebox.showerror("Validation Error", "Institution URL is required")
            return

        # Validate that at least one authentication method is configured
        has_oauth = bool(self.oauth_client_id.get().strip())
        has_access_token = bool(self.rest_access_token.get().strip())
        has_admin_token = bool(self.rest_admin_token.get().strip())

        if not (has_oauth or has_access_token or has_admin_token):
            messagebox.showerror(
                "Validation Error",
                "Please configure at least one authentication method:\n"
                "  • OAuth Client ID, OR\n"
                "  • REST Access Token, OR\n"
                "  • REST Admin Token",
            )
            return

        # Save settings
        self.settings.set("institution_url", institution_url)
        self.settings.set("oauth_client_id", self.oauth_client_id.get().strip())
        self.settings.set("oauth_redirect_uri", self.oauth_redirect_uri.get().strip() or "default")
        self.settings.set("rest_access_token", self.rest_access_token.get().strip())
        self.settings.set("rest_admin_token", self.rest_admin_token.get().strip())
        self.settings.set("debug", self.debug_var.get())

        self.settings.save()
        self.result = True

        messagebox.showinfo(
            "Success",
            "Settings saved successfully!\n\n"
            "The application will use these settings on next run.",
        )
        self.root.destroy()

    def _on_cancel(self):
        """Close dialog without saving."""
        self.result = False
        self.root.destroy()

    def show(self) -> bool:
        """Show dialog and wait for result.

        Returns:
            True if settings were saved, False if cancelled
        """
        self.root.wait_window()
        return self.result or False


def show_settings_dialog(parent=None, settings_manager: Optional[SettingsManager] = None) -> bool:
    """Convenience function to show settings dialog.

    Args:
        parent: Parent tkinter window
        settings_manager: SettingsManager instance

    Returns:
        True if settings were saved, False if cancelled
    """
    dialog = SettingsDialog(parent, settings_manager)
    return dialog.show()


if __name__ == "__main__":
    # Test the dialog
    show_settings_dialog()
