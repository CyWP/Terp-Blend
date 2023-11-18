import tensorflow as tf
import numpy as np
import cv2
import time
from pythonosc.udp_client import SimpleUDPClient
'''This file includes everything that has to do with generating pose data from input
(video or webcam) and sending appropriately formatted output to a shared memory buffer.'''
#Global Variables

def launchmvnet(webcam, webindex, vidpath, wekosc, blendosc, wait, duration, show):
#Load Model
    interpreter = tf.lite.Interpreter(model_path='lite-model_movenet_singlepose_lightning_3.tflite')
    interpreter.allocate_tensors()
    ip="127.0.0.1"
    wekclient = SimpleUDPClient(ip, wekosc)
    blendclient = SimpleUDPClient(ip, blendosc)
    #Capture video
    if webcam:
        try:
            cap = cv2.VideoCapture(webindex)
        except:
            cap = cv2.VideoCapture(0)
        camtimer(wait, cap)
    else:
        cap = cv2.VideoCapture(vidpath)
    start = time.time()
    while cap.isOpened():
        ret, frame = cap.read()
        # Reshape image
        img = frame.copy()
        img = tf.image.resize_with_pad(np.expand_dims(img, axis=0), 192,192)
        input_image = tf.cast(img, dtype=tf.float32)
        # Setup input and output 
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        # Make predictions 
        interpreter.set_tensor(input_details[0]['index'], np.array(input_image))
        interpreter.invoke()
        keypoints_with_scores = interpreter.get_tensor(output_details[0]['index'])
        #Send to wekinator
        out = format_tensor(keypoints_with_scores)
        #blendclient.send_message("/vector", extract_direction(out))
        wekclient.send_message("/wek/inputs", out)
        #FRAMES += 1
        # Rendering 
        if show:
            draw_connections(frame, keypoints_with_scores, EDGES, 0.2)
            draw_keypoints(frame, keypoints_with_scores, 0.2)
            cv2.imshow('Press q to quit', frame)
        #Press q to exit
        if cv2.waitKey(10) & 0xFF==ord('q') or (webcam and time.time()-start>=duration):
            break           
    cap.release()
    cv2.destroyAllWindows()

def draw_keypoints(frame, keypoints, confidence_threshold):
    y, x, c = frame.shape
    shaped = np.squeeze(np.multiply(keypoints, [y,x,1]))       
    for kp in shaped:
        ky, kx, kp_conf = kp
        if kp_conf > confidence_threshold:
            cv2.circle(frame, (int(kx), int(ky)), 4, (0,255,0), -1) 

def draw_connections(frame, keypoints, edges, confidence_threshold):
    y, x, c = frame.shape
    shaped = np.squeeze(np.multiply(keypoints, [y, x, 1]))
    
    for edge, color in edges.items():
        p1, p2, col= edge
        y1, x1, c1 = shaped[p1]
        y2, x2, c2 = shaped[p2]
        
        if (c1 > confidence_threshold) & (c2 > confidence_threshold):      
            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), col, 2)

#Implement later
def format_tensor(keypoints):
   return np.asarray(np.delete(keypoints[0], np.s_[::3], None), dtype=float)

'''def pose_to_vector(keypoints):
    frame = (FRAMES+1)%BUF_SIZE
    facing = 1
    if keypoints[lefthand][0]<keypoints[righthand][0]:
        facing = -1
    for i in range(len(extremities)):
        extr_buffer[i] = np.ndarray([keypoints[extremities[i]]])'''

def camtimer(wait, cap):
    start = time.time()
    last = time.time()
    font = cv2.FONT_HERSHEY_SIMPLEX
    color = (0, 0, 255)
    while last-start<wait:
        last = time.time()
        num = int(last-start+1)
        ret, frame = cap.read()
        prompt = f"Video starts in {wait- num}"
        cv2.putText(frame, prompt, (50, 50), font, 1, color, 2, cv2.LINE_4) 
        cv2.imshow('Press q to quit', frame)
        if cv2.waitKey(10) & 0xFF==ord('q'):
            return

#Draw Edges, just the indices in the keypoints tensor at dim=2 that should connect
EDGES = {
    (0, 1, (0, 255, 0)): 'm',
    (0, 2, (0, 0, 255)): 'c',
    (1, 3, (0, 0, 255)): 'm',
    (2, 4, (0, 0, 255)): 'c',
    (0, 5, (0, 0, 255)): 'm',
    (0, 6, (0, 0, 255)): 'c',
    (5, 7, (0, 255, 0)): 'm', #left bicep
    (7, 9,(0, 125, 0)): 'm', #left forearm
    (6, 8, (255, 0, 0)): 'c', #right biecep
    (8, 10, (125, 0, 0)): 'c', #right forearm
    (5, 6, (255, 255, 255)): 'y', #collarbone
    (5, 11, (0, 0, 255)): 'm',
    (6, 12, (0, 0, 255)): 'c',
    (11, 12, (255, 255, 255)): 'y', #hips
    (11, 13, (0, 255, 255)): 'm', #left thigh
    (13, 15,(0, 125, 125)): 'm', #left tibia
    (12, 14, (255, 0, 255)): 'c', #right thigh
    (14, 16, (125, 0, 125)): 'c' #right tibia
    }

'''#index mapping as global var
leftshoulder= 5
rightshoulder= 6
lefthand= 9
righthand= 10
lefthip= 11
righthip= 12
leftfoot= 15
rightfoot= 16
extremities = [lefthand, righthand, leftfoot, rightfoot]
core = [leftshoulder, rightshoulder, lefthip, righthip]
BUF_SIZE = 5
extr_buffer = np.zeros((len(extremities), BUF_SIZE, 3), dtype=float)
FRAMES = 0'''



#these are for testing, don't uncomment
#launchmvnet(True, "test.mp4", 6448, 8449, 5, 10, True)
#launchmvnet(False, "test.mp4", 6448, 8449, 5, 10, True)