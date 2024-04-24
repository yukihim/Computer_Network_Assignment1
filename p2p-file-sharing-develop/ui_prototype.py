import tkinter
from tkinter import filedialog
import os
import shutil

END = "end"


def Publish_Command():
    file_name = publish_input_entry.get()
    publish_input_entry.delete(0, END)
    print("Published", file_name)
    
def Fetch_Command():
    file_name = fetch_input_entry.get()
    fetch_input_entry.delete(0, END)
    print("Fetched", file_name)
    pass

def Stop_Command():  
    main_window.destroy()
    pass

main_window = tkinter.Tk()
main_window.sourceFile = ''

main_window.title('UI Prototype')

tkinter.Label(main_window, text='File to Publish').grid(row=0, column=0)

publish_input_entry = tkinter.Entry(main_window)
publish_input_entry.grid(row=0, column=1)

button = tkinter.Button(main_window, text='Publish', width=20, command=Publish_Command).grid(row=0, column=2)

tkinter.Label(main_window, text='File to Fetch').grid(row=1, column=0)

fetch_input_entry = tkinter.Entry(main_window)
fetch_input_entry.grid(row=1, column=1)

button = tkinter.Button(main_window, text='Fetch', width=20, command=Fetch_Command).grid(row=1, column=2)

button = tkinter.Button(main_window, text='Stop', width=20, command=Stop_Command).grid(row=3, column=0)

def chooseFile():
    main_window.sourceFile = filedialog.askopenfilename(parent=main_window,
                                                        initialdir= "/", 
                                                        title='Please select a directory')
    sourceString.config(text=main_window.sourceFile)
    file_name = os.path.basename(main_window.sourceFile)
    print(file_name)
    dst = "C:/Users/nvhuy/Documents/GitHub/p2p-file-sharing-fork/sender_repo_test/" + file_name
    shutil.copyfile(main_window.sourceFile, dst)

b_chooseFile = tkinter.Button(main_window, text = "Put file in repo", width = 20, command = chooseFile).grid(row=4, column=0)
sourceString = tkinter.Label(main_window, text=main_window.sourceFile)
sourceString.grid(row=4, column=2)

main_window.minsize(600, 300)

main_window.mainloop()

