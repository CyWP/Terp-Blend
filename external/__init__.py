from tkinter import *
from tkinter import filedialog
from mvnet import *

root = Tk()  # create a root widget
#Variables
webcam = BooleanVar(root, True)
show = BooleanVar(root, True)
vidpath =StringVar(root, "/path/to/file")
#Utils/Operators
def toggle_webcam():
    new = not(webcam.get())
    root.setvar(name="webcam", value=new)

def toggle_show():
    new = not(show.get())
    root.setvar(name="show", value=new)

def browseFiles():
    filename = filedialog.askopenfilename(initialdir = "/", title = "Select a File", filetypes = (("all files","*.*"),("Video Files","*.mp4*")))    
    # Change label contents
    video_label.configure(text="Video: "+filename)
    vidpath.set(filename)

def launch():
    webindex = index_entry.get()
    if webindex == "":
        index=0
    else:
        index = int(webindex)
    launchmvnet(webcam.get(), index, vidpath.get(), int(wek_entry.get()), int(blend_entry.get()), int(delay_entry.get()), int(duration_entry.get()), show.get())

#Build Panel
root.title("Terpsichore v0.0 (Powered by MoveNet Lightning)")
root.minsize(400, 160)  # width, height
root.maxsize(400, 200)
root.geometry("400x160+25+25")  # width x height + x + y
root.config(bg="#FFFFFF")
#Webcam settings
webcam_button = Checkbutton(root, text="Use Webcam", bg="#FFFFFF", command=toggle_webcam, variable=webcam)
webcam_button.grid(row=1, column=1, columnspan=2)
Label(root, text="Index", bg='#FFFFFF').grid(row=1, column=3)
index_entry = Entry(root, bd=1)
index_entry.grid(row=1, column=4)
Label(root, text="Delay", bg="#FFFFFF").grid(row=2 ,column=1)
delay_entry = Entry(root, bd=1)
delay_entry.grid(row=2, column=2)
Label(root, text="Duration", bg="#FFFFFF").grid(row=2, column=3)
duration_entry = Entry(root, bd=1)
duration_entry.grid(row=2, column=4)
#video settings
Button(root, text="Browse", command=browseFiles).grid(row=3, column=4)
video_label = Label(root, text="/path/to/video", bg='#CCCCCC')
video_label.grid(row=3, column=1, columnspan=3)
#OSC Settings
Label(root, text="OSC Ports", bg="#FFFFFF").grid(row=4, column=1, columnspan=4)
Label(root, text="Wekinator", bg="#FFFFFF").grid(row=5, column=1)
wek_entry = Entry(root, bd=1)
wek_entry.grid(row=5, column=2)
Label(root, text="Blender", bg="#FFFFFF").grid(row=5, column=3)
blend_entry = Entry(root, bd=1)
blend_entry.grid(row=5, column=4)
#Start button
Button(root, text="Start", command=launch).grid(row=6, column=1, columnspan=2)
Checkbutton(root, text="Video feedback", bg="#FFFFFF", command=toggle_show, variable=show).grid(row=6, column=3)

root.mainloop()
