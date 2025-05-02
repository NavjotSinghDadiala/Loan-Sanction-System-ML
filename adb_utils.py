import subprocess
import os

def make_phone_call(phone_number):
    """
    Make a phone call using ADB to a connected Android device
    """
    try:
        # Adjust ADB path
        adb_path = os.getenv('ANDROID_HOME', '') + '/platform-tools/adb'
        if not os.path.exists(adb_path):
            adb_path = 'adb'  # fallback to PATH

        # Check if device is connected
        devices = subprocess.check_output([adb_path, 'devices']).decode('utf-8')
        if 'device' not in devices:
            print("No Android device connected.")
            return False

        # Make the call
        subprocess.run([
            adb_path, 'shell', 'am', 'start', 
            '-a', 'android.intent.action.CALL', 
            '-d', f'tel:{phone_number}'
        ])
        print(f"Calling {phone_number}...")
        return True
    except Exception as e:
        print(f"Error making phone call: {str(e)}")
        return False
