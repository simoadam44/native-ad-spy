from cloakbrowser import binary_info
import os
import platform

print(f"Platform: {platform.system()}")
print(f"Current Directory: {os.getcwd()}")
try:
    info = binary_info()
    print(f"Binary Info: {info}")
except Exception as e:
    print(f"Error calling binary_info(): {e}")
