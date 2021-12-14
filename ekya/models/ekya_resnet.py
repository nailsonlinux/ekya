from collections import defaultdict

import torchvision.models as models
import torch.nn as nn
import torch
import time
import torch.optim as optim
import copy

from torch.optim.lr_scheduler import ReduceLROnPlateau

class Resnet(object):
    DEFAULT_HYPER_PARAMS = {'num_hidden': 512,
                            'last_layer_only': True,
                            'model_name': "resnet18"}
    def __init__(self, hyperparameters, pretrained=True, restore_path=None,):
        # Required params in hyperparameters: ["num_hidden", "last_layer_only", "model_name"]
        print("Initializing model with hyperparameters: {}".format(hyperparameters))
        self.hyperparameters = hyperparameters if hyperparameters else self.DEFAULT_HYPER_PARAMS
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_class = self.get_model_from_str(hyperparameters['model_name'])
        self.model = self.model_class(pretrained=pretrained)
        self.last_layer_only = self.hyperparameters["last_layer_only"]
        self.set_parameter_requires_grad()
        self.num_classes = self.hyperparameters["num_classes"]
        self.initialize_last_layer(self.num_classes, num_hidden=self.hyperparameters["num_hidden"])
        self.set_params_to_update()
        if restore_path:
            self.load(restore_path)
        self.model.to(self.device)

    @staticmethod
    def get_model_from_str(model_str):
        if model_str == 'resnet18':
            return models.resnet18
        if model_str == 'resnet50':
            return models.resnet50
        if model_str == 'resnet101':
            return models.resnet101
        if model_str == 'resnet152':
            return models.resnet152
        raise Exception("Model {} not found".format(model_str))

    def initialize_last_layer(self, num_classes, num_hidden=512):
        self.model.fc = nn.Linear(self.model.fc.in_features, num_hidden)

        self.model = nn.Sequential(
            self.model,
            nn.Linear(num_hidden, num_classes)
        )

    def set_parameter_requires_grad(self):
        if self.last_layer_only:
            for param in self.model.parameters():
                param.requires_grad = False

    def set_params_to_update(self):
        print("Params to learn:")
        if self.last_layer_only:
            params_to_update = []
            for name, param in self.model.named_parameters():
                if param.requires_grad == True:
                    params_to_update.append(param)
                    print("\t", name)
        else:
            params_to_update = self.model.parameters()
            for name, param in self.model.named_parameters():
                if param.requires_grad == True:
                    print("\t", name)
        self.params_to_update = params_to_update

    def train_model(self, dataloaders, subprofile_test_epochs = None, num_epochs=1, lr=0.001, momentum=0.9):
        '''
        Trains the resnet model.
        :param dataloaders: dict of "train", "test", "val" with corresponding dataloaders.
        :param subprofile_test_epochs: Specifies the epochs at which all tasks should be tested and corresponding data loaders. A dict of {epoch_num: {taskid: test_dataloader, ....}}.
        :param num_epochs:
        :param lr:
        :param momentum:
        :return:
        '''
        since = time.time()
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.SGD(self.params_to_update, lr=lr, momentum=momentum)
        scheduler = ReduceLROnPlateau(optimizer, 'min', verbose=True)

        val_acc_history = []

        best_model_wts = copy.deepcopy(self.model.state_dict())
        best_acc = 0.0

        profile = []    # List of [timestamp, train metrics, val metrics, test metrics]
        subprofile_test_results = {}

        if dataloaders["train"] is None:
            # 0th task, just run inference for subprofiles
            # Ideally this needs to run just once and assign the same subprofile to all epochs since there's no retraining
            # However, not optimizing this because user may pass different test loaders for different epochs.

            for epoch in subprofile_test_epochs.keys():
                subprofile_test_this_epoch = {}
                for task_id, task_test_loader in subprofile_test_epochs[epoch].items():
                    subprofile_test_this_epoch[task_id] = self.infer(task_test_loader)
                subprofile_test_results[epoch] = subprofile_test_this_epoch

        if dataloaders["train"] is not None:
            for epoch in range(num_epochs):
                epoch_start_time = time.time()
                print('Epoch {}/{}'.format(epoch, num_epochs - 1))
                print('-' * 10)

                profile_data = defaultdict(lambda: defaultdict(lambda: 0))

                # Each epoch has a training and validation phase
                for phase in dataloaders.keys():
                    start_time = time.time()
                    if phase == 'train':
                        self.model.train()  # Set model to training mode
                    else:
                        self.model.eval()  # Set model to evaluate mode

                    running_loss = 0.0
                    running_corrects = 0

                    # Iterate over data.
                    for batch_idx, (inputs, labels) in enumerate(dataloaders[phase]):
                        inputs = inputs.to(self.device)
                        labels = labels.to(self.device)

                        # zero the parameter gradients
                        optimizer.zero_grad()

                        # forward
                        # track history if only in train
                        with torch.set_grad_enabled(phase == 'train'):
                            outputs = self.model(inputs)
                            loss = criterion(outputs, labels)
                            _, preds = torch.max(outputs, 1)

                            # backward + optimize only if in training phase
                            if phase == 'train':
                                loss.backward()
                                optimizer.step()

                        # statistics
                        running_loss += loss.item() * inputs.size(0)
                        running_corrects += torch.sum(preds == labels.data)

                        print(
                            '{} Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.
                                format(phase, epoch, batch_idx * len(inputs), len(dataloaders[phase]) * len(inputs),
                                       100. * batch_idx / len(dataloaders[phase]), loss))

                    epoch_loss = running_loss / len(dataloaders[phase].dataset)
                    epoch_acc = running_corrects.double() / len(dataloaders[phase].dataset)

                    if phase == 'train':
                        scheduler.step(epoch_loss)

                    end_time = time.time()
                    print('{} epoch done. Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))

                    # deep copy the model
                    if phase == 'val' and epoch_acc > best_acc:
                        val_acc_history.append(epoch_acc)
                        if epoch_acc > best_acc:
                            best_acc = epoch_acc
                            best_model_wts = copy.deepcopy(self.model.state_dict())
                    profile_data[phase]['time'] = end_time-start_time
                    profile_data[phase]['loss'] = float(epoch_loss)
                    profile_data[phase]['acc'] = float(epoch_acc)
                    profile_data[phase]['num_samples'] = len(dataloaders[phase].dataset)
                profile_this_epoch = [epoch_start_time]
                for phase in ["train","val","test"]:
                    for metric in ['time', 'loss', 'acc', 'num_samples']:
                        profile_this_epoch.append(profile_data[phase][metric])
                profile.append(profile_this_epoch)

                # Epoch done, check if this is a subprofile epoch and run testing on all tasks if required
                if epoch in subprofile_test_epochs.keys():
                    subprofile_test_this_epoch = {}
                    for task_id, task_test_loader in subprofile_test_epochs[epoch].items():
                        subprofile_test_this_epoch[task_id] = self.infer(task_test_loader)
                    subprofile_test_results[epoch] = subprofile_test_this_epoch

        time_elapsed = time.time() - since
        print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
        print('Best val Acc: {:4f}'.format(best_acc))

        # load best model weights
        self.model.load_state_dict(best_model_wts)
        return self.model, val_acc_history, float(best_acc), profile, subprofile_test_results

    def infer(self, dataloader):
        self.model.eval()
        running_corrects = 0

        # Iterate over data.
        for batch_idx, (inputs, labels) in enumerate(dataloader):
            inputs = inputs.to(self.device)
            labels = labels.to(self.device)

            # forward
            with torch.set_grad_enabled(False):
                outputs = self.model(inputs)
                _, preds = torch.max(outputs, 1)
            num_corrects = torch.sum(preds == labels.data)
            running_corrects += num_corrects

            print(
                'Infer [{}/{} ({:.0f}%)]\tBatch acc: {:.2f}% \tRunning acc: {:.2f}%'.
                    format(batch_idx * len(inputs), len(dataloader) * len(inputs),
                           100. * batch_idx / len(dataloader),
                           num_corrects.double() / len(inputs),
                           running_corrects.double() / batch_idx * len(inputs)))

        acc = running_corrects.double() / len(dataloader.dataset)

        print('Inference done. Final Acc: {:.4f}'.format(acc))
        return float(acc.double())

    def save(self, path):
        torch.save(self.model.state_dict(), path)

    def load(self, path):
        self.model.load_state_dict(torch.load(path, map_location=torch.device(self.device)))
