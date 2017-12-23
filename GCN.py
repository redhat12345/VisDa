import torch
import torch.nn.functional as F
from torch import nn
from torchvision import models
import os

res152_path = os.path.join(root, 'ResNet', 'resnet152-b121ed2d.pth')

class _GlobalConvModule(nn.Module):
	def __init__(self, in_dim, out_dim, kernel_size):
		super(_GlobalConvModule, self).__init__()
		pad0 = (kernel_size[0] - 1) / 2
		pad1 = (kernel_size[1] - 1) / 2
		# kernel size had better be odd number so as to avoid alignment error
		super(_GlobalConvModule, self).__init__()
		self.conv_l1 = nn.Conv2d(in_dim, out_dim, kernel_size=(kernel_size[0], 1), padding=(pad0, 0))
		self.conv_l2 = nn.Conv2d(out_dim, out_dim, kernel_size=(1, kernel_size[1]), padding=(0, pad1))
		self.conv_r1 = nn.Conv2d(in_dim, out_dim, kernel_size=(1, kernel_size[1]), padding=(0, pad1))
		self.conv_r2 = nn.Conv2d(out_dim, out_dim, kernel_size=(kernel_size[0], 1), padding=(pad0, 0))

	def forward(self, x):
		x_l = self.conv_l1(x)
		x_l = self.conv_l2(x_l)
		x_r = self.conv_r1(x)
		x_r = self.conv_r2(x_r)
		x = x_l + x_r
		return x


class _BoundaryRefineModule(nn.Module):
	def __init__(self, dim):
		super(_BoundaryRefineModule, self).__init__()
		self.relu = nn.ReLU(inplace=True)
		self.conv1 = nn.Conv2d(dim, dim, kernel_size=3, padding=1)
		self.conv2 = nn.Conv2d(dim, dim, kernel_size=3, padding=1)

	def forward(self, x):
		residual = self.conv1(x)
		residual = self.relu(residual)
		residual = self.conv2(residual)
		out = x + residual
		return out


class GCN(nn.Module):
	def __init__(self, num_classes, input_size, pretrained=True):
		super(GCN, self).__init__()
		self.input_size = input_size
		resnet = models.resnet152()
		if pretrained:
			resnet.load_state_dict(torch.load(res152_path))
		self.layer0 = nn.Sequential(resnet.conv1, resnet.bn1, resnet.relu)
		self.layer1 = nn.Sequential(resnet.maxpool, resnet.layer1)
		self.layer2 = resnet.layer2
		self.layer3 = resnet.layer3
		self.layer4 = resnet.layer4

		self.gcm1 = _GlobalConvModule(2048, num_classes, (7, 7))
		self.gcm2 = _GlobalConvModule(1024, num_classes, (7, 7))
		self.gcm3 = _GlobalConvModule(512, num_classes, (7, 7))
		self.gcm4 = _GlobalConvModule(256, num_classes, (7, 7))

		self.brm1 = _BoundaryRefineModule(num_classes)
		self.brm2 = _BoundaryRefineModule(num_classes)
		self.brm3 = _BoundaryRefineModule(num_classes)
		self.brm4 = _BoundaryRefineModule(num_classes)
		self.brm5 = _BoundaryRefineModule(num_classes)
		self.brm6 = _BoundaryRefineModule(num_classes)
		self.brm7 = _BoundaryRefineModule(num_classes)
		self.brm8 = _BoundaryRefineModule(num_classes)
		self.brm9 = _BoundaryRefineModule(num_classes)

		initialize_weights(self.gcm1, self.gcm2, self.gcm3, self.gcm4, self.brm1, self.brm2, self.brm3,
							self.brm4, self.brm5, self.brm6, self.brm7, self.brm8, self.brm9)

	def forward(self, x):

		fm0 = self.layer0(x)
		fm1 = self.layer1(fm0)
		fm2 = self.layer2(fm1)
		fm3 = self.layer3(fm2)
		fm4 = self.layer4(fm3)

		gcfm1 = self.brm1(self.gcm1(fm4))
		gcfm2 = self.brm2(self.gcm2(fm3))
		gcfm3 = self.brm3(self.gcm3(fm2))
		gcfm4 = self.brm4(self.gcm4(fm1))

		fs1 = self.brm5(F.upsample_bilinear(gcfm1, fm3.size()[2:]) + gcfm2)
		fs2 = self.brm6(F.upsample_bilinear(fs1, fm2.size()[2:]) + gcfm3)
		fs3 = self.brm7(F.upsample_bilinear(fs2, fm1.size()[2:]) + gcfm4)
		fs4 = self.brm8(F.upsample_bilinear(fs3, fm0.size()[2:]))
		out = self.brm9(F.upsample_bilinear(fs4, self.input_size))

		return out


def initialize_weights(*models):
	for model in models:
		for module in model.modules():
			if isinstance(module, nn.Conv2d) or isinstance(module, nn.Linear):
				nn.init.kaiming_normal(module.weight)
				if module.bias is not None:
					module.bias.data.zero_()
			elif isinstance(module, nn.BatchNorm2d):
				module.weight.data.fill_(1)
				module.bias.data.zero_()