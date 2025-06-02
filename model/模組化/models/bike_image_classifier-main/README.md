# Deep Learning Bike Image Classification Project

This repository contains a deep learning project for classifying bicycle and motorcycle images using TensorFlow and Keras. The project involves data scraping, model training, and evaluation.

## Project Overview

The main goal of this project is to develop a deep learning model that can accurately classify images as either bicycles or motorcycles. The project involves the following steps:

1. **Data Collection**: Around 200 images were scraped from Google using a Python script. Images that were not in the .jpg or .jpeg format were filtered out.

2. **Model Architecture**: The project utilizes a Convolutional Neural Network (CNN) architecture implemented using TensorFlow and Keras. The model architecture consists of several layers, including convolutional layers, max-pooling layers, and fully connected layers.

3. **Model Training**: The CNN model is trained on the collected dataset of labeled bicycle and motorcycle images. The model is trained to minimize the loss and improve accuracy.

4. **Model Evaluation**: The trained model is evaluated using precision, recall, and binary accuracy metrics. These metrics provide insights into the model's performance in classifying images.

5. **Model Saving**: The trained model is saved in a format suitable for production deployment. This saved model can be used to make predictions on new and unseen images.

## Model Architecture

The CNN model architecture consists of the following layers:

1. Convolutional Layer: 16 filters, each of size 3x3.
2. Max Pooling Layer: Reduces the spatial dimensions by a factor of 2.
3. Convolutional Layer: 32 filters, each of size 3x3.
4. Max Pooling Layer: Reduces the spatial dimensions by a factor of 2.
5. Convolutional Layer: 16 filters, each of size 3x3.
6. Max Pooling Layer: Reduces the spatial dimensions by a factor of 2.
7. Flatten Layer: Flattens the output from the previous layer.
8. Fully Connected Layer: 256 neurons with ReLU activation.
9. Fully Connected Layer: 1 neuron with a sigmoid activation.

## Model Performance

The trained model achieved the following performance metrics:

- Precision: 1.0
- Recall: 1.0
- Binary Accuracy: 1.0

These metrics indicate that the model is capable of accurately classifying both bicycles and motorcycles from the provided images.

## Usage

1. **Data Preparation**: Ensure that your dataset is prepared with labeled images of bicycles and motorcycles.

2. **Model Training**: Use the provided code to train the CNN model on your prepared dataset. Adjust hyperparameters as needed.

3. **Model Evaluation**: After training, evaluate the model using various metrics to assess its performance.

4. **Model Saving**: Save the trained model using the provided code. This saved model can be deployed for making predictions on new images.

5. **Prediction**: Use the saved model to make predictions on new images by loading the model and passing images through it.

## Files and Folders

- `data/`: Contains the collected and prepared dataset.
- `model.ipynb`: Jupyter Notebook containing code for model training and evaluation.
- `model/`: Folder containing the saved model files for production use.

## Conclusion

This project demonstrates the process of developing a deep learning model for image classification using TensorFlow and Keras. The model is capable of accurately classifying bicycle and motorcycle images. The trained model can be further fine-tuned and deployed in real-world applications.

