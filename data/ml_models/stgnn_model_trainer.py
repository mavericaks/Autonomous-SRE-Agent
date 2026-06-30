import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



DATASET_PATH = os.path.join(BASE_DIR, "\datasets\telemetry_dataset_gnn_20k_cascading.csv")
WINDOW_SIZE = 5

print(f"Loading 100k Dataset for ST-GNN (Window Size: {WINDOW_SIZE})...")
df = pd.read_csv(DATASET_PATH)

if 'Timestamp' in df.columns:
    df = df.drop(columns=['Timestamp'])

label_encoder = LabelEncoder()
df['Root_Cause_Fault_Label'] = label_encoder.fit_transform(df['Root_Cause_Fault_Label'])
labels_all = df['Root_Cause_Fault_Label'].values

print(f"Classes found: {label_encoder.classes_}")

app_cols = [c for c in df.columns if c.startswith('app_')]
k8s_cols = [c for c in df.columns if c.startswith('node_') or c.startswith('container_') or c.startswith('kube_') or c.startswith('pod_')]
os_cols = [c for c in df.columns if c.startswith('os_')]
mist_cols = [c for c in df.columns if c.startswith('mist_')]
all_feats = app_cols + k8s_cols + os_cols + mist_cols

scaler = StandardScaler()
df[all_feats] = scaler.fit_transform(df[all_feats].fillna(0))

max_features = max(len(app_cols), len(k8s_cols), len(os_cols), len(mist_cols))

def pad_features(feature_array, max_len):
    pad_width = max_len - feature_array.shape[1]
    if pad_width > 0:
        return np.pad(feature_array, ((0,0), (0, pad_width)), mode='constant')
    return feature_array

app_x = pad_features(df[app_cols].values, max_features)
k8s_x = pad_features(df[k8s_cols].values, max_features)
os_x = pad_features(df[os_cols].values, max_features)
mist_x = pad_features(df[mist_cols].values, max_features)

print("Constructing Temporal Sliding Windows...")
# Create spatial graphs [num_nodes=4, max_features] per timestamp
spatial_graphs = np.stack([app_x, k8s_x, os_x, mist_x], axis=1) # Shape: [total_rows, 4, max_features]

X_windows = []
y_windows = []

# Sliding window
for i in range(len(df) - WINDOW_SIZE):
    X_windows.append(spatial_graphs[i:i+WINDOW_SIZE])
    # Label of the window is the label of the LAST timestamp in the window
    y_windows.append(labels_all[i+WINDOW_SIZE-1])

X_windows = np.array(X_windows, dtype=np.float32)
y_windows = np.array(y_windows, dtype=np.int64)

class STGNNDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X)
        self.y = torch.tensor(y)
    def __len__(self):
        return len(self.X)
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

X_train, X_test, y_train, y_test = train_test_split(X_windows, y_windows, test_size=0.2, random_state=42)
train_loader = DataLoader(STGNNDataset(X_train, y_train), batch_size=256, shuffle=True)
test_loader = DataLoader(STGNNDataset(X_test, y_test), batch_size=256, shuffle=False)

# Adjacency
edge_index = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]], dtype=torch.long)

class RCA_STGNN(nn.Module):
    def __init__(self, num_node_features, num_classes, window_size):
        super(RCA_STGNN, self).__init__()
        # Spatial Graph Convolutions
        self.conv1 = GCNConv(num_node_features, 64)
        self.conv2 = GCNConv(64, 64)
        
        # Temporal LSTM (input size is 64 because GCN output per node is 64, global pooled to 64)
        self.lstm = nn.LSTM(input_size=64, hidden_size=64, num_layers=1, batch_first=True)
        
        # Classifier
        self.fc = nn.Linear(64, num_classes)
        self.edge_index = edge_index

    def forward(self, x_batch):
        # x_batch shape: [batch_size, window_size, 4, max_features]
        batch_size, window_size, num_nodes, features = x_batch.shape
        
        # We need to process each graph in the batch and window.
        # Flatten batch and window to process all spatial graphs at once
        x_flat = x_batch.view(batch_size * window_size, num_nodes, features)
        
        # We process each graph. GCNConv expects [num_nodes_total, features] and an edge_index.
        # So we flatten node dimension as well
        x_nodes = x_flat.view(batch_size * window_size * num_nodes, features)
        
        # Create block diagonal edge index for the whole batch
        # edge_index is [2, E]. We repeat it batch_size * window_size times with offsets
        edges_list = []
        for i in range(batch_size * window_size):
            edges_list.append(self.edge_index + (i * num_nodes))
        batch_edges = torch.cat(edges_list, dim=1).to(x_batch.device)
        
        # Graph Convolutions (Spatial Extraction)
        out = self.conv1(x_nodes, batch_edges)
        out = F.relu(out)
        out = self.conv2(out, batch_edges)
        out = F.relu(out)
        
        # Reshape back to [batch*window, num_nodes, 64]
        out = out.view(batch_size * window_size, num_nodes, 64)
        
        # Global mean pool across the 4 nodes for each graph
        out = out.mean(dim=1) # Shape: [batch_size * window_size, 64]
        
        # Reshape for LSTM (Temporal Extraction)
        out = out.view(batch_size, window_size, 64)
        
        # Pass through LSTM
        lstm_out, (hn, cn) = self.lstm(out)
        
        # Take the hidden state of the final time step in the window
        last_out = lstm_out[:, -1, :] # Shape: [batch_size, 64]
        
        # Classifier
        logits = self.fc(last_out)
        return F.log_softmax(logits, dim=1)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Training on device: {device}")

model = RCA_STGNN(num_node_features=max_features, num_classes=len(label_encoder.classes_), window_size=WINDOW_SIZE).to(device)
model.edge_index = edge_index.to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
criterion = nn.NLLLoss()

def train():
    model.train()
    total_loss = 0
    for X, y in train_loader:
        X, y = X.to(device), y.to(device)
        optimizer.zero_grad()
        out = model(X)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(train_loader)

def test(loader):
    model.eval()
    correct = 0
    with torch.no_grad():
        for X, y in loader:
            X, y = X.to(device), y.to(device)
            out = model(X)
            pred = out.argmax(dim=1)
            correct += int((pred == y).sum())
    return correct / len(loader.dataset)

print("Starting ST-GNN Training (15 Epochs)...")
for epoch in range(1, 16):
    loss = train()
    train_acc = test(train_loader)
    test_acc = test(test_loader)
    print(f'Epoch: {epoch:02d}, Loss: {loss:.4f}, Train Acc: {train_acc:.4f}, Test Acc: {test_acc:.4f}')

os.makedirs("models", exist_ok=True)
torch.save(model.state_dict(), "models/stgnn_rca_model.pt")
print("Model saved to models/stgnn_rca_model.pt")

joblib.dump(scaler, "models/scaler.pkl")
joblib.dump(label_encoder, "models/label_encoder.pkl")
print("Scaler and Encoder saved.")
