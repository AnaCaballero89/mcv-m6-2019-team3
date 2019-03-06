from math import ceil
from copy import deepcopy

import cv2
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

from evaluation.bbox_iou import bbox_iou


def compute_IoU(video_path, groundtruth_list, detections_list):

    capture = cv2.VideoCapture(video_path)
    n = 0; TP = 0; FN = 0; FP = 0
    IoUFrames = []
    F1_frames = []
    while capture.isOpened():
        valid, image = capture.read()
        if not valid:
            break

        # Get grountruth and detections from frame n
        gt_on_frame = [x for x in groundtruth_list if x.frame == n]
        gt_bboxes = [o.bbox for o in gt_on_frame]
        #print("groundtruth: {}".format(gt_bboxes))

        detections_on_frame = [x for x in detections_list if x.frame == n]
        detections_bboxes = [o.bbox for o in detections_on_frame]
        #print("detections: {}".format(detections_bboxes))

        TP_temp, FN_temp, FP_temp = performance_accumulation_window(detections_bboxes, gt_bboxes)
        IoU_temp = 0
        precision = 0
        recall = 0
        F1_score = 0
        if TP_temp is not 0:
            IoU_temp = float(TP_temp) / float(TP_temp+FP_temp+FN_temp)
            recall = float(TP_temp) / float(TP_temp+FP_temp)
            precision = float(TP_temp) / float(TP_temp+FN_temp)
            F1_score = 2*recall*precision / (recall+precision)

        TP += TP_temp
        FN += FN_temp
        FP += FP_temp
        IoUFrames.append([TP_temp, FN_temp, FP_temp, IoU_temp])
        F1_frames.append([F1_score, precision, recall])
        n += 1
    IoU = float(TP) / float(TP+FP+FN)
    recall = float(TP) / float(TP+FP)
    precision = float(TP) / float(TP+FN)
    F1_score = 2*recall*precision / (recall+precision)
    print("TP={} FN={} FP={}".format(TP, FN, FP))
    print("IoU={}".format(IoU))
    print("F1={}".format(F1_score))
    return IoUFrames, F1_frames


def compute_mAP(groundtruth_list_original, detections_list):

    groundtruth_list = deepcopy(groundtruth_list_original)

    # Sort detections by confidence
    detections_list.sort(key=lambda x: x.confidence, reverse=True)
    # Save number of groundtruth labels
    groundtruth_size = len(groundtruth_list)

    TP = 0; FP = 0; FN = 0
    precision = list(); recall = list()

    # to compute mAP
    max_precision_per_step = list()
    threshold = 1; checkpoint = 0
    print(groundtruth_size)
    print(len(detections_list))
    temp = 1000

    for n, detection in enumerate(detections_list):
        match_flag = False
        if threshold != temp:
            #print(threshold)
            temp = threshold

        # Get groundtruth of the target frame
        gt_on_frame = [x for x in groundtruth_list if x.frame == detection.frame]
        gt_bboxes = [(o.bbox, o.confidence) for o in gt_on_frame]

        #print(gt_bboxes)
        for gt_bbox in gt_bboxes:
            #print(gt_bbox[0])
            #print(detection.bbox)
            iou = bbox_iou(gt_bbox[0], detection.bbox)
            if iou > 0.5 and gt_bbox[1] > 0.9:
                match_flag = True
                TP += 1
                gt_used = next((x for x in groundtruth_list if x.frame == detection.frame and x.bbox == gt_bbox[0]), None)
                gt_used.confidence = 0
                break

        if match_flag == False:
            FP += 1
        match_flag = False

        # Save metrics
        precision.append(TP/(TP+FP))
        recall.append(TP/groundtruth_size)

    for n, (p, r) in enumerate(zip(reversed(precision), reversed(recall))):
        if(r < threshold or n == len(precision)-1):
            #print(n)
            #print(r)
            max_precision_per_step.append(max(precision[0:n]))
            threshold -= 0.1

    """
    groups = defaultdict(list)
    for obj in groundtruth_list:
        groups[obj.frame].append(obj)
    grouped_groundtruth_list = groups.values()

    # Check false negatives
    for groundtruth in grouped_groundtruth_list:

        detection_on_frame = [x for x in detections_list if x.frame == groundtruth[0].frame]
        detection_bboxes = [o.bbox for o in detection_on_frame]

        groundtruth_bboxes = [o.bbox for o in groundtruth]

        TP_temp, FN_temp, FP_temp = performance_accumulation_window(detection_bboxes, groundtruth_bboxes)
        #print(detection_bboxes)
        #print(groundtruth_bboxes)
        #print("TP={} FN={} FP={}".format(TP_temp, FN_temp, FP_temp))

        FP += FP_temp
        FN += FN_temp
        if (TP_temp > len(groundtruth_bboxes)):
            TP += 1
            FP += TP_temp - len(groundtruth_bboxes)
        else:
            TP += 1
    """


    print("TP={} FN={} FP={}".format(TP, FN, FP))
    print(TP+FP)
    #print("precision:{}".format(precision))
    #print("recall:{}".format(recall))
    print(max_precision_per_step)
    mAP = sum(max_precision_per_step)/11
    print("mAP: {}\n".format(mAP))
    return precision, recall

def plot_precision_recall_curve(precision, recall, title="plot"):

    # Data for plotting
    fig, ax = plt.subplots()
    ax.plot(recall, precision)

    ax.set(xlabel='Recall', ylabel='Precision',
           title='Precision-Recall Curve')
    ax.grid()

    fig.savefig("plots/precision-recall-"+ title + ".png")
    # plt.show()

# def performance_accumulation_pixel(pixel_candidates, pixel_annotation):
#     """
#     performance_accumulation_pixel()
#
#     Function to compute different performance indicators
#     (True Positive, False Positive, False Negative, True Negative)
#     at the pixel level
#
#     [pixelTP, pixelFP, pixelFN, pixelTN] = performance_accumulation_pixel(pixel_candidates, pixel_annotation)
#
#     Parameter name      Value
#     --------------      -----
#     'pixel_candidates'   Binary image marking the detected areas
#     'pixel_annotation'   Binary image containing ground truth
#
#     The function returns the number of True Positive (pixelTP), False Positive (pixelFP),
#     False Negative (pixelFN) and True Negative (pixelTN) pixels in the image pixel_candidates
#     """
#
#     pixel_candidates = np.uint64(pixel_candidates>0)
#     pixel_annotation = np.uint64(pixel_annotation>0)
#
#     pixelTP = np.sum(pixel_candidates & pixel_annotation)
#     pixelFP = np.sum(pixel_candidates & (pixel_annotation==0))
#     pixelFN = np.sum((pixel_candidates==0) & pixel_annotation)
#     pixelTN = np.sum((pixel_candidates==0) & (pixel_annotation==0))
#
#     return [pixelTP, pixelFP, pixelFN, pixelTN]


def performance_accumulation_window(detections, annotations):
    """ 
    performance_accumulation_window()

    Function to compute different performance indicators (True Positive, 
    False Positive, False Negative) at the object level.
    
    Objects are defined by means of rectangular windows circumscribing them.
    Window format is [ struct(x,y,w,h)  struct(x,y,w,h)  ... ] in both
    detections and annotations.
    
    An object is considered to be detected correctly if detection and annotation 
    windows overlap by more of 50%
    
       function [TP,FN,FP] = PerformanceAccumulationWindow(detections, annotations)
    
       Parameter name      Value
       --------------      -----
       'detections'        List of windows marking the candidate detections
       'annotations'       List of windows with the ground truth positions of the objects
    
    The function returns the number of True Positive (TP), False Positive (FP), 
    False Negative (FN) objects
    """
    
    detections_used  = np.zeros(len(detections))
    annotations_used = np.zeros(len(annotations))
    TP = 0
    for ii in range (len(annotations)):
        for jj in range (len(detections)):
            if (detections_used[jj] == 0) & (bbox_iou(annotations[ii], detections[jj]) > 0.5):
                TP = TP+1
                detections_used[jj]  = 1
                annotations_used[ii] = 1

    FN = np.sum(annotations_used==0)
    FP = np.sum(detections_used==0)

    return [TP,FN,FP]


# def performance_evaluation_pixel(pixelTP, pixelFP, pixelFN, pixelTN):
#     """
#     performance_evaluation_pixel()
#
#     Function to compute different performance indicators (Precision, accuracy,
#     specificity, sensitivity) at the pixel level
#
#     [pixelPrecision, pixelAccuracy, pixelSpecificity, pixelSensitivity] = PerformanceEvaluationPixel(pixelTP, pixelFP, pixelFN, pixelTN)
#
#        Parameter name      Value
#        --------------      -----
#        'pixelTP'           Number of True  Positive pixels
#        'pixelFP'           Number of False Positive pixels
#        'pixelFN'           Number of False Negative pixels
#        'pixelTN'           Number of True  Negative pixels
#
#     The function returns the precision, accuracy, specificity and sensitivity
#     """
#
#     pixel_precision   = float(pixelTP) / float(pixelTP+pixelFP)
#     pixel_accuracy    = float(pixelTP+pixelTN) / float(pixelTP+pixelFP+pixelFN+pixelTN)
#     pixel_specificity = float(pixelTN) / float(pixelTN+pixelFP)
#     pixel_sensitivity = float(pixelTP) / float(pixelTP+pixelFN)
#
#     return [pixel_precision, pixel_accuracy, pixel_specificity, pixel_sensitivity]


def performance_evaluation_window(TP, FN, FP):
    """
    performance_evaluation_window()

    Function to compute different performance indicators (Precision, accuracy, 
    sensitivity/recall) at the object level
    
    [precision, sensitivity, accuracy] = PerformanceEvaluationPixel(TP, FN, FP)
    
       Parameter name      Value
       --------------      -----
       'TP'                Number of True  Positive objects
       'FN'                Number of False Negative objects
       'FP'                Number of False Positive objects
    
    The function returns the precision, accuracy and sensitivity
    """
    
    precision   = float(TP) / float(TP+FP) # Q: What if i do not have TN?
    sensitivity = float(TP) / float(TP+FN)
    accuracy    = float(TP) / float(TP+FN+FP)

    return [precision, sensitivity, accuracy]

