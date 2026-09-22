import threading
import time
import webbrowser

from app import app

from database import (
    create_database,
    save_media,
)

from drives import (
    discover_drives,
    print_drives,
)

from scanner import (
    scan_drive,
    print_results,
)

from services.enrich import enrich_library
from services.enrich_tv import enrich_tv
from services.link_episodes import link_episodes
from services.enrich_episodes import enrich_episodes


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

HOST = "127.0.0.1"
PORT = 8050

DASH_URL = f"http://{HOST}:{PORT}"

# Current Ubuntu media drive.
MEDIA_MOUNTPOINT = "/media/bbk/zKr0wz"


# --------------------------------------------------
# DRIVE DETECTION
# --------------------------------------------------

def find_media_drive():
    """
    Find the configured media drive.

    If it cannot be found automatically,
    allow the user to select another drive
    or start the library without scanning.
    """

    drives = discover_drives()

    if not drives:
        print("\nNo storage drives detected.")
        return None

    # Look for our normal media drive.
    for drive in drives:

        if drive.mountpoint == MEDIA_MOUNTPOINT:

            print("\nMedia drive detected.")
            print(f"Device:     {drive.device}")
            print(f"Mountpoint: {drive.mountpoint}")
            print(f"Filesystem: {drive.filesystem}")

            return drive

    # Media drive wasn't found.
    print(
        "\nConfigured media drive was not "
        "automatically detected."
    )

    print_drives(drives)

    print(
        "[0] Start library without scanning"
    )

    while True:

        choice = input(
            "Select media drive: "
        ).strip()

        if choice == "0":
            return None

        try:
            index = int(choice) - 1

            if 0 <= index < len(drives):
                return drives[index]

        except ValueError:
            pass

        print(
            "Please enter a valid drive number."
        )


# --------------------------------------------------
# SCAN MEDIA
# --------------------------------------------------

def scan_library():
    """
    Detect the media drive, scan it, and save
    discovered media files into SQLite.

    Returns True when a media drive was scanned.
    """

    print("\n" + "=" * 60)
    print("CHECKING MEDIA DRIVE")
    print("=" * 60)

    drive = find_media_drive()

    if drive is None:

        print(
            "\nNo media drive selected."
        )

        print(
            "Using existing library database."
        )

        return False

    print(
        f"\nScanning media drive:"
        f"\n{drive.mountpoint}"
    )

    media_files = scan_drive(
        drive.mountpoint
    )

    if not media_files:

        print(
            "\nNo media files found."
        )

        print(
            "Using existing library database."
        )

        return False

    # Show scan summary.
    print_results(
        media_files
    )

    # Save/update SQLite.
    saved = save_media(
        media_files
    )

    print("\nDATABASE")
    print("=" * 60)

    print(
        f"Media records saved: {saved}"
    )

    return True


# --------------------------------------------------
# METADATA PIPELINE
# --------------------------------------------------

def update_metadata():
    """
    Run the metadata and TV episode pipeline.

    Existing matched movie/episode metadata is
    skipped by the enrichment functions.
    """

    print("\n" + "=" * 60)
    print("UPDATING LIBRARY METADATA")
    print("=" * 60)

    # ----------------------------------------------
    # MOVIES
    # ----------------------------------------------

    print("\n[1/4] Movie metadata")
    print("-" * 60)

    try:
        enrich_library()

    except Exception as error:
        print(
            f"Movie enrichment failed: {error}"
        )

    # ----------------------------------------------
    # TV SHOWS
    # ----------------------------------------------

    print("\n[2/4] TV show metadata")
    print("-" * 60)

    try:
        enrich_tv()

    except Exception as error:
        print(
            f"TV enrichment failed: {error}"
        )

    # ----------------------------------------------
    # LINK EPISODES
    # ----------------------------------------------

    print("\n[3/4] Linking TV episodes")
    print("-" * 60)

    try:
        link_episodes()

    except Exception as error:
        print(
            f"Episode linking failed: {error}"
        )

    # ----------------------------------------------
    # EPISODE METADATA
    # ----------------------------------------------

    print("\n[4/4] Episode metadata")
    print("-" * 60)

    try:
        enrich_episodes()

    except Exception as error:
        print(
            f"Episode enrichment failed: {error}"
        )

    print("\n" + "=" * 60)
    print("LIBRARY UPDATE COMPLETE")
    print("=" * 60)


# --------------------------------------------------
# BROWSER
# --------------------------------------------------

def open_browser():
    """
    Give Dash time to start and then open
    the media library in the default browser.
    """

    time.sleep(1.5)

    print(
        f"\nOpening browser: {DASH_URL}"
    )

    webbrowser.open(
        DASH_URL
    )


# --------------------------------------------------
# START DASH
# --------------------------------------------------

def start_dash():

    browser_thread = threading.Thread(
        target=open_browser,
        daemon=True,
    )

    browser_thread.start()

    print("\n" + "=" * 60)
    print("STARTING MY MEDIA LIBRARY")
    print("=" * 60)

    print(
        f"\nServer: {DASH_URL}"
    )

    print(
        "Press Ctrl+C to stop the server.\n"
    )

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\n" + "=" * 60)
    print("MY MEDIA LIBRARY")
    print("=" * 60)

    # Make sure SQLite and all required tables exist.
    create_database()

    # Scan external media drive.
    drive_scanned = scan_library()

    # Only run the metadata pipeline when the
    # media drive was actually scanned.
    #
    # If the drive isn't connected, we'll simply
    # launch Dash using the existing database.
    if drive_scanned:

        update_metadata()

    else:

        print(
            "\nSkipping media update."
        )

        print(
            "Starting with existing library."
        )

    # Start Dash and open browser.
    start_dash()


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    main()