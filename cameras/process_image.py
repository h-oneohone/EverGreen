import cv2
import mediapipe as mp
import matplotlib.pyplot as plt
import time
import os

mp_pose = mp.solutions.pose

def detect_pose(image, pose, draw = False, display = False):
    h, w, c = image.shape
    # Drawing tools
    mp_drawing = mp.solutions.drawing_utils
    copycat = image.copy()
    RGB_rendered = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = pose.process(RGB_rendered)
    if result.pose_landmarks and draw:
        mp_drawing.draw_landmarks(image = copycat,
                                 landmark_list = result.pose_landmarks,
                                 connections = mp.solutions.pose.POSE_CONNECTIONS,
                                 landmark_drawing_spec = mp_drawing.DrawingSpec(color = (255,255,255),
                                                                               thickness = 1,
                                                                               circle_radius = 1),
                                 connection_drawing_spec = mp_drawing.DrawingSpec(color = (49,125,237),
                                                                                 thickness = 1,
                                                                                 circle_radius = 1))
        
        x_max = 0
        y_max = 0
        x_min = w
        y_min = h
        if result.pose_landmarks:
            for lm in result.pose_landmarks.landmark:
                x, y = int(lm.x * w), int(lm.y * h)
                if x > x_max:
                    x_max = x
                if x < x_min:
                    x_min = x
                if y > y_max:
                    y_max = y
                if y < y_min:
                    y_min = y
            cv2.rectangle(copycat, (x_min, y_min), (x_max, y_max), (49,125,237), 10)

    if display:
        plt.figure(figsize = [22, 22])
        plt.subplot(121)
        plt.imshow(image[:, :, ::-1])
        plt.title('Input image')
        plt.axis('off')
        
        plt.subplot(122)
        plt.imshow(copycat[:, :, ::-1])
        plt.title('Detected image')
        plt.axis('off')
    else:
        return copycat, result

# Main function
def draw_figure(image):
    # For images
    image_pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5, min_tracking_confidence = 0.5)

    # For videos
    video_pose = mp_pose.Pose(static_image_mode = True, min_detection_confidence = 0.6, min_tracking_confidence = 0.6)
    
    output, log = detect_pose(image, video_pose, draw=True, display=False)
    return output, log

def reorder(x):
    x = [min(x[0], x[2]), min(x[1], x[3]), max(x[0], x[2]), max(x[1], x[3])]
    return x

def crossing_boxes(tuple1, tuple2):
    tuple1 = reorder(tuple1)
    tuple2 = reorder(tuple2)
    if tuple1[0] >= tuple2[0] and tuple1[0] <= tuple2[2]:
        if tuple1[1] >= tuple2[1] and tuple1[1] <= tuple2[3]:
            return True
    if tuple2[0] >= tuple1[0] and tuple2[0] <= tuple1[2]:
        if tuple2[1] >= tuple1[1] and tuple2[1] <= tuple1[3]:
            return True
    return False