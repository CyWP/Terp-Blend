from tkinter import *
from tkinter import filedialog
from mvnet import *

root = Tk()  # create a root widget
#Variables
webcam = BooleanVar(root, True)
show = BooleanVar(root, True)
vidpath =StringVar(root, "C:/Users/thoma/Documents/FALL23\CART398\Final/test.mp4")
tfpath =StringVar(root, "C:/Users/thoma/Documents/FALL23/CART398/Finallite-model_movenet_singlepose_lightning_3.tflite")
#Utils/Operators
def toggle_webcam():
    new = not(webcam.get())
    root.setvar(name="webcam", value=new)

def toggle_show():
    new = not(show.get())
    root.setvar(name="show", value=new)

def browseVidFiles():
    filename = filedialog.askopenfilename(initialdir = "/", title = "Select a File", filetypes = (("all files","*.*"),("Video Files","*.mp4*")))    
    # Change label contents
    if len(filename)>25:
        video_label.configure(text="Video: "+"..."+filename[-25:])
    else:
        video_label.configure(text="Video: "+filename)
    vidpath.set(filename)

def browseTfFiles():
    filename = filedialog.askopenfilename(initialdir = "/", title = "Select a File", filetypes = (("all files","*.*"),("Video Files","*.mp4*")))    
    # Change label contents
    if len(filename)>25:
        tf_label.configure(text="Model: "+"..."+filename[-25:])
    else:
        tf_label.configure(text="Model: "+filename)
    tfpath.set(filename)

def launch():
    launchmvnet(webcam.get(), index_entry.get(), vidpath.get(), tfpath.get(), int(wek_entry.get()), int(blend_entry.get()), int(delay_entry.get()), int(duration_entry.get()), show.get())

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
index_entry.insert(10, "0")
Label(root, text="Delay", bg="#FFFFFF").grid(row=2 ,column=1)
delay_entry = Entry(root, bd=1)
delay_entry.grid(row=2, column=2)
delay_entry.insert(10, "5")
Label(root, text="Duration", bg="#FFFFFF").grid(row=2, column=3)
duration_entry = Entry(root, bd=1)
duration_entry.grid(row=2, column=4)
duration_entry.insert(10, "15")
#video settings
Button(root, text="Browse", command=browseVidFiles).grid(row=3, column=4)
video_label = Label(root, text="/path/to/video", bg='#CCCCCC')
video_label.grid(row=3, column=1, columnspan=3)
#Path to tflite model
Button(root, text="Browse", command=browseTfFiles).grid(row=4, column=4)
tf_label = Label(root, text="/path/to/model", bg='#CCCCCC')
tf_label.grid(row=4, column=1, columnspan=3)
#OSC Settings
Label(root, text="OSC Ports", bg="#FFFFFF").grid(row=5, column=1, columnspan=4)
Label(root, text="Wekinator", bg="#FFFFFF").grid(row=6, column=1)
wek_entry = Entry(root, bd=1)
wek_entry.grid(row=6, column=2)
wek_entry.insert(10, "6448")
Label(root, text="Blender", bg="#FFFFFF").grid(row=6, column=3)
blend_entry = Entry(root, bd=1)
blend_entry.grid(row=6, column=4)
blend_entry.insert(10, "12000")
#Start button
Button(root, text="Start", command=launch).grid(row=7, column=1, columnspan=2)
Checkbutton(root, text="Video feedback", bg="#FFFFFF", command=toggle_show, variable=show).grid(row=7, column=3)

root.mainloop()
