import torch
from torch import nn
from torch import optim

import os
import cv2
import numpy as np

import util.visda_helper as visda

class Namespace:
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)
	def print_dict(self):
		for key, val in sorted(self.__dict__.items()):
			print("{}:\t{}".format(key, val))
	def dict(self):
		return self.__dict__

def poly_lr_scheduler(optimizer, init_lr, it, lr_decay_iter=1, max_iter=100, power=0.9):
	if it % lr_decay_iter or it > max_iter:
		return optimizer

	lr = init_lr*(1 - it/max_iter)**power
	for param_group in optimizer.param_groups:
		param_group['lr'] = lr

def reverse_img_norm(image):
	image = image.transpose(1, 2, 0)
	image *= visda.img_stdev
	image += visda.img_mean
	image = image.astype(np.uint8)
	return image

def recolor(lbl):
	out = np.zeros((lbl.shape[0], lbl.shape[1], 3))
	for label in visda.labels:
		out[lbl==label.trainId] = label.color
	return out

def save_set(src, gt, pred, pred_crf, num, path):
	if src is not None:
		save_img(src, "src", num, path, is_lbl=False)
	if gt is not None:
		save_img(gt, "gt", num, path, is_lbl=True)
	if pred is not None:
		save_img(pred, "pred", num, path, is_lbl=True)
	if pred_crf is not None:
		save_img(pred_crf, "predcrf", num, path, is_lbl=True)

def save_img(img, name, num, out_path, is_lbl=False):
	fn = "{}_{}.png".format(num, name)
	path = os.path.join(out_path, fn)
	if is_lbl: img = recolor(img)
	cv2.imwrite(path, img)
