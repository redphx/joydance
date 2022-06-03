import subprocess
import sys
import webview

dance_server = None
try:
    window = webview.create_window('Just dance!', 'http://localhost:32623', confirm_close=True)
    dance_server = subprocess.Popen([sys.executable or 'python', "dance.py"])
    webview.start()

    #terminate server on window close
    dance_server.terminate()

except Exception: # if GUI not available or error, ex. in a server terminal
    dance_server.terminate()
    startInTerminalMode = input("ERROR: Couln't open the GUI. Would you like to start in terminal mode instead? (y/n)")

    if (startInTerminalMode == 'y'):
        subprocess.call([sys.executable or 'python', "dance.py"])
    else: print("Exiting...")