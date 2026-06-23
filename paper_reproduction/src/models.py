from __future__ import annotations

import torch
from torch import nn


def conv_bn_relu(in_channels: int, out_channels: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
        nn.BatchNorm3d(out_channels),
        nn.ReLU(inplace=True),
    )


class PaperCNN3D(nn.Module):
    """Paper-inspired 2+3+2 convolution architecture with 1,000-D FC features."""

    model_name = "paper_cnn"

    def __init__(self, num_classes: int = 3, dropout: float = 0.35) -> None:
        super().__init__()
        self.block1 = nn.Sequential(conv_bn_relu(1, 16), conv_bn_relu(16, 16), nn.MaxPool3d(2))
        self.block2 = nn.Sequential(
            conv_bn_relu(16, 32), conv_bn_relu(32, 32), conv_bn_relu(32, 32), nn.MaxPool3d(2)
        )
        self.block3 = nn.Sequential(conv_bn_relu(32, 64), conv_bn_relu(64, 64), nn.MaxPool3d(2))
        self.pool = nn.AdaptiveMaxPool3d(1)
        self.fc1 = nn.Linear(64, 1000)
        self.fc2 = nn.Linear(1000, 1000)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(1000, num_classes)

    def forward(self, x: torch.Tensor, return_features: bool = False):
        x = self.block3(self.block2(self.block1(x)))
        x = self.pool(x).flatten(1)
        fc1 = torch.relu(self.fc1(x))
        fc2 = torch.relu(self.fc2(self.dropout(fc1)))
        # The paper describes FC-1/FC-2 fusion as element-wise maximum.
        features = torch.maximum(fc1, fc2)
        logits = self.classifier(self.dropout(features))
        return (logits, features) if return_features else logits


class ResidualUnit3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1) -> None:
        super().__init__()
        self.conv1 = nn.Conv3d(in_channels, out_channels, 3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm3d(out_channels)
        self.conv2 = nn.Conv3d(out_channels, out_channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm3d(out_channels)
        self.skip = (
            nn.Identity()
            if stride == 1 and in_channels == out_channels
            else nn.Sequential(
                nn.Conv3d(in_channels, out_channels, 1, stride=stride, bias=False),
                nn.BatchNorm3d(out_channels),
            )
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.skip(x)
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.bn2(self.conv2(x))
        return self.relu(x + residual)


class ResNet3D(nn.Module):
    model_name = "resnet3d"

    def __init__(self, num_classes: int = 3, dropout: float = 0.35) -> None:
        super().__init__()
        self.stem = conv_bn_relu(1, 16)
        self.body = nn.Sequential(
            ResidualUnit3D(16, 16),
            ResidualUnit3D(16, 32, stride=2),
            ResidualUnit3D(32, 32),
            ResidualUnit3D(32, 64, stride=2),
            ResidualUnit3D(64, 64),
        )
        self.pool = nn.AdaptiveAvgPool3d(1)
        self.features = nn.Linear(64, 1000)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(1000, num_classes)

    def forward(self, x: torch.Tensor, return_features: bool = False):
        x = self.pool(self.body(self.stem(x))).flatten(1)
        features = torch.relu(self.features(x))
        logits = self.classifier(self.dropout(features))
        return (logits, features) if return_features else logits


def build_model(name: str, num_classes: int = 3) -> nn.Module:
    if name == "paper_cnn":
        return PaperCNN3D(num_classes=num_classes)
    if name == "resnet3d":
        return ResNet3D(num_classes=num_classes)
    raise ValueError(f"Unknown model: {name}")

