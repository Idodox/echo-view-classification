# from PIL import Image
import numpy as np
import torch
from vis_utils import get_clip_to_run, save_class_activation_images
from torchutils import create_model, load_checkpoint

class CamExtractor:
    """
        Extracts cam features from the model
    """
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None

    def save_gradient(self, grad):
        self.gradients = grad

    def forward_pass_on_convolutions(self, x):
        """
            Does a forward pass on convolutions, hooks the function at given layer
        """
        conv_output = None
        if torch.cuda.is_available():
            items = self.model.module.features._modules.items()
        else:
            items = self.model.features._modules.items()
        for module_pos, module in items:
            x = module(x)  # Forward
            if int(module_pos) == self.target_layer:
                x.register_hook(self.save_gradient)
                conv_output = x  # Save the convolution output on that layer
        return conv_output, x

    def forward_pass(self, x):
        """
            Does a full forward pass on the model
        """
        # Forward pass on the convolutions
        conv_output, x = self.forward_pass_on_convolutions(x)
        # There may be an avgpool layer:
        try:
            if torch.cuda.is_available():
                x = self.model.module.avgpool(x)
            else:
                x = self.model.avgpool(x)
        except AttributeError:
            pass
        x = x.view(x.size(0), -1)  # Flatten
        # Forward pass on the classifier
        if torch.cuda.is_available():
            x = self.model.module.classifier(x)
        else:
            x = self.model.classifier(x)

        return conv_output, x


class GradCam():
    """
        Produces class activation map
    """
    def __init__(self, model, target_layer):
        self.model = model
        self.model.eval()
        # Define extractor
        self.extractor = CamExtractor(self.model, target_layer)

    def zero_grad(self):
        if torch.cuda.is_available():
            self.model.module.features.zero_grad()
            self.model.module.classifier.zero_grad()
        else:
            self.model.features.zero_grad()
            self.model.classifier.zero_grad()
        try:
            if torch.cuda.is_available():
                self.model.module.avgpool.zero_grad()
            else:
                self.model.avgpool.zero_grad()
        except AttributeError:
            pass


    def generate_cam(self, input_clip, target_class=None):
        # Full forward pass
        # conv_output is the output of convolutions at specified layer
        # model_output is the final output of the model (1, 1000)
        conv_output, model_output = self.extractor.forward_pass(input_clip)
        if target_class is None:
            target_class = np.argmax(model_output.data.numpy())
        # Target for backprop
        one_hot_output = torch.cuda.FloatTensor(1, model_output.size()[-1]).zero_()
        one_hot_output[0][target_class] = 1
        # Zero grads
        self.zero_grad()
        # Backward pass with specified target
        model_output.backward(gradient=one_hot_output, retain_graph=True)
        # Get hooked gradients
        guided_gradients = self.extractor.gradients.data.cpu().numpy()[0] # we take it at position 0 to remove batch dimension
        # Get convolution outputs
        target = conv_output.data.cpu().numpy()[0]
        # Get weights from gradients
        weights = np.mean(guided_gradients, axis=(1, 2))  # Take averages for each gradient
        # Create empty numpy array for cam
        cam = np.ones(target.shape[1:], dtype=np.float32)
        # Multiply each weight with its conv output and then, sum
        for i, w in enumerate(weights):
            cam += w * target[i, :, :]
        cam = np.max(cam, 0)
        cam = (cam - np.min(cam)) / (np.max(cam) - np.min(cam))  # Normalize between 0-1
        cam = np.uint8(cam * 255)  # Scale between 0-255 to visualize
        cam = np.uint8(Image.fromarray(cam).resize((input_clip.shape[2], input_clip.shape[3]), Image.ANTIALIAS))/255
        # ^ I am extremely unhappy with this line. Originally resizing was done in cv2 which
        # supports resizing numpy matrices with antialiasing, however,
        # when I moved the repository to PIL, this option was out of the window.
        # So, in order to use resizing with ANTIALIAS feature of PIL,
        # I briefly convert matrix to PIL image and then back.
        # If there is a more beautiful way, do not hesitate to send a PR.

        # You can also use the code below instead of the code line above, suggested by @ ptschandl
        # from scipy.ndimage.interpolation import zoom
        # cam = zoom(cam, np.array(input_image[0].shape[1:])/np.array(cam.shape))
        return cam


if __name__ == '__main__':

    hyper_params = {"max_frames": 10
        , "random_seed": 999
        , "classes": ['apex', 'papillary', 'mitral', '2CH', '3CH', '4CH']
        , "model_type": "3dCNN"
        , "resolution": 100
        , "adaptive_pool": (7, 5, 5)
        , "features": [16, 16, "M", 16, 16, "M", 32, 32, "M"]
        ,"classifier": [0.5, 200,0.5, 150, 0.4, 100]
     }

    # clip_path = '/Users/idofarhi/Documents/Thesis/Data/frames/5frame_steps10/2CH/AA-055KAP_2CH_0.pickle'
    clip_path = '/home/ido/data/5frame_steps10/2CH/AA-055KAP_2CH_0.pickle'
    # checkpoint_path = '/Users/idofarhi/Documents/Thesis/Code/model_best.pt.tar'
    checkpoint_path = '/home/ido/PycharmProjects/us-view-classification/model_best.pt.tar'

    (original_clip, prep_clip, movie_name, target_class) = get_clip_to_run(clip_path)

    model = create_model(hyper_params)
    pretrained_model = load_checkpoint(model, checkpoint_path)

    # Grad cam
    grad_cam = GradCam(pretrained_model, target_layer=17)
    # Generate cam mask
    cam = grad_cam.generate_cam(prep_clip, target_class)
    # Save mask
    save_class_activation_images(original_clip, cam, movie_name)
    print('Grad cam completed')