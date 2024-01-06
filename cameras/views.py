from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.conf import settings
from .models import Camera
# from .process_image import draw_figure, detect_pose, draw_bbox
from pathlib import Path
from math import ceil
import os
import cv2
import threading
from threading import Lock
from boxmot import DeepOCSORT
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import torch
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from datetime import datetime
import cv2
from collections import deque
import subprocess
import time

def send_email(track_id, image):
    try:
        # Email setup
        from_email = "hung8a1thth@gmail.com"  # Replace with your email
        to_email = "hung9a1th@gmail.com"  # Replace with recipient's email
        subject = f"Littering Alert for ID {track_id}"
        body = f"Detected littering at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for ID {track_id}."

        # Set up the MIME
        message = MIMEMultipart()
        message['From'] = from_email
        message['To'] = to_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))

        # Attach the photo
        img_data = cv2.imencode('.jpg', image)[1].tobytes()
        image_attachment = MIMEImage(img_data, name=f"track_{track_id}.jpg")
        message.attach(image_attachment)

        # Email sending
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, "crhd ypsy bzpj bqwh")  # Replace with your password or App Password
        server.sendmail(from_email, to_email, message.as_string())
        server.quit()
        print(f"Email sent for track ID {track_id}")
    except Exception as e:
        print(f"Failed to send email: {e}")


dictt = {}
age_miss_trash = {}

tracker = DeepOCSORT(
    model_weights=Path('osnet_x0_25_msmt17.pt'), # which ReID model to use
    device='cpu',
    fp16=False,
)

model = YOLO("detect_person.pt")
model_detect_trash = YOLO("model_trash/best.pt")

videos_path = settings.MEDIA_ROOT

def camerapage(request):
    return render(request=request,
                  template_name="cameras/watch.html",
                  context={"Cameras": Camera.objects.all()})


def watch(request, cam_name):
    for cam in Camera.objects.all():
        if cam.title == cam_name:
            return render(request=request,
                          template_name="cameras/watch.html",
                          context={"camera": cam, "cameras": Camera.objects.all()})
    return render(request=request,
                  template_name="home/unknown_page.html",
                  context={"cameras": Camera.objects.all()})



# Helper function to check intersection
def check_intersection(box1, box2):

    center_x2 = (box2[0] + box2[2]) / 2
    center_y2 = (box2[1] + box2[3]) / 2
    tmp = 30
    if (box1[0]-tmp) <= center_x2 <= (box1[2]+tmp) and (box1[1]-tmp) <= center_y2 <= (box1[3]+tmp):
        return True
    return False

def save_litterer_video(frames_snapshot, track_id, save_folder="camereReplay/replay1"):
    try:
        video_name = f"littering_{track_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        save_path = os.path.join(save_folder, video_name)
        # save_path_output = os.path.join(save_folder, "video"+video_name)
        # Define the codec and create VideoWriter object
        # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # fourcc = cv2.VideoWriter_fourcc(*'H264')
        fourcc = 0x00000021
        out = cv2.VideoWriter(save_path, fourcc, 20.0, (1280,720))

        for frame in frames_snapshot:
            out.write(frame)

        out.release()
        
        # subprocess.run(['ffmpeg', '-i', save_path, '-vcodec', 'libx264', save_path_output])
        print(f"Saved video for track ID {track_id} at {save_path}")
    except Exception as e:
        print(f"Failed to save video: {e}")

# def save_litterer_video(frames_snapshot, track_id, save_folder="camereReplay/replay1"):
#     try:
#         video_name = f"littering_low_bitrate_{track_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
#         save_path = os.path.join(save_folder, video_name)

#         # Lower resolution for lower bitrate
#         lower_resolution = (640, 360)  # Example: half of 1280x720

#         # Define the codec (MJPEG for more compression) and create VideoWriter object
#         fourcc = cv2.VideoWriter_fourcc(*'MJPG')
#         out = cv2.VideoWriter(save_path, fourcc, 20.0, lower_resolution)

#         for frame in frames_snapshot:
#             # Resize frame to lower resolution
#             resized_frame = cv2.resize(frame, lower_resolution)
#             out.write(resized_frame)

#         out.release()
#         print(f"Saved low-bitrate video for track ID {track_id} at {save_path}")
#     except Exception as e:
#         print(f"Failed to save video: {e}")

# Initialize dictionaries to track the state of individuals
def stream0(cam_name):
    # id = "rtsp://iocldg:iocldg123123@14.241.197.248:2006/cam/realmonitor?channel=1&subtype=0"
    id = ""
    for cam in Camera.objects.all():
        if cam.title == cam_name:
            id = cam.url
    if id[:4] == "rtsp":
        id = "2.png"
    
    cap = cv2.VideoCapture(id) 
    while True:
        ret, frame = cap.read()

        # # Image Processing
        frame = cv2.resize(frame,(1280,720))
        # Encode the frame in-memory
        ret, buffer = cv2.imencode('.jpg', frame)

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


def stream(cam_name):
    # id = "rtsp://iocldg:iocldg123123@14.241.197.248:2006/cam/realmonitor?channel=1&subtype=0"
    id = ""
    for cam in Camera.objects.all():
        if cam.title == cam_name:
            id = cam.url
    # if id[:4] == "rtsp":
    #     id = "2.png"
    if id == "0":
        id = 0

    # Fixed size queue to store the last 150 frames
    frame_queue = deque(maxlen=100)

    litter_threshold = {}
    person_states = {}  # To track the state of each person (normal, suspect, litter)
    frame_counter = 0
    previous_frame_data = []

    cap = cv2.VideoCapture(id) 
    while True:

        ret, frame = cap.read()

        if not ret:
            print("Error: failed to capture image")
            break

        # # Image Processing
        frame = cv2.resize(frame,(1280,720))
        if frame_counter % 5 == 0:
            results = model(frame, imgsz=640,  classes=0)[0]  # predict on an image
            # print("boxs:",results)

            t1 = results.boxes.xyxy
            t2 = results.boxes.conf
            t3 = results.boxes.cls

            dets = np.array(torch.cat([t1, t2.unsqueeze(1), t3.unsqueeze(1)], dim=1))

            # print("dets",dets)
            tracks = tracker.update(dets, frame) # --> (x, y, x, y, id, conf, cls, ind)

            color = (255, 255, 255)  # BGR
            thickness = 2
            fontscale = 0.5
            previous_frame_data.clear()  # Clear previous data
            # Detect trash
            results_trashs = model_detect_trash(frame)
            # print("results_trash",results_trashs)

            # for results_trash in results_trashs:
            #     bb_trashs = results_trash.boxes
            #     print("res_trash",bb_trashs.xyxy)
            #     print("res_trash",type(bb_trashs.xyxy))

            
            hung = results_trashs[0].boxes.xyxy
            # print("hung",hung)
            # trash_boxes = np.array([d[0:4] for d in hung if len(d) > 0])  # Assuming the format is [x1, y1, x2, y2, ...]
            trash_boxes = hung.numpy()
            # print("trash_boxes",trash_boxes)
            # Process each track
            for track in tracks:
                track_id = int(track[4])
                person_box = track[:4]

                # Check if this person intersects with any trash
                intersects_with_trash = any(check_intersection(person_box, trash_box) for trash_box in trash_boxes)

                print("trackid",track_id)
                # Only update state if the person is not already marked as 'littering'
                if person_states.get(track_id) != 'littering':
                    # Check if this person intersects with any trash
                    intersects_with_trash = any(check_intersection(person_box, trash_box) for trash_box in trash_boxes)

                    if intersects_with_trash:
                        person_states[track_id] = 'suspected'
                        litter_threshold[track_id] = 0
                    elif person_states.get(track_id, 'normal') == 'suspected':
                        print("trackid",track_id, "litter_threshold[track_id] ",litter_threshold[track_id] )
                        litter_threshold[track_id] += 1
                        if litter_threshold[track_id] > 5:
                            person_states[track_id] = 'littering'
                            person_image = cv2.rectangle(frame, (int(person_box[0]), int(person_box[1])), (int(person_box[2]), int(person_box[3])), (0, 0, 255), thickness)
                            threading.Thread(target=send_email, args=(track_id, person_image)).start()
                            frames_snapshot = list(frame_queue)
                            threading.Thread(target=save_litterer_video, args=(frames_snapshot,track_id,)).start()


                # Draw bounding boxes and state labels based on the state
                label = person_states.get(track_id, 'normal')
                if label == 'suspected':
                    color = (0, 255, 255)  # Yellow
                    label = 'suspected ' + str(litter_threshold[track_id])
                elif label == 'littering':
                    color = (0, 0, 255)  # Red
                    label = 'littering ' + str(litter_threshold[track_id])
                else:
                    color = (255, 255, 255)  # White for 'normal'

                cv2.rectangle(frame, (int(track[0]), int(track[1])), (int(track[2]), int(track[3])), color, thickness)
                cv2.putText(frame, f'ID {track_id} - {label}', (int(track[0]), int(track[1] - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)

                # Store the data for redrawing in next frames
                previous_frame_data.append((track_id, person_box, label, color))
        else:
            # Redraw bounding boxes and labels from the previous frame
            for track_id, person_box, label, color in previous_frame_data:
                cv2.rectangle(frame, (int(person_box[0]), int(person_box[1])), (int(person_box[2]), int(person_box[3])), color, thickness)
                cv2.putText(frame, f'ID {track_id} - {label}', (int(person_box[0]), int(person_box[1] - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)

        # Draw trash boxes
        for trash_box in trash_boxes:
            cv2.rectangle(frame, (int(trash_box[0]), int(trash_box[1])), (int(trash_box[2]), int(trash_box[3])), (0, 0, 255), thickness)


        # cv2.imshow('.jpg', frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break
        frame_queue.append(frame.copy())
        frame_counter += 1  # Increment frame counter

        # Encode the frame in-memory
        ret, buffer = cv2.imencode('.jpg', frame)

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def stream1(cam_name):
    # id = "rtsp://iocldg:iocldg123123@14.241.197.248:2006/cam/realmonitor?channel=1&subtype=0"
    id = ""
    for cam in Camera.objects.all():
        if cam.title == cam_name:
            id = cam.url
    if id[:4] == "rtsp":
        id = "2.png"
    
    i = 0
    cap = cv2.VideoCapture(id) 
    while True:
        i+=1
        
        ret, frame = cap.read()

        if not ret:
            print("Error: failed to capture image")
            break

        # # Image Processing
        frame = cv2.resize(frame,(1280,720))
        results = model(frame, save=True, imgsz=960,  classes=0)[0]  # predict on an image
        # print("boxs:",results)

        t1 = results.boxes.xyxy
        t2 = results.boxes.conf
        t3 = results.boxes.cls

        dets = np.array(torch.cat([t1, t2.unsqueeze(1), t3.unsqueeze(1)], dim=1))

        # print("dets",dets)
        tracks = tracker.update(dets, frame) # --> (x, y, x, y, id, conf, cls, ind)
        # print("tracks",tracks)
        try:
            xyxys = tracks[:, 0:4].astype('int') # float64 to int
            ids = tracks[:, 4].astype('int') # float64 to int
            confs = tracks[:, 5]
            clss = tracks[:, 6].astype('int') # float64 to int
            inds = tracks[:, 7].astype('int') # float64 to int
        except:
            pass
        # print bboxes with their associated id, cls and conf

        results_trash = model_detect_trash(frame) 

        color = (255, 255, 255)  # BGR
        thickness = 2
        fontscale = 0.5

        # people_without_delivery = list(ids)


        # # Detect litterers based on criteria (e.g., matching person and trash bounding boxes)
        # for xyxy, id, conf, cls in zip(xyxys, ids, confs, clss):
        #     if cls == 0:  # Assuming class 0 corresponds to a person
        #         person_id = id
        #         if person_id in people_without_delivery:
        #             people_without_delivery.remove(person_id)

        #         # Check if the person's bounding box matches a trash bounding box
        #         for result in results_trash[0].boxes.xyxy:
        #             trash_x1, trash_y1, trash_x2, trash_y2 = int(result[0]), int(result[1]), int(result[2]), int(result[3])
        #             if trash_x1 <= xyxy[0] <= trash_x2 and trash_y1 <= xyxy[1] <= trash_y2:
        #                 # The person's bounding box matches a trash bounding box
        #                 if person_id not in person_states:
        #                     person_states[person_id] = "suspect"
        #                 else:
        #                     person_states[person_id] = "suspect"
        #                 trash_detected[person_id] = True
        #                 break

        # # Mark people who are not delivered to any bounding box as "normal"
        # for person_id in people_without_delivery:
        #     person_states[person_id] = "normal"

        # # Mark "suspect" people who did not see trash as "litter"
        # for person_id in person_states.keys():
        #     if person_states[person_id] == "suspect" and person_id not in trash_detected:
        #         person_states[person_id] = "litter"



        if tracks.shape[0] != 0:
            for xyxy, id, conf, cls in zip(xyxys, ids, confs, clss):
                color = (255, 255, 255)  # BGR
                # if person_states[id] == "suspect":
                #     color = (0, 255, 255)  # BGR 
                # elif person_states[id] == "litter":
                #     color = (0, 0, 255)
                # else:
                #     color = (255, 255, 255)
                frame = cv2.rectangle(
                    frame,
                    (xyxy[0], xyxy[1]),
                    (xyxy[2], xyxy[3]),
                    color,
                    thickness
                )
                cv2.putText(
                    frame,
                    f'id: {id}, conf: {conf}, c: {cls}',
                    (xyxy[0], xyxy[1]-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    fontscale,
                    color,
                    thickness
                )
                
        for result in results_trash[0].boxes.xyxy:
            trash_x1, trash_y1, trash_x2, trash_y2 = int(result[0]), int(result[1]), int(result[2]), int(result[3])
            frame = cv2.rectangle(frame, (trash_x1, trash_y1), (trash_x2, trash_y2), (0, 0, 255), thickness)


        # dettect litterer



        # Encode the frame in-memory
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def video_feed(request, cam_name):
    return StreamingHttpResponse(stream(cam_name), content_type='multipart/x-mixed-replace; boundary=frame')

def replay(request,cam_name, page_number=1):
    try:
        page_number = int(page_number)
    except ValueError:
        return render(request=request,
                      template_name="home/unknown_page.html",
                      context={"cameras": Camera.objects.all()})

    class Video:
        def __init__(self, path, title):
            self.path = path
            self.title = title

        def __str__(self):
            return self.title

    class Date:
        videos = []

        def __init__(self, path, date):
            self.path = path
            self.date = date

        def __str__(self):
            return self.date

    for cam in Camera.objects.all():
        if cam.title == cam_name:
            dates = []
            exact_path = cam.path
            if "//" not in exact_path:
                exact_path = os.path.join(videos_path, cam.path)

            for dir_or_file in os.listdir(exact_path):
                date_folder_path = os.path.join(os.path.join(videos_path, cam.path), dir_or_file)
                if os.path.isdir(date_folder_path):
                    new_date = Date(date_folder_path, dir_or_file)
                    for possible_file in os.listdir(date_folder_path):
                        if str(possible_file).endswith("MJPEG.mp4"):
                            continue
                        file_path = os.path.join(date_folder_path, possible_file)
                        if os.path.isfile(file_path):
                            new_video = Video(os.path.join(dir_or_file, possible_file), possible_file.replace("-", ":"))
                            new_date.videos.append(new_video)
                    dates.append(new_date)

            dates.sort(key=lambda x: x.date, reverse=True)
            for date in dates:
                date.videos.sort(key=lambda x: x.title, reverse=True)

            page_amount = ceil(len(dates)/7)
            begin = 0 + (page_number-1)*7
            end = 7 + (page_number-1)*7
            begin_end = "{}:{}".format(begin, end)

            return render(request=request,
                          template_name="cameras/replay.html",
                          context={"dates": dates, "page_amount": page_amount, "current_page": page_number,
                                   "begin_end": begin_end, "cameras": Camera.objects.all(), "camera": cam})

    return render(request=request,
                  template_name="home/unknown_page.html",
                  context={"cameras": Camera.objects.all()})
