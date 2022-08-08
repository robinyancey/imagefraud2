# -*- coding: utf-8 -*-
"""SyntheticImageFraudYOLO.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/13-eX6amLXSNe9O7UAUwkhrLp3nIlJTfE

# Now that Ive applied for industry jobs, I know how important it is to write code as presentable/reusable to link to my resume. 
- Not sure why I never used to think people would care about this.


---


# This file will contain the code for Image Fraud Detection via my modified YOLO-based method (including data preprocessing, pre-training, finetuning, etc.)

### Imports
"""

import cv2
import re
import yaml
import numpy as np
import matplotlib.pyplot as plt
import zipfile
import glob
import random
import os
import torch
import tensorflow as tf
from torchvision.io import read_image
import torchvision.transforms.functional as F
import torchvision.transforms as T
from torchvision.ops import masks_to_boxes
from random import randint

"""## Unzip/extract 'masks.zip' and 'images.zip' (uploaded as 2 separate zip files)"""

# path where images and masks zip folders are located 
root = '/content/'

with zipfile.ZipFile(root +'masks.zip' , 'r') as zip_ref:
  zip_ref.extractall(root)
with zipfile.ZipFile(root + 'images.zip' , 'r') as zip_ref:
  zip_ref.extractall(root)

"""## Notes/TODO:

### may need to try resizing via padding only to avoid adding additional "tampering" or artifacts
### can also use larger squares as input to YOLO

## Create Labeled Train/Val/Test Sets in Proper File Structure (from Masks for specific IF DB)
"""

# YOLO requires images to be squares 
# choose appropriate side length
im_size = 416
# COVERAGE is a very small DB
val_size = test_size = 15
DB = 'coverage'

# create file structures:
# train 
os.mkdir(root + 'train')
os.mkdir(root + 'train/' + 'labels')
os.mkdir(root + 'train/' + 'images')
# test
os.mkdir(root + 'test')
os.mkdir(root + 'test/' + 'labels')
os.mkdir(root + 'test/' + 'images')
# valid
os.mkdir(root + 'valid')
os.mkdir(root + 'valid/' + 'labels')
os.mkdir(root + 'valid/' + 'images')

"""## TODO:
- add more images (eg. background is different for each added)
- rotate masks pasted
- move around masks pasted
- add Pascal Voc images (download masks)
- add COCO images (download masks)
"""

# image fraud DBs only include masks (no BBs) so this function extracts BBs
# from masks to create the labels while placing ims and labels in proper YOLO
# file structures (for each train/val/test set)

def createLabeledSyntheticSets(root, DB, test_size, val_size, im_size):


  # to start add ims/labels to test subset (make sure ims not ordered in any way)
  subset = 'test'
  # get all mask names in a list
  masks = list(os.listdir(os.path.join(root, 'masks')))
  # get all images in a list (these will be )
  images = list(os.listdir(os.path.join(root, 'images')))

  # iterate through each mask 
  for i in range(len(masks)):
    if DB == 'coverage':
      # this time include all interations since each mask can just be associated with a new synthetic image

      # remove forgery type info from image number so it matches with the corresponding image
      # for COVERAGE dataset matching numbers in names mean corresponding image/mask pair
      auth_name = re.sub("[^0-9]", "", masks[i])
      tamp_name = auth_name + 't'

      if masks[i] != auth_name + 'paste.jpeg':
        continue

    for rotate in range(4):
      # read in image to extract masked region
      im = cv2.imread(os.path.join(root, "images", tamp_name + '.jpeg'))
      # read corresponding mask
      mask = cv2.imread(os.path.join(root, "masks", masks[i]))

      # randomly rotate the synthetically tampered object
      # by rotating both the mask and the tamped image its extracted from 
      #rotate = randint(0,3)
      if rotate == 0:
        rotate = cv2.ROTATE_90_CLOCKWISE
      elif rotate == 1:
        rotate = cv2.ROTATE_90_COUNTERCLOCKWISE
      elif rotate == 2:
        rotate = cv2.ROTATE_180
      else:
        mask = cv2.rotate(mask, cv2.ROTATE_180)
        im = cv2.rotate(im, cv2.ROTATE_180)
        rotate = cv2.ROTATE_180
      
      # get BBs from mask
      # first rotate and resize
      mask = cv2.rotate(mask, rotate)
      mask = cv2.resize(mask, (im_size,im_size))
      gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      thresh = cv2.threshold(gray,180,255,cv2.THRESH_BINARY)[1]
      cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      cnts = cnts[0] if len(cnts) == 2 else cnts[1]
      for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        if len(cnts) > 1:
          
          x,y,w,h = cv2.boundingRect(c)
          print(masks[i], c, x,y,w,h)
        

      # YOLO requires coordinates in x,y center, x,y height/width
      b_center_x = x + (w // 2) 
      b_center_y = y + (h // 2)
      # YOLO requires normalization of coordinates      
      b_center_x /= im_size
      b_center_y /= im_size 
      w /= im_size 
      h /= im_size
      
      if i <= val_size:
        subset = 'valid'
      elif test_size + val_size >= i > val_size:
        subset = 'test' 
      else:
        subset = 'train'


      # rotate and resize image
      im = cv2.rotate(im, rotate)
      im = cv2.resize(im, (im_size,im_size))
      

      # read in image to paste extracted masked region onto
      # choose random other image in DB:
      num = randint(0,len(images)-1)
      # make sure to not paste on tampered image
      im2_name = re.sub("[^0-9]", "", images[num])
      im2 = cv2.imread(os.path.join(root, "images", im2_name + ".jpeg")) 
      im2 = cv2.resize(im2, (im_size, im_size))
      
      # mask of im == 0 everywhere where im2 will go

      synthetic = np.where(mask == 0, im2, im)
      
      cv2.imwrite(os.path.join(root, subset, "images", tamp_name + '_' + str(num) + '_' + str(rotate) + '.jpeg'), synthetic)

      with open(os.path.join(root, subset, "labels", tamp_name + '_' + str(num) + '_' + str(rotate) + '.txt'), 'w') as f:
        f.write(str(0) + ' ' + str(b_center_x) + ' ' + str(b_center_y) + ' ' + str(w) + ' ' + str(h))

createLabeledSyntheticSets(root, DB, test_size, val_size, im_size)

# Commented out IPython magic to ensure Python compatibility.
# %%writefile /content/data.yaml
# train: /content/train/images
# val: /content/valid/images
# test: /content/test/images
# 
# 
# nc: 1
# names: ['tampered']

"""##YOLOv5"""

# Commented out IPython magic to ensure Python compatibility.
!git clone https://github.com/ultralytics/yolov5  # clone repo
# %cd yolov5
!git reset --hard 886f1c03d839575afecb059accf74296fad395b6

# install dependencies as necessary
!pip install -qr requirements.txt  # install dependencies (ignore errors)
import torch

from IPython.display import Image, clear_output  # to display images
from utils.google_utils import gdrive_download  # to download models/datasets

# clear_output()
print('Setup complete. Using torch %s %s' % (torch.__version__, torch.cuda.get_device_properties(0) if torch.cuda.is_available() else 'CPU'))

# Commented out IPython magic to ensure Python compatibility.
# %%writefile /content/yolov5/models/custom_yolov5m.yaml
# 
# # parameters
# nc: {num_classes}  # number of classes
# depth_multiple: 0.67  # model depth multiple
# width_multiple: 0.75  # layer channel multiple
# 
# # anchors
# anchors:
#   - [10,13, 16,30, 33,23]  # P3/8
#   - [30,61, 62,45, 59,119]  # P4/16
#   - [116,90, 156,198, 373,326]  # P5/32
# 
# # YOLOv5 backbone
# backbone:
#   # [from, number, module, args]
#   [[-1, 1, Focus, [64, 3]],  # 0-P1/2
#    [-1, 1, Conv, [128, 3, 2]],  # 1-P2/4
#    [-1, 3, BottleneckCSP, [128]],
#    [-1, 1, Conv, [256, 3, 2]],  # 3-P3/8
#    [-1, 9, BottleneckCSP, [256]],
#    [-1, 1, Conv, [512, 3, 2]],  # 5-P4/16
#    [-1, 9, BottleneckCSP, [512]],
#    [-1, 1, Conv, [1024, 3, 2]],  # 7-P5/32
#    [-1, 1, SPP, [1024, [5, 9, 13]]],
#    [-1, 3, BottleneckCSP, [1024, False]],  # 9
#   ]
# 
# # YOLOv5 head
# head:
#   [[-1, 1, Conv, [512, 1, 1]],
#    [-1, 1, nn.Upsample, [None, 2, 'nearest']],
#    [[-1, 6], 1, Concat, [1]],  # cat backbone P4
#    [-1, 3, BottleneckCSP, [512, False]],  # 13
# 
#    [-1, 1, Conv, [256, 1, 1]],
#    [-1, 1, nn.Upsample, [None, 2, 'nearest']],
#    [[-1, 4], 1, Concat, [1]],  # cat backbone P3
#    [-1, 3, BottleneckCSP, [256, False]],  # 17 (P3/8-small)
# 
#    [-1, 1, Conv, [256, 3, 2]],
#    [[-1, 14], 1, Concat, [1]],  # cat head P4
#    [-1, 3, BottleneckCSP, [512, False]],  # 20 (P4/16-medium)
# 
#    [-1, 1, Conv, [512, 3, 2]],
#    [[-1, 10], 1, Concat, [1]],  # cat head P5
#    [-1, 3, BottleneckCSP, [1024, False]],  # 23 (P5/32-large)
# 
#    [[17, 20, 23], 1, Detect, [nc, anchors]],  # Detect(P3, P4, P5)
#   ]

"""### had to change torch>= 1.7.0 to torch == 1.7.0 in requirements.txt (and reinstall above eg. https://github.com/ultralytics/yolov5/issues/8405) """

# Commented out IPython magic to ensure Python compatibility.
# %%time
# %cd /content/yolov5/
# !python train.py --img 416 --batch 16 --epochs 120 --data '/content/data.yaml' --cfg /content/yolov5/models/yolov5m.yaml --weights '' --name yolov5s_results  --cache

!python test.py --weights /content/yolov5/runs/train/yolov5s_results/weights/best.pt --data /content/data.yaml --img 416 --conf 0.2 --task test --save-txt

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/yolov5/
!python detect.py --weights runs/train/yolov5s_results4/weights/best.pt --img 416 --conf 0.5 --source ../test/images