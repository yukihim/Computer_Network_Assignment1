import random
import socket
import threading
import os
import shutil
from client import peer
import tkinter
import sys
from tkinter import filedialog

END = "end"

global gui_message 
gui_message = "Welcome to our File Sharing App!!"

def wlan_ip():
    import subprocess
    result=subprocess.run('ipconfig',stdout=subprocess.PIPE,text=True).stdout.lower()
    scan=0
    for i in result.split('\n'):
        if 'wireless' in i: scan=1
        if scan:
            if 'ipv4' in i: return i.split(':')[1].strip()

def Publish_Command():
    global gui_message
    try:
        file_name = publish_input_entry.get()
        publish_input_entry.delete(0, END)
        sender.publish(file_name, file_name)
        gui_message = "Published " + file_name
    except socket.error:
        gui_message = "Published " + file_name + " failed!!, Error: " + repr(socket.error)
        print(socket.error)
    except BaseException as e:
        gui_message = "Published " + file_name + " failed!!, Error: " + repr(e)
    finally:
        message_label.insert(gui_message)

def Stop_Publish_Command():
    global gui_message
    try: 
        file_name = stop_publish_input_entry.get()
        stop_publish_input_entry.delete(0, END)
        sender.stop_publish_specific_file(file_name)
        gui_message = "Stop Published " + file_name
    except socket.error:
        gui_message = "Stop Published " + file_name + " failed!!, Error: " + str(socket.error)
    except BaseException as e:
        gui_message = "Stop Published " + file_name + " failed!!, Error: " + str(e)
        print(e)
    finally:
        message_label.insert(gui_message)

def Fetch_Command():
    global gui_message
    try:
        file_name = fetch_input_entry.get()
        fetch_input_entry.delete(0, END)
        receiver.fetch(file_name)
        gui_message = "Fetched " + file_name
    except socket.error:
        gui_message = "Fetched " + file_name + " failed!!, Error: " + str(socket.error)
    except BaseException as e:
        gui_message = "Fetched " + file_name + " failed!!, Error: " + str(e)
    finally:
        message_label.insert(gui_message)

def Stop_Command():
    try:
        sys.stdout = old_std
        sender.stop_publish()
        receiver.stop_receive()
    except BaseException:
        pass
    finally:
        main_window.destroy()
        # Delete the directory after the program ends
        shutil.rmtree(repo_dir)
        exit(1)

# Get the host name of the machine
host_name = socket.gethostname()
random_port_number = random.randint(0, 1000)

#host_last_8bit_ip = socket.gethostbyname(host_name)
host_ip = wlan_ip()

sender_port = 1000 + random_port_number
receiver_port = 2000 + random_port_number

this_file_path = os.path.dirname(os.path.realpath(__file__))       
repo_dir = this_file_path + "/user_repo_" + str(random_port_number) + "/"

os.makedirs(repo_dir, exist_ok=True)

receiver = peer.ReceiverPeer(host_ip, receiver_port, repo_dir)
sender = peer.SenderPeer(host_ip, sender_port, repo_dir)


#**Region GUI**#
main_window = tkinter.Tk()

main_window.title('User')
main_window.sourceFile = ''

tkinter.Label(main_window, text="Host name:"+ host_name).grid(row=6, column=0)
tkinter.Label(main_window, text="IP address:"+ host_ip).grid(row=6, column=1)
tkinter.Label(main_window, text="Repo directory:"+ "/user_repo_" + str(random_port_number)).grid(row=6, column=2, columnspan=2) 

#* Publish 
tkinter.Label(main_window, text='File to Publish').grid(row=0, column=0)

publish_input_entry = tkinter.Entry(main_window)
publish_input_entry.grid(row=0, column=1)

button = tkinter.Button(main_window, text='Publish', width=20, command=Publish_Command).grid(row=0, column=2)

#*Stop Publish
tkinter.Label(main_window, text='File to stop Publish').grid(row=2, column=0)

stop_publish_input_entry = tkinter.Entry(main_window)
stop_publish_input_entry.grid(row=2, column=1)

button = tkinter.Button(main_window, text='Stop publish', width=20, command=Stop_Publish_Command).grid(row=2, column=2)

#*Fetch
tkinter.Label(main_window, text='File to Fetch').grid(row=3, column=0)

fetch_input_entry = tkinter.Entry(main_window)
fetch_input_entry.grid(row=3, column=1)

button = tkinter.Button(main_window, text='Fetch', width=20, command=Fetch_Command).grid(row=3, column=2)

#*Stop
button = tkinter.Button(main_window, text='Stop', width=20, command=Stop_Command).grid(row=4, column=0)

#*GUI Message
message_label = tkinter.Text(main_window, )
message_label.grid(row=7, column=0, columnspan=3, rowspan=2)

main_window.minsize(600, 300)

def chooseFile():
    main_window.sourceFile = filedialog.askopenfilename(parent=main_window,
                                                        initialdir= "/", 
                                                        title='Please select a directory')
    sourceString.config(text=main_window.sourceFile)
    file_name = os.path.basename(main_window.sourceFile)
    print(file_name)
    dst =  repo_dir + file_name
    shutil.copyfile(main_window.sourceFile, dst)

b_chooseFile = tkinter.Button(main_window, text = "Put file in repo", width = 20, command = chooseFile).grid(row=5, column=0)
sourceString = tkinter.Label(main_window, text=main_window.sourceFile)
sourceString.grid(row=5, column=2)

class PrintRedirector:
    def __init__(self):
        pass

    def write(self, message):
        global gui_message
        if (message != '' and message != None):
            gui_message = message
            message_label.insert(tkinter.END, gui_message)
        
    def flush(self):
        pass
    
old_std = sys.stdout
sys.stdout = PrintRedirector()

def clear_text():
    message_label.delete('1.0', END)
    main_window.after(10000, clear_text)

main_window.protocol("WM_DELETE_WINDOW", Stop_Command)

main_window.after(10000, clear_text)
main_window.mainloop()


