"""
A collection of models we'll use to attempt to classify videos.
"""
from keras.engine.training import Model
from keras.layers import Dense, Flatten, Dropout
from keras.layers.recurrent import LSTM
from keras.models import Sequential, load_model, model_from_json
from keras.optimizers import Adam, SGD
from keras.layers.wrappers import TimeDistributed
from keras.layers.convolutional import (Conv2D, MaxPooling3D, Conv3D, MaxPooling2D)
from collections import deque
import sys
import os


class ResearchModels():
    def __init__(self, nb_classes, model, seq_length,
                 saved_model=None, features_length=2048, dimension=150):
        """
        `model` = one of:
            lstm
            crnn
            mlp
            conv_3d
        `nb_classes` = the number of classes to predict
        `seq_length` = the length of our video sequences
        `saved_model` = the path to a saved Keras model to load
        """
        image_width = dimension
        image_heigth = dimension
        image_channels = 3

        # Set defaults.
        self.seq_length = seq_length
        self.load_model = load_model
        self.saved_model = saved_model
        self.nb_classes = nb_classes
        self.feature_queue = deque()

        # Set the metrics. Only use top k if there's a need.
        metrics = ['accuracy']
        if self.nb_classes >= 10:
            metrics.append('top_k_categorical_accuracy')

        # Get the appropriate model.
        if self.saved_model is not None:
            print("Loading model %s" % self.saved_model)
            self.model = load_model(self.saved_model)
        elif model == 'lstm':
            print("Loading LSTM model.")
            self.input_shape = (seq_length, features_length)
            self.model = self.lstm_tuned()
        elif model == 'crnn':
            print("Loading CRNN model.")
            self.input_shape = (seq_length, image_width, image_heigth, image_channels)
            self.model = self.crnn()
        elif model == 'mlp':
            print("Loading simple MLP.")
            self.input_shape = features_length * seq_length
            self.model = self.mlp()
        elif model == 'conv_3d':
            print("Loading Conv3D")
            self.input_shape = (seq_length, image_width, image_heigth, image_channels)
            self.model = self.conv_3d_pre_trained()
        else:
            print("Unknown network.")
            sys.exit()

        # Now compile the network.
        optimizer = Adam(lr=1)
        optimizer = Adam(lr=1e-6)  # aggressively small learning rate
        optimizer = Adam(lr=1e-4, decay=1e-6)
        optimizer = Adam(lr=1e-4, decay=1e-4)
        self.model.compile(loss='categorical_crossentropy', optimizer=optimizer,
                           metrics=metrics)

    def lstm(self):
        """Build a simple LSTM network. We pass the extracted features from
        our CNN to this model predomenently."""
        # Model.
        model = Sequential()
        model.add(LSTM(2048, return_sequences=True, input_shape=self.input_shape,
                       dropout=0.5))
        model.add(Flatten())
        model.add(Dense(512, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(self.nb_classes, activation='softmax'))

        return model

    def lstm_tuned(self):
        """Build a simple LSTM network. We pass the extracted features from
        our CNN to this model predomenently."""
        # Model.
        model = Sequential()
        model.add(LSTM(128, return_sequences=True, input_shape=self.input_shape,
                       dropout=0.5))
        model.add(Flatten())
        model.add(Dense(64, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(self.nb_classes, activation='softmax'))

        return model

    def crnn(self):
        """Build a CNN into RNN.
        Starting version from:
        https://github.com/udacity/self-driving-car/blob/master/
            steering-models/community-models/chauffeur/models.py
        """
        model = Sequential()
        model.add(TimeDistributed(Conv2D(32, (3, 3),
                                         kernel_initializer="he_normal",
                                         activation='relu'), input_shape=self.input_shape))
        model.add(TimeDistributed(Conv2D(32, (3, 3),
                                         kernel_initializer="he_normal",
                                         activation='relu')))
        model.add(TimeDistributed(MaxPooling2D()))
        model.add(TimeDistributed(Conv2D(48, (3, 3),
                                         kernel_initializer="he_normal",
                                         activation='relu')))
        model.add(TimeDistributed(Conv2D(48, (3, 3),
                                         kernel_initializer="he_normal",
                                         activation='relu')))
        model.add(TimeDistributed(MaxPooling2D()))
        model.add(TimeDistributed(Conv2D(64, (3, 3),
                                         kernel_initializer="he_normal",
                                         activation='relu')))
        model.add(TimeDistributed(Conv2D(64, (3, 3),
                                         kernel_initializer="he_normal",
                                         activation='relu')))
        model.add(TimeDistributed(MaxPooling2D()))
        model.add(TimeDistributed(Conv2D(128, (3, 3),
                                         kernel_initializer="he_normal",
                                         activation='relu')))
        model.add(TimeDistributed(Conv2D(128, (3, 3),
                                         kernel_initializer="he_normal",
                                         activation='relu')))
        model.add(TimeDistributed(MaxPooling2D()))
        model.add(TimeDistributed(Flatten()))
        model.add(LSTM(256, return_sequences=True))
        model.add(Flatten())
        model.add(Dense(512))
        model.add(Dropout(0.5))
        model.add(Dense(self.nb_classes, activation='softmax'))

        return model

    def mlp(self):
        """Build a simple MLP."""
        # Model.
        model = Sequential()
        model.add(Dense(512, input_dim=self.input_shape))
        model.add(Dropout(0.5))
        model.add(Dense(512))
        model.add(Dropout(0.5))
        model.add(Dense(self.nb_classes, activation='softmax'))

        return model

    def conv_3d(self):
        """
        Build a 3D convolutional network, based loosely on C3D.
            https://arxiv.org/pdf/1412.0767.pdf
        """
        # Model.
        model = Sequential()
        model.add(Conv3D(
            32, (7, 7, 7), activation='relu', input_shape=self.input_shape
        ))
        model.add(MaxPooling3D(pool_size=(1, 2, 2), strides=(1, 2, 2)))
        model.add(Conv3D(64, (3, 3, 3), activation='relu'))
        model.add(MaxPooling3D(pool_size=(1, 2, 2), strides=(1, 2, 2)))
        model.add(Conv3D(128, (2, 2, 2), activation='relu'))
        model.add(MaxPooling3D(pool_size=(1, 2, 2), strides=(1, 2, 2)))
        model.add(Flatten())
        model.add(Dense(256))
        model.add(Dropout(0.2))
        model.add(Dense(256))
        model.add(Dropout(0.2))
        model.add(Dense(self.nb_classes, activation='softmax'))

        return model

    def conv_3d_tuned(self):
        """
        Build a 3D convolutional network, based loosely on C3D.
            https://arxiv.org/pdf/1412.0767.pdf
        """
        # Model.
        model = Sequential()
        model.add(Conv3D(32, (7, 7, 7), activation='relu', input_shape=self.input_shape))
        model.add(MaxPooling3D(pool_size=(1, 2, 2), strides=(1, 2, 2)))
        model.add(Conv3D(64, (3, 3, 3), activation='relu'))
        model.add(MaxPooling3D(pool_size=(1, 2, 2), strides=(1, 2, 2)))
        model.add(Conv3D(128, (2, 2, 2), activation='relu'))
        model.add(MaxPooling3D(pool_size=(1, 2, 2), strides=(1, 2, 2)))
        model.add(Flatten())
        model.add(Dense(128))
        model.add(Dropout(0.2))
        model.add(Dense(64))
        model.add(Dropout(0.2))
        model.add(Dense(self.nb_classes, activation='softmax'))

        return model

    def conv_3d_pre_trained(self):
        """
        Build a 3D convolutional network, based loosely on C3D.
            https://arxiv.org/pdf/1412.0767.pdf
        """
        # Model.

        root_dir = './thirdp/c3d_keras/'
        model_dir = root_dir + 'models'

        model_weight_filename = os.path.join(model_dir, 'sports1M_weights_tf.h5')
        model_json_filename = os.path.join(model_dir, 'sports1M_weights_tf.json')

        print("[Info] Reading model architecture...")
        base_model = model_from_json(open(model_json_filename, 'r').read())

        print("[Info] Loading model weights...")
        base_model.load_weights(model_weight_filename)
        print("[Info] Loading model weights -- DONE!")

        for i, layer in enumerate(base_model.layers):
            print(i, layer.name)
            print(layer.get_output_at(0).get_shape().as_list())

        x = base_model.get_layer('pool5').output

        x = Flatten()(x)
        x = Dense(4096)(x)
        x = Dropout(0.2)(x)
        x = Dense(4096)(x)
        x = Dropout(0.2)(x)
        predictions = Dense(self.nb_classes, activation='softmax')(x)

        # this is the model we will train
        model = Model(inputs=base_model.input, outputs=predictions)

        for i, layer in enumerate(model.layers):
            print(i, layer.name)
            print(layer.get_output_at(0).get_shape().as_list())

        # first: train only the top layers (which were randomly initialized)
        # i.e. freeze all convolutional InceptionV3 layers
        for layer in base_model.layers:
            layer.trainable = True

        # model.compile(loss='mean_squared_error', optimizer='sgd')

        # compile the model (should be done *after* setting layers to non-trainable)
        # model.compile(optimizer='rmsprop', loss='categorical_crossentropy')

        return model

    def conv_3d_prop(self):
        """
        Build a 3D convolutional network, based loosely on C3D.
            https://arxiv.org/pdf/1412.0767.pdf
        """
        # Model.
        model = Sequential()
        model.add(Conv3D(64, (3, 3, 3), activation='relu', input_shape=self.input_shape))
        model.add(MaxPooling3D(pool_size=(1, 2, 2), strides=(1, 2, 2)))

        model.add(Conv3D(128, (3, 3, 3), activation='relu'))
        model.add(MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2)))

        model.add(Conv3D(256, (3, 3, 3), activation='relu'))
        model.add(Conv3D(512, (3, 3, 3), activation='relu'))
        model.add(MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2)))

        model.add(Conv3D(512, (3, 3, 3), activation='relu'))
        model.add(Conv3D(512, (3, 3, 3), activation='relu'))
        model.add(MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2)))

        model.add(Conv3D(512, (3, 3, 3), activation='relu'))
        model.add(Conv3D(512, (3, 3, 3), activation='relu'))
        model.add(MaxPooling3D(pool_size=(2, 2, 2), strides=(2, 2, 2)))

        model.add(Flatten())
        model.add(Dense(4096))
        model.add(Dropout(0.2))
        model.add(Dense(4096))
        model.add(Dropout(0.2))
        model.add(Dense(self.nb_classes, activation='softmax'))

        return model
