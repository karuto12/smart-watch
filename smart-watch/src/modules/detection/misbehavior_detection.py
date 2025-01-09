from torchvision import transforms, models
from torch import stack, nn
import torch
from os.path import abspath

# To download the pretrained weights
# from torchvision.models import resnet101, ResNet101_Weights
# model = resnet101(weights=ResNet101_Weights.IMAGENET1K_V2)

model_save_path = r"smart-watch\smart-watch\data\models\misbehavior_classifier.pth"
model_save_path = abspath(model_save_path)

def preprocess_images(images):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),  # Resize to 224x224
        transforms.ToTensor(),         # Convert to tensor
        transforms.Normalize(mean=[0.485, 0.456, 0.406],  # Normalize (ImageNet values)
                             std=[0.229, 0.224, 0.225])
    ])

    # Preprocess each image
    image_tensors = []
    for img in images:
        image_tensor = transform(img)
        image_tensors.append(image_tensor)
    
    # Stack all images into a single batch
    return stack(image_tensors)

def load_model(model_path=model_save_path):
    # Define the model architecture (same as used for training)
    model = models.resnet101(pretrained=False)  # ResNet-101, no pre-trained weights
    num_features = model.fc.in_features
    model.fc = nn.Linear(num_features, 5)  # Replace the final layer with 5 categories

    # Load the model weights
    model.load_state_dict(torch.load(model_path))

    # Move model to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    return model
    # Set model to evaluation mode
    # model.eval()

def predict(img_batch, model):
    with torch.no_grad():
        outputs = model(img_batch)
        _, predicted = torch.max(outputs, 1)

    # Print the predicted categories for each camera
    for i, pred in enumerate(predicted):
        print(f"Camera {i+1} - Predicted misbehavior level: {pred.item()}")
    return predicted
