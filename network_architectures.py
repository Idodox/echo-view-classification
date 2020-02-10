import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class TestNetwork(nn.Module):
    def __init__(self):  # layers are defined in the class constructor as object attributes
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=6, kernel_size=5)
        self.conv2 = nn.Conv2d(in_channels=6, out_channels=12, kernel_size=5)

        self.fc1 = nn.Linear(in_features=12 * 22 * 22, out_features=200)
        self.fc2 = nn.Linear(in_features=200, out_features=60)
        self.out = nn.Linear(in_features=60, out_features=3)

    def forward(self, t):  # Forward transformation the network performs on tensors
        # (1) input layer
        t = t

        # (2) hidden conv layer
        t = self.conv1(t)
        t = F.relu(t)
        t = F.max_pool2d(t, kernel_size=2, stride=2)
        # (3) hidden conv layer
        t = self.conv2(t)
        t = F.relu(t)
        t = F.max_pool2d(t, kernel_size=2, stride=2)

        # (4) hidden linear layer
        t = t.reshape(-1, 12 * 22 * 22)
        t = self.fc1(t)
        t = F.relu(t)

        # (5) hidden linear layer
        t = self.fc2(t)
        t = F.relu(t)

        # (6) output layer
        t = self.out(t)
        # t = F.softmax(t, dim=1)

        return t


class Unit(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()

        self.conv = nn.Conv2d(in_channels=in_channels, kernel_size=3, out_channels=out_channels, stride=1, padding=1)
        self.bn = nn.BatchNorm2d(num_features=out_channels)
        self.relu = nn.ReLU()

    def forward(self, input):
        output = self.conv(input)
        output = self.bn(output)
        output = self.relu(output)

        return output


class SimpleNet(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()

        # Create 14 layers of the unit with max pooling in between
        self.unit1 = Unit(in_channels=1, out_channels=32)
        self.unit2 = Unit(in_channels=32, out_channels=32)
        self.unit3 = Unit(in_channels=32, out_channels=32)

        self.pool1 = nn.MaxPool2d(kernel_size=2)

        self.unit4 = Unit(in_channels=32, out_channels=64)
        self.unit5 = Unit(in_channels=64, out_channels=64)
        self.unit6 = Unit(in_channels=64, out_channels=64)
        self.unit7 = Unit(in_channels=64, out_channels=64)

        self.pool2 = nn.MaxPool2d(kernel_size=2)

        self.unit8 = Unit(in_channels=64, out_channels=128)
        self.unit9 = Unit(in_channels=128, out_channels=128)
        self.unit10 = Unit(in_channels=128, out_channels=128)
        self.unit11 = Unit(in_channels=128, out_channels=128)

        self.pool3 = nn.MaxPool2d(kernel_size=2)

        self.unit12 = Unit(in_channels=128, out_channels=128)
        self.unit13 = Unit(in_channels=128, out_channels=128)
        self.unit14 = Unit(in_channels=128, out_channels=128)

        self.avgpool = nn.AvgPool2d(kernel_size=4)

        # Add all the units into the Sequential layer in exact order
        self.net = nn.Sequential(self.unit1, self.unit2, self.unit3, self.pool1, self.unit4, self.unit5, self.unit6
                                 , self.unit7, self.pool2, self.unit8, self.unit9, self.unit10, self.unit11, self.pool3,
                                 self.unit12, self.unit13, self.unit14, self.avgpool)

        self.fc = nn.Linear(in_features=128, out_features=num_classes)

    def forward(self, input):
        output = self.net(input)
        output = output.view(-1, 128)
        output = self.fc(output)
        return output



class cnn_3d_1(nn.Module):
    def __init__(self):
        super().__init__()
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

        # channels is 1 because we are using grayscale images
        self.conv1 = nn.Conv3d(in_channels = 1, out_channels = 16, kernel_size = 3)
        self.bn1 = nn.BatchNorm3d(num_features = 16)
        self.conv2 = nn.Conv3d(in_channels = 16, out_channels = 16, kernel_size = 3)
        self.bn2 = nn.BatchNorm3d(num_features = 16)
        self.conv3 = nn.Conv3d(in_channels = 16, out_channels = 16, kernel_size = 3)
        self.bn3 = nn.BatchNorm3d(num_features = 16)
        self.maxpool1 = nn.MaxPool3d(2)
        # self.conv4 = nn.Conv3d(in_channels = 32, out_channels = 64, kernel_size = 3)
        # self.bn4 = nn.BatchNorm3d(num_features = 64)
        # self.conv5 = nn.Conv3d(in_channels = 64, out_channels = 64, kernel_size = 3)
        # self.bn5 = nn.BatchNorm3d(num_features = 64)
        # self.conv6 = nn.Conv3d(in_channels = 64, out_channels = 64, kernel_size = 3)
        # self.bn6 = nn.BatchNorm3d(num_features = 64)
        # self.maxpool2 = nn.MaxPool3d(2)
        # self.conv3 = nn.conv3d(in_channels = 1, out_channels = 1, kernel_size = 3)

        # input_dims = self.calc_input_dims(10, 10)

        self.fc1 = nn.Linear(in_features= 16 * 2 * 47 * 47, out_features=1000)
        self.fc2 = nn.Linear(in_features= 1000, out_features=200)
        self.out = nn.Linear(in_features=200, out_features=3)

        self.to(self.device)

    def calc_input_dims(self, batch_size, n_frames):
        # we don't care about result just shape so won't include activations and BN layers
        batch_data = torch.zeros((batch_size, 1, n_frames, 100, 100))
        batch_data = self.conv1(batch_data)
        batch_data = self.conv2(batch_data)
        batch_data = self.conv3(batch_data)
        batch_data = self.maxpool1(batch_data)
        # batch_data = self.conv4(batch_data)
        # batch_data = self.conv5(batch_data)
        # batch_data = self.conv6(batch_data)
        # batch_data = self.maxpool2(batch_data)
        # N elements in batch_size of 1 (batch of image sets)
        return int(np.prod(batch_data.size()))



    def forward(self, t):  # Forward transformation the network performs on tensors
        torch.tensor(t).to(self.device)

        # convert from ByteTensor (uint8) to float so we can run on CPU:
        t = t.float()


        self.conv1 = nn.Conv3d(in_channels = 1, out_channels = 16, kernel_size = 3)
        self.bn1 = nn.BatchNorm3d(num_features = 16)
        self.conv2 = nn.Conv3d(in_channels = 16, out_channels = 16, kernel_size = 3)
        self.bn2 = nn.BatchNorm3d(num_features = 16)
        self.conv3 = nn.Conv3d(in_channels = 16, out_channels = 16, kernel_size = 3)
        self.bn3 = nn.BatchNorm3d(num_features = 16)
        self.maxpool1 = nn.MaxPool3d(2)
        # self.conv4 = nn.Conv3d(in_channels = 32, out_channels = 64, kernel_size = 3)
        # self.bn4 = nn.BatchNorm3d(num_features = 64)
        # self.conv5 = nn.Conv3d(in_channels = 64, out_channels = 64, kernel_size = 3)
        # self.bn5 = nn.BatchNorm3d(num_features = 64)
        # self.conv6 = nn.Conv3d(in_channels = 64, out_channels = 64, kernel_size = 3)
        # self.bn6 = nn.BatchNorm3d(num_features = 64)
        # self.maxpool2 = nn.MaxPool3d(2)


        t = self.conv1(t)
        t = self.bn1(t)
        t = F.relu(t)

        t = self.conv2(t)
        t = self.bn2(t)
        t = F.relu(t)

        t = self.conv3(t)
        t = self.bn3(t)
        t = F.relu(t)

        t = self.maxpool1(t)

        # t = self.conv4(t)
        # t = self.bn4(t)
        # t = F.relu(t)
        #
        # t = self.conv5(t)
        # t = self.bn5(t)
        # t = F.relu(t)
        #
        # t = self.conv6(t)
        # t = self.bn6(t)
        # t = F.relu(t)
        #
        # t = self.maxpool2(t)

        t = t.reshape(-1, 16*2*47*47) # N_features * N_frames * height * width
        t = self.fc1(t)
        t = F.relu(t)

        t = self.fc2(t)
        t = F.relu(t)

        # output layer
        t = self.out(t)
        t = F.softmax(t, dim=1)

        return t