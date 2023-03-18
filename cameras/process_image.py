import cv2
import mediapipe as mp
import matplotlib.pyplot as plt
import time
import os

mp_pose = mp.solutions.pose

def detect_pose(image, pose, draw = False, display = False):
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


def draw_figure(image):
    # For images
    image_pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5, min_tracking_confidence = 0.5)

    # For videos
    video_pose = mp_pose.Pose(static_image_mode = True, min_detection_confidence = 0.6, min_tracking_confidence = 0.6)

    # Drawing tools

    output, log = detect_pose(image, video_pose, draw=True, display=False)
    return output, log