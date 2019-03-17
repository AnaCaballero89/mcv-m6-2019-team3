import cv2
from matplotlib import pyplot as plt
import numpy as np
import matplotlib.patches as mpatches
import motmetrics as mm

from utils.track import Track
from utils.detection import Detection
from evaluation.bbox_iou import bbox_iou


def obtain_new_tracks(tracks, unused_detections, max_track, frame_tracks):
    for detection in unused_detections:
        tracks.append(Track(max_track+1, [detection], 0, 1, 1))
        frame_tracks[max_track+1] = detection.bbox

        max_track += 1

    return tracks, max_track, frame_tracks


def predict_position(image, track):
    width = 0
    height = 0
    xtl_new = 0
    ytl_new = 0
    time = track.time_since_update + 1
    for n, detection in enumerate(track.detections):
        width += detection.bbox[2] - detection.bbox[0]
        height += detection.bbox[3] - detection.bbox[1]
        if n>0:
            xtl_new += detection.bbox[0] - track.detections[n - 1].bbox[0]
            ytl_new += detection.bbox[1] - track.detections[n - 1].bbox[1]

    width = width/len(track.detections)
    height = height/len(track.detections)
    xtl_new = track.detections[-1].bbox[0] + time*xtl_new/len(track.detections)
    ytl_new = track.detections[-1].bbox[1] + time*ytl_new / len(track.detections)

    next_detection_bbox = [xtl_new, ytl_new, xtl_new + width, ytl_new + height]

    # if track.detections[-1].label == 'bike':
    #     fig, ax = plt.subplots()
    #     ax.imshow(image, cmap='gray')
    #     minc, minr, maxc, maxr = next_detection_bbox
    #     rect = mpatches.Rectangle((minc, minr), maxc - minc + 1, maxr - minr + 1, fill=False, edgecolor='red',
    #                                   linewidth=2)
    #     ax.add_patch(rect)
    #
    #     plt.show()

    return next_detection_bbox


def update_tracks(image, tracks, detections, frame_tracks):
    unused_detections = detections
    for track in tracks:
        if track.time_since_update < 20:
            if track.time_since_update > 0 and len(track.detections) > 1:
                last_bbox = predict_position(image, track)
            else:
                last_bbox = track.detections[-1].bbox
            match_detection = match_next_bbox(last_bbox, unused_detections)
            if match_detection is not None:
                unused_detections.remove(match_detection)
                track.detections.append(match_detection)
                frame_tracks[track.id] = match_detection.bbox
                track.hits +=1
                if track.time_since_update == 0:
                    track.hit_streak += 1
                track.time_since_update = 0
            else:
                track.time_since_update += 1
                track.hit_streak = 0
    return tracks, unused_detections, frame_tracks


def match_next_bbox(last_bbox, unused_detections):
    highest_IoU = 0
    for detection in unused_detections:
        IoU = bbox_iou(last_bbox, detection.bbox)
        if IoU > highest_IoU:
            highest_IoU = IoU
            best_match = detection

    if highest_IoU > 0:
        return best_match
    else:
        return None


def visualize_tracks(image, frame_tracks, colors):
    fig, ax = plt.subplots()
    ax.imshow(image, cmap='gray')

    for id in frame_tracks.keys():
        bbox = frame_tracks[id]
        minc, minr, maxc, maxr = bbox
        rect = mpatches.Rectangle((minc, minr), maxc - minc + 1, maxr - minr + 1, fill=False, edgecolor=colors[id],
                                  linewidth=2)
        ax.add_patch(rect)

    plt.show()


def track_objects(video_path, detections_list, display = False):
    colors = np.random.rand(500, 3)  # used only for display
    tracks = []
    max_track = 0

    capture = cv2.VideoCapture(video_path)
    n_frame = 0

    while capture.isOpened():
        valid, image = capture.read()
        if not valid:
            break
        frame_tracks = {}

        detections_on_frame = [x for x in detections_list if x.frame == n_frame]
        detections_bboxes = [o.bbox for o in detections_on_frame]

        tracks, unused_detections, frame_tracks = update_tracks(image, tracks, detections_on_frame, frame_tracks)
        tracks, max_track, frame_tracks = obtain_new_tracks(tracks, unused_detections, max_track, frame_tracks)

        if display and n_frame%10==0:
            visualize_tracks(image, frame_tracks, colors)

        n_frame += 1
    capture.release()
    cv2.destroyAllWindows()

    return tracks
