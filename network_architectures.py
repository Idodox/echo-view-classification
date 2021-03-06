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
    def __init__(self, params):
        super().__init__()

        self.max_frames = params["max_frames"]
        self.resolution = params["resolution"]
        self.conv1_ch = params["conv1_ch"]
        self.conv1_kernel = params["conv1_kernel"]
        self.conv2_ch = params["conv2_ch"]
        self.conv2_kernel = params["conv2_kernel"]
        self.conv3_ch = params["conv3_ch"]
        self.conv3_kernel = params["conv3_kernel"]
        self.conv4_ch = params["conv4_ch"]
        self.conv4_kernel = params["conv4_kernel"]
        self.last_maxpool_kernel = params['last_maxpool_kernel']
        self.fc1_size = params["fc1_size"]
        self.dropout1_ratio = params["dropout1_ratio"]
        self.fc2_size = params["fc2_size"]
        self.dropout2_ratio = params["dropout2_ratio"]
        self.fc3_size = params["fc3_size"]
        self.dropout3_ratio = params["dropout3_ratio"]
        # self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

        self.features = nn.Sequential(
            nn.Conv3d(in_channels=1, out_channels=self.conv1_ch, kernel_size=self.conv1_kernel),
            nn.BatchNorm3d(num_features = self.conv1_ch),
            nn.Conv3d(in_channels=self.conv1_ch, out_channels=self.conv2_ch, kernel_size=self.conv2_kernel),
            nn.BatchNorm3d(num_features=self.conv2_ch),
            nn.Conv3d(in_channels=self.conv2_ch, out_channels=self.conv3_ch, kernel_size=self.conv3_kernel),
            nn.BatchNorm3d(num_features=self.conv3_ch),
            nn.Conv3d(in_channels=self.conv3_ch, out_channels=self.conv4_ch, kernel_size=self.conv4_kernel),
            nn.BatchNorm3d(num_features=self.conv4_ch),
            nn.MaxPool3d(self.last_maxpool_kernel)
        )


        self.input_dims = self.calc_input_dims()

        self.classifier = nn.Sequential(
            nn.Linear(in_features = self.input_dims, out_features = self.fc1_size),
            nn.ReLU(),
            nn.Dropout(p= self.dropout1_ratio),
            nn.Linear(in_features = self.fc1_size, out_features= self.fc2_size),
            nn.ReLU(),
            nn.Dropout(p= self.dropout2_ratio),
            nn.Linear(in_features = self.fc2_size, out_features= self.fc3_size),
            nn.ReLU(),
            nn.Dropout(p= self.dropout3_ratio),
            nn.Linear(in_features = self.fc3_size, out_features = 3)
        )


    def calc_input_dims(self):
        # we don't care about result just shape so won't include activations and BN layers
        batch_data = torch.zeros((1, 1, self.max_frames, self.resolution, self.resolution))
        batch_data = self.features(batch_data)
        return int(np.prod(batch_data.size()))

    def forward(self, t):  # Forward transformation the network performs on tensors
        # convert from ByteTensor (uint8) to float so we can run on CPU:
        t = t.float()

        t = self.features(t)
        t = t.reshape(-1, self.input_dims) # N_features * N_frames * height * width
        t = self.classifier(t)

        # t = F.softmax(t, dim=1) # already a part of CrossEntropyLoss

        return t



class cnn_3d_2(nn.Module):
    def __init__(self, params):
        super().__init__()

        self.max_frames = params["max_frames"]
        self.resolution = params["resolution"]
        self.conv1_in_ch = params["conv1_in_ch"]
        self.conv1_out_ch = params["conv1_out_ch"]
        self.conv1_kernel = params["conv1_kernel"]
        self.bn1_n_features = params["bn1_n_features"]
        self.conv2_in_ch = params["conv2_in_ch"]
        self.conv2_out_ch = params["conv2_out_ch"]
        self.conv2_kernel = params["conv2_kernel"]
        self.bn2_n_features = params["bn2_n_features"]
        self.conv3_in_ch = params["conv3_in_ch"]
        self.conv3_out_ch = params["conv3_out_ch"]
        self.conv3_kernel = params["conv3_kernel"]
        self.bn3_n_features = params["bn3_n_features"]
        self.conv4_in_ch = params["conv4_in_ch"]
        self.conv4_out_ch = params["conv4_out_ch"]
        self.conv4_kernel = params["conv4_kernel"]
        self.bn4_n_features = params["bn4_n_features"]
        self.maxpool1_kernel = params["maxpool1_kernel"]
        self.fc1_size = params["fc1_size"]
        self.dropout1_ratio = params["dropout1_ratio"]
        self.fc2_size = params["fc2_size"]
        self.dropout2_ratio = params["dropout2_ratio"]
        self.fc3_size = params["fc3_size"]
        self.dropout3_ratio = params["dropout3_ratio"]
        # self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

        self.conv1 = nn.Conv3d(in_channels = self.conv1_in_ch, out_channels = self.conv1_out_ch, kernel_size = self.conv1_kernel)
        self.bn1 = nn.BatchNorm3d(num_features = self.bn1_n_features)
        self.conv2 = nn.Conv3d(in_channels = self.conv2_in_ch, out_channels = self.conv2_out_ch, kernel_size = self.conv2_kernel)
        self.bn2 = nn.BatchNorm3d(num_features = self.bn2_n_features)
        self.conv3 = nn.Conv3d(in_channels = self.conv3_in_ch, out_channels = self.conv3_out_ch, kernel_size = self.conv3_kernel)
        self.bn3 = nn.BatchNorm3d(num_features = self.bn3_n_features)
        self.conv4 = nn.Conv3d(in_channels = self.conv4_in_ch, out_channels = self.conv4_out_ch, kernel_size = self.conv4_kernel)
        self.bn4 = nn.BatchNorm3d(num_features = self.bn4_n_features)
        self.maxpool1 = nn.MaxPool3d(self.maxpool1_kernel)

        self.input_dims = self.calc_input_dims()

        self.fc1 = nn.Linear(in_features = self.input_dims, out_features = self.fc1_size)
        self.drop_layer1 = nn.Dropout(p= self.dropout1_ratio)
        self.fc2 = nn.Linear(in_features = self.fc1_size, out_features= self.fc2_size)
        self.drop_layer2 = nn.Dropout(p= self.dropout2_ratio)
        self.fc3 = nn.Linear(in_features = self.fc2_size, out_features= self.fc3_size)
        self.drop_layer3 = nn.Dropout(p= self.dropout3_ratio)
        self.out = nn.Linear(in_features = self.fc3_size, out_features = 3)

        # self.to(self.device)

    def calc_input_dims(self):
        # we don't care about result just shape so won't include activations and BN layers
        batch_data = torch.zeros((1, 1, self.max_frames, self.resolution, self.resolution))
        batch_data = self.conv1(batch_data)
        batch_data = self.conv2(batch_data)
        batch_data = self.conv3(batch_data)
        batch_data = self.conv4(batch_data)
        batch_data = self.maxpool1(batch_data)

        return int(np.prod(batch_data.size()))



    def forward(self, t):  # Forward transformation the network performs on tensors
        # torch.tensor(t).to(self.device)

        # convert from ByteTensor (uint8) to float so we can run on CPU:
        t = t.float()

        t = self.conv1(t)
        t = self.bn1(t)
        t = F.relu(t)

        t = self.conv2(t)
        t = self.bn2(t)
        t = F.relu(t)

        t = self.conv3(t)
        t = self.bn3(t)
        t = F.relu(t)

        t = self.conv4(t)
        t = self.bn4(t)
        t = F.relu(t)

        t = self.maxpool1(t)

        t = t.reshape(-1, self.input_dims) # N_features * N_frames * height * width

        t = self.drop_layer1(t)

        t = self.fc1(t)
        t = F.relu(t)

        t = self.drop_layer2(t)

        t = self.fc2(t)
        t = F.relu(t)

        t = self.drop_layer3(t)

        t = self.fc3(t)
        t = F.relu(t)

        # output layer
        t = self.out(t)
        # t = F.softmax(t, dim=1) # already a part of CrossEntropyLoss

        return t

