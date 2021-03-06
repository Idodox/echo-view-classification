from torch import nn as nn
from torchvision import datasets
import pickle
import torch
import shutil
import random
from comet_ml import Experiment
from modular_cnn import ModularCNN, make_layers
from utils import get_num_correct, get_mistakes, calc_accuracy
import numpy as np
from resnext_util import generate_resnext_model
import os



class DatasetFolderWithPaths(datasets.DatasetFolder):
    """Custom dataset that includes file paths. Extends
    torchvision.datasets.DatasetFolder
    """

    # override the __getitem__ method. this is the method that dataloader calls
    def __getitem__(self, index):
        # this is what DatasetFolder normally returns
        original_tuple = super(DatasetFolderWithPaths, self).__getitem__(index)
        # data file path
        path = self.samples[index][0]
        # make a new tuple that includes original and the path
        tuple_with_path = (original_tuple + (path,))
        return tuple_with_path

class ToTensor(object):
    """Convert a ``numpy.ndarray`` to tensor.
    """

    def __call__(self, arr):
        """
        Args:
            numpy array to be converted to tensor.

        Returns:
            Tensor: Converted array.
        """
        return torch.from_numpy(arr).float()

    def __repr__(self):
        return self.__class__.__name__ + '()'

class Normalize(object):
    """Normalize a tensor image with mean and standard deviation.
    ``input[channel] = (input[channel] - mean[channel]) / std[channel]``

    .. note::
        This transform acts out of place, i.e., it does not mutates the input tensor.

    Args:
        mean (sequence): Sequence of means for each channel.
        std (sequence): Sequence of standard deviations for each channel.

    """

    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def __call__(self, tensor):
        new_tensor = tensor.clone()

        dtype = tensor.dtype
        mean = torch.as_tensor(self.mean, dtype=dtype, device=tensor.device)
        std = torch.as_tensor(self.std, dtype=dtype, device=tensor.device)
        for i, image in enumerate(tensor):
            new_tensor[i] = image.sub_(mean).div_(std)
        return new_tensor

    def __repr__(self):
        return self.__class__.__name__ + '(mean={0}, std={1})'.format(self.mean, self.std)

class UnNormalize(object):
    """UnNormalize a tensor image with mean and standard deviation.
    ``input[channel] = (input[channel] + mean[channel]) * std[channel]``

    .. note::
        This transform acts out of place, i.e., it does not mutates the input tensor.
    Args:
        mean (sequence): Sequence of means for each channel.
        std (sequence): Sequence of standard deviations for each channel.

    """

    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def __call__(self, tensor):
        new_tensor = tensor.clone()

        dtype = tensor.dtype
        mean = torch.as_tensor(self.mean, dtype=dtype, device=tensor.device)
        std = torch.as_tensor(self.std, dtype=dtype, device=tensor.device)
        for i, image in enumerate(tensor):
            new_tensor[i] = image.mul_(std).add_(mean)
        return new_tensor

    def __repr__(self):
        return self.__class__.__name__ + '(mean={0}, std={1})'.format(self.mean, self.std)

class RandomHorizontalFlip(object):
    """Horizontally flip every frame in the set pending probability.

    Args:
        p (float): probability of the image being flipped. Default value is 0.5
    """

    def __init__(self, p=0.5):
        self.p = p

    def __call__(self, clip):
        """
        Args:
            clip (sequence of grayscale images): clip to be flipped.

        Returns:
            Randomly flipped image.
        """
        if random.random() < self.p:
            for i, image in enumerate(clip):
                clip[i] = torch.flip(image, [1])

        return clip

    def __repr__(self):
        return self.__class__.__name__ + '(p={})'.format(self.p)


def pickle_loader(path, min_frames = None, shuffle_frames = False):
    """
    :param path: path to pickle file
    :return: opens the file and returns the un-pickled file
    NOTE: the returned file is in the range 0 to 1 !
    """
    # try:
    with open(path, 'rb') as handle:
        file = pickle.load(handle)
    file = file / 255
    if min_frames is not None:
        assert len(file) >= min_frames # Assert file has at least (max_frames) number of frames.
        file = file[:min_frames]
    # this option was added to ascertain weather the net uses frame order to determine classification.
    if shuffle_frames:
        np.random.shuffle(file)
    return file
    # except:
    #     print('Loading pickle file failed. path:', path)


def save_checkpoint(state, is_best, filename='checkpoint.pt.tar'):
    torch.save(state, filename)
    if is_best:
        shutil.copyfile(filename, 'model_best.pt.tar')


def load_checkpoint(model, path):
    if os.path.isfile(path):
        print("=> loading checkpoint")
        if not torch.cuda.is_available():
            checkpoint = torch.load(path, map_location=torch.device('cpu'))
        else:
            checkpoint = torch.load(path, map_location='cuda:0')
        state_dict = checkpoint['state_dict']
        if 'module' in list(checkpoint['state_dict'].keys())[0]:
            state_dict = remove_module_from_checkpoint_state_dict(state_dict)
        model.load_state_dict(state_dict)
        print("=> loaded checkpoint '{}' (epoch {})"
              .format(path, checkpoint['epoch']))
        return model
    else:
        print("=> no checkpoint file found at '{}'".format(path))

def load_model(model, path, on_cpu = True):
    if on_cpu:
        model.load_state_dict(remove_module_from_checkpoint_state_dict(torch.load(path, map_location=torch.device('cpu'))))
    else:
        model.load_state_dict(torch.load(path))
    model.eval()

def remove_module_from_checkpoint_state_dict(state_dict):
    """
    Removes the prefix `module` from weight names that gets added by
    torch.nn.DataParallel()
    """
    from collections import OrderedDict
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k[7:]  # remove `module.`
        new_state_dict[name] = v
    return new_state_dict


def train(epoch, run, mod_name = ''):
    total_train_loss = 0
    total_train_correct = 0
    incorrect_classifications_train = []
    epoch_classifications_train = []
    run.model.train()
    for batch_number, (images, labels, paths) in enumerate(run.train_loader):

        # for i, (image, label, path) in enumerate(zip(images, labels, paths)):
        #     save_plot_clip_frames(image, label, path, added_info_to_path = epoch)

        if run.grayscale:
            images = torch.unsqueeze(images, 1).double()  # added channel dimensions (grayscale)
        else:
            images = images.float().permute(0, 4, 1, 2, 3).float()
        labels = labels.long()

        if torch.cuda.is_available():
            images, labels = images.cuda(), labels.cuda()

        run.optimizer.zero_grad()  # Whenever pytorch calculates gradients it always adds it to whatever it has, so we need to reset it each batch.
        preds = run.model(images)  # Pass Batch

        loss = run.criterion(preds, labels)  # Calculate Loss
        total_train_loss += loss.item()
        loss.backward()  # Calculate Gradients - the gradient is the direction we need to move towards the loss function minimum (LR will tell us how far to step)
        run.optimizer.step()  # Update Weights - the optimizer is able to update the weights because we passed it the weights as an argument in line 4.

        num_correct = get_num_correct(preds, labels)
        total_train_correct += num_correct

        run.experiment.log_metric(mod_name + "Train batch accuracy", num_correct / len(labels) * 100, step=run.log_number_train)
        run.experiment.log_metric(mod_name + "Avg train batch loss", loss.item(), step=run.log_number_train)
        run.log_number_train += 1

        # print('Train: Batch number:', batch_number, 'Num correct:', num_correct, 'Accuracy:', "{:.2%}".format(num_correct/len(labels)), 'Loss:', loss.item())
        incorrect_classifications_train.append(get_mistakes(preds, labels, paths))
        for prediction in zip(preds, labels, paths):
            epoch_classifications_train.append(prediction)
    epoch_accuracy = calc_accuracy(epoch_classifications_train)

    run.experiment.log_metric(mod_name + "Train epoch accuracy", epoch_accuracy, step=epoch)
    run.experiment.log_metric(mod_name + "Avg train epoch loss", total_train_loss / batch_number, step=epoch)


    print('\nTrain: Epoch:', epoch, 'num correct:', total_train_correct, 'Accuracy:', str(epoch_accuracy) + '%')


def evaluate(epoch, run, mod_name = ''):
    incorrect_classifications_val = []
    total_val_loss = 0
    total_val_correct = 0
    best_val_acc = 0
    epoch_classifications_val = []
    run.model.eval()
    with torch.no_grad():
        for batch_number, (images, labels, paths) in enumerate(run.val_loader):

            if run.grayscale:
                images = torch.unsqueeze(images, 1).double()  # added channel dimensions (grayscale)
            else:
                images = images.float().permute(0, 4, 1, 2, 3).float()
            labels = labels.long()

            if torch.cuda.is_available():
                images, labels = images.cuda(), labels.cuda()

            preds = run.model(images)  # Pass Batch
            loss = run.criterion(preds, labels)  # Calculate Loss
            total_val_loss += loss.item()

            num_correct = get_num_correct(preds, labels)
            total_val_correct += num_correct

            run.experiment.log_metric(mod_name + "Val batch accuracy", num_correct / len(labels) * 100, step=run.log_number_val)
            run.experiment.log_metric(mod_name + "Avg val batch loss", loss.item(), step=run.log_number_val)
            run.log_number_val += 1

            # print('Val: Batch number:', batch_number, 'Num correct:', num_correct, 'Accuracy:', "{:.2%}".format(num_correct / len(labels)), 'Loss:', loss.item())
            # print_mistakes(preds, labels, paths)

            incorrect_classifications_val.append(get_mistakes(preds, labels, paths))

            for prediction in zip(preds, labels, paths):
                epoch_classifications_val.append(prediction)

        epoch_accuracy = calc_accuracy(epoch_classifications_val)

        run.experiment.log_metric(mod_name + "Val epoch accuracy", epoch_accuracy, step=epoch)
        run.experiment.log_metric(mod_name + "Avg val epoch loss", total_val_loss / batch_number, step=epoch)
        print('Val Epoch:', epoch, 'num correct:', total_val_correct, 'Accuracy:', str(epoch_accuracy) + '%')

    is_best = (epoch_accuracy > run.best_val_acc) | ((epoch_accuracy >= run.best_val_acc) & (total_val_loss/batch_number < run.best_val_loss))
    if is_best:
        print("Best run so far! updating params...")
        run.best_val_acc = epoch_accuracy
        run.best_val_loss = total_val_loss/batch_number
        run.best_model_preds = epoch_classifications_val
        run.best_model_mistakes = incorrect_classifications_val
    save_checkpoint({
        'epoch': epoch + 1,
        'state_dict': run.model.state_dict(),
        'best_acc1': run.best_val_acc,
        'optimizer': run.optimizer.state_dict(),
    }, is_best)

    # Step lr_scheduler
    run.lr_scheduler.step()


def create_model(hyper_params):
    # In this way we can build a model using the function outside the class as well as in it.
    if hyper_params['model_type'] == "3dCNN":
        return get_modular_3dCNN(hyper_params)
    elif hyper_params['model_type'] == 'resnext':
        return get_resnext(hyper_params)
    else:
        raise NameError("Unknown model type")


def get_resnext(hyper_params):
    model = generate_resnext_model('score') # in score, last_ft=True, in feature, last_fc=False
    model = nn.DataParallel(model).cuda(0)
    print('loading resnext model')
    model_data = torch.load('resnext-101-64f-kinetics.pth')
    model.load_state_dict(model_data['state_dict'])
    for param in model.parameters():
        param.requires_grad = False
    # Parameters of newly constructed modules have requires_grad=True by default
    num_classes = len(hyper_params['classes'])
    model.module.fc = nn.Linear(2048, num_classes)
    model.to(torch.device('cuda:0'))
    return model


def get_modular_3dCNN(hyper_params):
    num_classes = len(hyper_params['classes'])
    model = ModularCNN(make_layers(hyper_params["features"], batch_norm=True), classifier = hyper_params["classifier"], adaptive_pool=hyper_params["adaptive_pool"], num_classes = num_classes)
    if torch.cuda.is_available():
        model = model.cuda(0)
    if torch.cuda.device_count() > 1:
        print("Let's use", torch.cuda.device_count(), "GPUs!")
        model = nn.DataParallel(model).cuda(0)
        model.to(torch.device('cuda:0'))
    return model

def load_run_for_inference(hyper_params, checkpoint_path, machine = 'server'):
    from run_state import Run # import placed here to avoid circular dependency with Run
    run = Run(machine=machine, hyper_params=hyper_params, inference=True, checkpoint_path=checkpoint_path)
    run.model.eval()
    return run

