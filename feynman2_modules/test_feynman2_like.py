import os
import time
import math
import psutil
import random

import torch
import torch.nn as nn
import torch.optim as optim


# ========== 配置区域：你可以在这里调大/调小任务规模 ==========
N_SAMPLES = 50000      # 数据点数量，越大越耗时/耗内存
N_EPOCHS = 200         # 训练轮数
BATCH_SIZE = 1024      # 批大小
HIDDEN_WIDTH = 256     # 隐藏层宽度，越大越耗算力
N_HIDDEN_LAYERS = 4    # 隐藏层数
USE_GPU = torch.cuda.is_available()  # 如果有 GPU 就用，没有就用 CPU
# =======================================================


def get_mem_mb():
    """当前进程占用的内存（MB）"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def print_device_info(device):
    print(f"使用设备: {device}")
    print(f"初始内存: {get_mem_mb():.2f} MB")
    if device.type == "cuda":
        print(f"GPU 总显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        print(f"GPU 初始占用: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")


# 构造一个“类费曼”物理方程：f(x, y) = x^2 * sin(y) + 0.1*x
def ground_truth(xy):
    x = xy[:, 0]
    y = xy[:, 1]
    return x**2 * torch.sin(y) + 0.1 * x


def make_dataset(n_samples):
    torch.manual_seed(0)
    random.seed(0)

    # x ~ Uniform(-2, 2), y ~ Uniform(0, 2π)
    x = torch.rand(n_samples) * 4 - 2
    y = torch.rand(n_samples) * 2 * math.pi
    xy = torch.stack([x, y], dim=1)
    z = ground_truth(xy)

    # 加一点噪声，模拟真实实验数据
    noise = 0.01 * torch.randn_like(z)
    z_noisy = z + noise

    return xy, z_noisy


class FeynmanLikeNet(nn.Module):
    """一个多层前馈网络，模拟 Feynman2.0 中用 NN 近似函数的部分"""

    def __init__(self, in_dim=2, hidden_width=256, n_hidden_layers=4, out_dim=1):
        super().__init__()
        layers = []

        # 输入层
        layers.append(nn.Linear(in_dim, hidden_width))
        layers.append(nn.Tanh())

        # 中间若干隐层
        for _ in range(n_hidden_layers - 1):
            layers.append(nn.Linear(hidden_width, hidden_width))
            layers.append(nn.Tanh())

        # 输出层
        layers.append(nn.Linear(hidden_width, out_dim))

        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def train():
    device = torch.device("cuda" if USE_GPU else "cpu")
    print_device_info(device)

    # 准备数据
    print("\n[1/3] 生成数据集...")
    t0 = time.time()
    X, y = make_dataset(N_SAMPLES)
    X = X.to(device)
    y = y.to(device).unsqueeze(1)  # (N, 1)
    print(f"数据集大小: {N_SAMPLES} 样本")
    print(f"生成数据耗时: {time.time() - t0:.2f} 秒")
    print(f"生成数据后内存: {get_mem_mb():.2f} MB")

    # 构造模型
    print("\n[2/3] 构建模型...")
    model = FeynmanLikeNet(
        in_dim=2,
        hidden_width=HIDDEN_WIDTH,
        n_hidden_layers=N_HIDDEN_LAYERS,
        out_dim=1,
    ).to(device)

    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    print(model)
    num_params = sum(p.numel() for p in model.parameters())
    print(f"参数量: {num_params / 1e6:.3f} M")

    print(f"构建模型后内存: {get_mem_mb():.2f} MB")
    if device.type == "cuda":
        print(f"GPU 当前占用: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")

    # 训练
    print("\n[3/3] 开始训练...")
    train_start = time.time()
    best_loss = float("inf")

    n_batches = math.ceil(N_SAMPLES / BATCH_SIZE)

    for epoch in range(1, N_EPOCHS + 1):
        perm = torch.randperm(N_SAMPLES, device=device)
        X_shuffled = X[perm]
        y_shuffled = y[perm]

        epoch_loss = 0.0

        for i in range(n_batches):
            start = i * BATCH_SIZE
            end = min((i + 1) * BATCH_SIZE, N_SAMPLES)

            xb = X_shuffled[start:end]
            yb = y_shuffled[start:end]

            optimizer.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, yb)
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item() * (end - start)

        epoch_loss /= N_SAMPLES
        best_loss = min(best_loss, epoch_loss)

        if epoch % 20 == 0 or epoch == 1:
            elapsed = time.time() - train_start
            mem = get_mem_mb()
            if device.type == "cuda":
                gpu_mem = torch.cuda.memory_allocated() / 1024**2
                print(
                    f"Epoch {epoch:4d}/{N_EPOCHS} | "
                    f"loss={epoch_loss:.4e} | "
                    f"时间累计={elapsed:.1f}s | "
                    f"内存={mem:.1f}MB | GPU={gpu_mem:.1f}MB"
                )
            else:
                print(
                    f"Epoch {epoch:4d}/{N_EPOCHS} | "
                    f"loss={epoch_loss:.4e} | "
                    f"时间累计={elapsed:.1f}s | "
                    f"内存={mem:.1f}MB"
                )

    total_time = time.time() - train_start
    print("\n训练结束。")
    print(f"最佳 loss: {best_loss:.4e}")
    print(f"总训练时间: {total_time:.2f} 秒")
    print(f"最终内存占用: {get_mem_mb():.2f} MB")
    if device.type == "cuda":
        print(f"GPU 最终占用: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")

if __name__ == "__main__":
    train()