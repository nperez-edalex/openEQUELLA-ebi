"""EBI Application Launcher

Main entry point for the EBI executable application.
Handles settings dialog and initialization of the REST client.
"""

import sys
import tkinter as tk
from equella_settings import SettingsManager
from equella_settings_ui import SettingsDialog
from equellaclient_rest import TLEClient


class EBILauncher:
    """Launcher for EBI application."""

    def __init__(self):
        """Initialize the launcher."""
        self.settings = SettingsManager()
        self.client = None

    def ensure_configured(self) -> bool:
        """Ensure application is configured.

        Shows settings dialog if not configured or if explicitly requested.

        Returns:
            True if configured, False if user cancelled
        """
        if not self.settings.is_configured():
            print("EBI Application Configuration")
            print("=" * 50)
            print("No settings found. Please configure the application.")
            print()

            if not self._show_settings_dialog():
                print("Configuration cancelled.")
                return False

            print("Configuration complete!")
            return True

        return True

    def _show_settings_dialog(self) -> bool:
        """Show the settings configuration dialog.

        Returns:
            True if settings were saved, False if cancelled
        """
        # Create a hidden root window for tkinter
        root = tk.Tk()
        root.withdraw()  # Hide the root window

        dialog = SettingsDialog(root, self.settings)
        result = dialog.show()

        root.destroy()
        return result

    def show_settings(self) -> bool:
        """Show settings dialog for user to modify settings.

        Returns:
            True if settings were saved, False if cancelled
        """
        print("Opening EBI Settings...")
        return self._show_settings_dialog()

    def create_client(self, owner="EBI") -> TLEClient:
        """Create and return a configured REST client.

        Args:
            owner: Owner identifier for the client

        Returns:
            Configured TLEClient instance

        Raises:
            ValueError: If settings are not properly configured
        """
        if not self.settings.is_configured():
            raise ValueError(
                "Application is not configured. "
                "Please run the settings configuration first."
            )

        if not self.settings.has_credentials():
            raise ValueError(
                "No authentication credentials configured. "
                "Please configure OAuth Client ID or a REST token."
            )

        institution_url = self.settings.get("institution_url")
        debug = self.settings.get("debug", False)

        self.client = TLEClient(
            owner=owner,
            institutionUrl=institution_url,
            debug=debug,
            settings_manager=self.settings,
        )

        return self.client

    def run_import(self, import_function):
        """Run import operation with configured client.

        Args:
            import_function: Callable that accepts a TLEClient and performs import

        Returns:
            Result from import_function
        """
        if not self.ensure_configured():
            return None

        try:
            client = self.create_client()
            print(f"\nConnected to: {self.settings.get('institution_url')}")
            print()
            return import_function(client)
        except Exception as e:
            print(f"\nError: {str(e)}", file=sys.stderr)
            if self.settings.get("debug"):
                import traceback
                traceback.print_exc()
            return None


def main():
    """Main entry point for the application.

    Demonstrates how to use the launcher in your application.
    """
    launcher = EBILauncher()

    # Ensure settings are configured
    if not launcher.ensure_configured():
        sys.exit(1)

    # Example: Create client and list collections
    try:
        client = launcher.create_client()
        print("Successfully created REST client!")
        print(f"Institution: {client.institutionUrl}")

        # Uncomment to test API call:
        # collections = client._get_collections_by_privilege("DISCOVER_ITEM")
        # print(f"Accessible collections: {len(collections)}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
