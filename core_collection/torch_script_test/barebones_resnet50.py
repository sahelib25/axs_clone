#!/usr/bin/env python3

"""An example Python script that is given its data, necessary Python environment and the output path by wrapping it into an Entry.

Usage examples :
                axs byname torch_script_test , run --execution_device=cpu --num_of_images=100

                axs byname torch_script_test , run --torchvision_query+=with_cuda --num_of_images=500
"""

import json
import os
import sys

imagenet_dir        = sys.argv[1]
num_of_images       = int(sys.argv[2])
model_name          = sys.argv[3]
output_file_path    = sys.argv[4]       # if empty, recording of the output will be skipped
execution_device    = sys.argv[5]       # if empty, it will be autodetected
file_pattern        = 'ILSVRC2012_val_000{:05d}.JPEG'

# sample execution (requires torchvision)
from PIL import Image
from time import time
import torch
import torchvision
from torchvision import transforms

execution_device    = execution_device or ('cuda' if torch.cuda.is_available() else 'cpu')  # autodetection
torchvision_version = ':v' + torchvision.__version__.split('+')[0]

ts_before_model_loading = time()

model = torch.hub.load('pytorch/vision' + torchvision_version, model_name, pretrained=True)
model.eval()
model.to( execution_device )

ts_before_data_loading  = time()

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

file_names  = []
pre_batch   = []
for i in range(num_of_images):
    file_name = file_pattern.format(i+1)
    file_path   = os.path.join( imagenet_dir, file_name )
    input_image = Image.open( file_path ).convert('RGB')
    input_tensor = preprocess(input_image)
    file_names.append( file_name )
    pre_batch.append(input_tensor)

input_batch = torch.stack(pre_batch, dim=0)
input_batch = input_batch.to( execution_device )

ts_before_inference     = time()

with torch.no_grad():
    output = model(input_batch)

# The output has unnormalized scores. To get probabilities, you can run a softmax on it.
#print(torch.nn.functional.softmax(output[0], dim=0))

class_numbers = torch.argmax(output, dim=1).tolist()

ts_before_reporting     = time()

if output_file_path:
    output_dict = {
        "execution_device": execution_device,
        "time": {
            "model_loading_s":  ts_before_data_loading - ts_before_model_loading,
            "data_loading_s":   ts_before_inference - ts_before_data_loading,
            "all_inference_s":  ts_before_reporting - ts_before_inference,
            "per_inference_s":  (ts_before_reporting - ts_before_inference) / num_of_images,
            "fps":              num_of_images / (ts_before_reporting - ts_before_inference),
        },
        "predictions": dict( zip(file_names, class_numbers) )
    }
    json_string = json.dumps( output_dict , indent=4)
    with open(output_file_path, "w") as json_fd:
        json_fd.write( json_string+"\n" )
    print(f'Predictions for {num_of_images} images written into "{output_file_path}"')
else:
    print(class_numbers)
