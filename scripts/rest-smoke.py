import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
SOURCE_DIR = os.path.join(REPO_ROOT, "source")
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

# Force REST transport for this smoke script.
os.environ["EBI_API_TRANSPORT"] = "rest"

from equellaclient import TLEClient


class SmokeOwner:
    def __init__(self):
        self.networkLogging = False
        self.StopProcessing = False

    def echo(self, message, *args, **kwargs):
        # Keep output concise for CLI smoke testing.
        print(message)


def require_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in your shell before running this script."
        )
    return value


def main():
    institution_url = require_env("EBI_TEST_INSTITUTION_URL")
    username = require_env("EBI_TEST_USERNAME")
    password = require_env("EBI_TEST_PASSWORD")
    print("Using credential-based session login.")

    owner = SmokeOwner()

    print("Connecting with REST transport...")
    client = TLEClient(owner, institution_url, username, password)

    print("Fetching collections...")
    collections = client._enumerateItemDefs(forExport=False)
    if not collections:
        raise RuntimeError("No collections returned from REST API")

    first_name = sorted(collections.keys())[0]
    first_uuid = collections[first_name]["uuid"]
    print(f"Collection count: {len(collections)}")
    print(f"Using collection: {first_name} ({first_uuid})")

    print("Running basic search...")
    results = client.search(0, 1, "*", [first_uuid], where="", query="", onlyLive=True)
    available = results.getNode("available")
    print(f"Search available: {available}")

    print("Smoke read-path completed successfully.")
    client.logout()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE FAILURE: {exc}")
        sys.exit(1)
