import os
import glob
import numpy as np
import torch
import cv2
from torch.utils import data

import multiprocessing as mp
PROCESSORS = 8

root_dir = "/media/data/train"


class EagerVisDaDataset(data.Dataset):

	num_classes = 35
	ignore_labels = [0, 1, 2, 3]

	shape = (1052, 1914)

	img_mean = np.array([108.56263368194266, 111.92560322135374, 113.01417537462997])
	img_stdev = 60

	labels = [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (20, 20, 20), (111, 74, 0), (81, 0, 81), (128, 64, 128),
	          (244, 35, 232), (250, 170, 160), (230, 150, 140), (70, 70, 70), (102, 102, 156), (190, 153, 153),
	          (180, 165, 180), (150, 100, 100), (150, 120, 90), (153, 153, 153), (153, 153, 153), (250, 170, 30),
	          (220, 220, 0), (107, 142, 35), (152, 251, 152), (70, 130, 180), (220, 20, 60), (255, 0, 0), (0, 0, 142),
	          (0, 0, 70), (0, 60, 100), (0, 0, 90), (0, 0, 110), (0, 80, 100), (0, 0, 230), (119, 11, 32), (0, 0, 142)]

	names = ['unlabeled', 'ego vehicle', 'rectification border', 'out of roi', 'static', 'dynamic', 'ground', 'road',
	         'sidewalk', 'parking', 'rail track', 'building', 'wall', 'fence', 'guard rail', 'bridge', 'tunnel',
	         'pole', 'polegroup', 'traffic light', 'traffic sign', 'vegetation', 'terrain', 'sky', 'person', 'rider',
	         'car', 'truck', 'bus', 'caravan', 'trailer', 'train', 'motorcycle', 'bicycle', 'license plate']

	class_weights = torch.FloatTensor([0.471072493982, 0.0, 0.0, 0.0, 0.00181448729946, 0.0, 0.00267729106253, 0.324546718887,
			0.0, 0.0, 0.0, 0.167350940922, 0.0, 0.0, 0.000255553958685, 0.0, 0.0, 0.0, 0.0106366173936,
			0.0, 0.0, 0.0, 0.0216458964943, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

	def __init__(self, im_size=shape, mode="train"):
		if mode == "train":
			self.image_fnlist = glob.glob(os.path.join(root_dir, "images", "*.png"))
			self.label_fnlist = [fn.replace("images", "annotations") for fn in self.image_fnlist]
		else:
			self.image_fnlist = glob.glob(os.path.join(root_dir, "eval", "images", "*.png"))
			self.label_fnlist = [fn.replace("images", "annotations") for fn in self.image_fnlist]

		self.size = len(self.image_fnlist)
		self.img_size = im_size
		self.shape = im_size

		pool = mp.Pool(PROCESSORS)
		self.data = pool.starmap(load_img, zip(image_fnlist, label_fnlist))

	def load_img(self, img_fn, lbl_fn):

		img = cv2.imread(img_fn)
		lbl = cv2.imread(lbl_fn)

		if (img.shape[0] != lbl.shape[0] or img.shape[1] != lbl.shape[1]):
			return self.__getitem__(index+1)

		if (lbl.shape != self.shape):
			size = (self.shape[1], self.shape[0])
			img = cv2.resize(img, size, cv2.INTER_LINEAR)
			lbl = cv2.resize(lbl, size, cv2.INTER_NEAREST)

		lbl = self.transform_labels(lbl)

		img = img - self.img_mean
		img /= self.img_stdev

		img = torch.from_numpy(img).permute(2, 0, 1).type(torch.FloatTensor)
		lbl = torch.from_numpy(lbl).type(torch.LongTensor)

		return (img, lbl)

	def __getitem__(self, index):
		return self.data[index]

	def __len__(self):
		return self.size

	def transform_labels(self, lbl):
		out = np.zeros((lbl.shape[0], lbl.shape[1]))
		for i, col in enumerate(self.labels):
			if i in self.ignore_labels: continue
			out[np.where(np.all(lbl == col, axis=-1))] = i
		return out