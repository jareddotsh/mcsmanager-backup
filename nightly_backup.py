import requests
import time
import subprocess
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# API Configuration
API_URL = "https://panel.mc.jared.cloud"
API_KEY = os.getenv("API_KEY")  # Load API key from environment variable

HEADERS = {'Content-Type': 'application/json'}

# API Utility Functions
def get_daemon_info():
    """Fetches daemon information from the API."""
    url = f"{API_URL}/api/overview"
    params = {'apikey': API_KEY}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching daemon info: {e}")
        return None

def get_instance_info(daemon_id, page=1, page_size=10, status="", name=""):
    """Fetches instance information for a given daemon."""
    url = f"{API_URL}/api/service/remote_service_instances"
    params = {'apikey': API_KEY, 'daemonId': daemon_id, 'page': page, 'page_size': page_size, 'instance_name': name, 'status': status}

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching instance info: {e}")
        return None

def send_command_to_instance(daemon, instance, command):
    """Sends a command to a given instance."""
    url = f"{API_URL}/api/protected_instance/command"
    params = {'apikey': API_KEY, 'uuid': instance, 'daemonId': daemon, 'command': command}

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        logging.info(f"Sent command '{command}' to instance {instance}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending command to instance: {e}")
        return None

def stop_instance(daemon, instance):
    """Stops a given instance."""
    url = f"{API_URL}/api/protected_instance/stop"
    params = {'apikey': API_KEY, 'uuid': instance, 'daemonId': daemon}

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        logging.info(f"Stopped instance {instance}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error stopping instance: {e}")
        return None

def start_instance(daemon, instance):
    """Starts a given instance."""
    url = f"{API_URL}/api/protected_instance/open"
    params = {'apikey': API_KEY, 'uuid': instance, 'daemonId': daemon}

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        logging.info(f"Started instance {instance}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error starting instance: {e}")
        return None

def create_backup():
    """Runs the backup script."""
    logging.info("Starting backup process...")
    result = subprocess.run(['/root/scripts/backup.sh'], capture_output=True, text=True)
    
    if result.returncode == 0:
        logging.info("Backup completed successfully.")
    else:
        logging.error(f"Backup failed: {result.stderr}")

def countdown_warnings(daemon, instance, warnings):
    """Sends multiple countdown warnings before shutting down."""
    for message, delay in warnings:
        send_command_to_instance(daemon, instance, message)
        logging.info(f"Waiting {delay} seconds before next warning...")
        time.sleep(delay)

# Main Execution
def nightly_backup():
    """Executes the full nightly backup routine."""
    daemons = get_daemon_info()
    if not daemons:
        logging.error("Failed to retrieve daemon data. Exiting.")
        return

    for remote in daemons.get("data", {}).get("remote", []):
        daemon_id = remote["uuid"]
        daemon_name = remote["remarks"]

        instances = get_instance_info(daemon_id, page=1, page_size=10, name=daemon_name)
        if not instances:
            logging.warning(f"No instances found for daemon {daemon_name}. Skipping.")
            continue

        for instance in instances.get("data", {}).get("data", []):
            instance_id = instance["instanceUuid"]

            warnings = [
                ("say Server powering off in 10 minutes for nightly backup...", 300),
                ("say Server powering off in 5 minutes for nightly backup...", 240),
                ("say Server powering off in 1 minute for nightly backup...", 60),
                ("say Server powering off for nightly backup...server will power on again shortly.", 0)
            ]

            countdown_warnings(daemon_id, instance_id, warnings)

            send_command_to_instance(daemon_id, instance_id, "save-all")
            time.sleep(120)

            stop_instance(daemon_id, instance_id)
            time.sleep(120)

            create_backup()

            start_instance(daemon_id, instance_id)

if __name__ == "__main__":
    nightly_backup()
