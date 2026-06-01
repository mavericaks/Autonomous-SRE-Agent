import os
import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.data import Data, DataLoader
from torch_geometric.nn import GCNConv, global_mean_pool
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from imblearn.over_sampling import SMOTE

DATASET_PATH = r"H:\Kolla-Ansible\datasets\telemetry_dataset_gnn_100k_cascading.csv"

print("Loading 100k Dataset...")
df = pd.read_csv(DATASET_PATH)

# Drop timestamp
if 'Timestamp' in df.columns:
    df = df.drop(columns=['Timestamp'])

# Encode Labels
label_encoder = LabelEncoder()
df['Root_Cause_Fault_Label'] = label_encoder.fit_transform(df['Root_Cause_Fault_Label'])
y_all = df['Root_Cause_Fault_Label'].values

print(f"Classes found: {label_encoder.classes_}")

# Define Node Feature columns
app_cols = [c for c in df.columns if c.startswith('app_')]
k8s_cols = [c for c in df.columns if c.startswith('node_') or c.startswith('container_') or c.startswith('kube_') or c.startswith('pod_')]
os_cols = [c for c in df.columns if c.startswith('os_')]
mist_cols = [c for c in df.columns if c.startswith('mist_')]

# Scale features
scaler = StandardScaler()
df[app_cols + k8s_cols + os_cols + mist_cols] = scaler.fit_transform(df[app_cols + k8s_cols + os_cols + mist_cols].fillna(0))

# Standardize node feature size (pad with zeros to match largest layer)
max_features = max(len(app_cols), len(k8s_cols), len(os_cols), len(mist_cols))
print(f"Max node features: {max_features}")

def pad_features(feature_array, max_len):
    pad_width = max_len - feature_array.shape[1]
    if pad_width > 0:
        return np.pad(feature_array, ((0,0), (0, pad_width)), mode='constant')
    return feature_array

app_feats = pad_features(df[app_cols].values, max_features)
k8s_feats = pad_features(df[k8s_cols].values, max_features)
os_feats = pad_features(df[os_cols].values, max_features)
mist_feats = pad_features(df[mist_cols].values, max_features)

# Define Graph Edges (App <-> K8s <-> OS <-> Mist)
# 0: App, 1: K8s, 2: OS, 3: Mist
edge_index = torch.tensor([
    [0, 1, 1, 2, 2, 3], # Source nodes
    [1, 0, 2, 1, 3, 2]  # Target nodes (bidirectional)
], dtype=torch.long)

# Construct PyG Data objects
print("Constructing Graphs...")
graph_data_list = []
for i in range(len(df)):
    x = torch.tensor(np.vstack([app_feats[i], k8s_feats[i], os_feats[i], mist_feats[i]]), dtype=torch.float)
    y = torch.tensor([y_all[i]], dtype=torch.long)
    graph_data_list.append(Data(x=x, edge_index=edge_index, y=y))

# Train/Test Split
train_data, test_data = train_test_split(graph_data_list, test_size=0.2, random_state=42)
train_loader = DataLoader(train_data, batch_size=256, shuffle=True)
test_loader = DataLoader(test_data, batch_size=256, shuffle=False)

# Define GNN Model
class RCAGNN(torch.nn.Module):
    def __init__(self, num_node_features, num_classes):
        super(RCAGNN, self).__init__()
        self.conv1 = GCNConv(num_node_features, 64)
        self.conv2 = GCNConv(64, 64)
        self.fc = torch.nn.Linear(64, num_classes)

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        
        # Graph Convolutions
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        
        # Readout layer (Global Mean Pool across all 4 nodes)
        x = global_mean_pool(x, batch)
        
        # Classifier
        x = self.fc(x)
        return F.log_softmax(x, dim=1)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Training on device: {device}")

model = RCAGNN(num_node_features=max_features, num_classes=len(label_encoder.classes_)).to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
criterion = torch.nn.NLLLoss()

def train():
    model.train()
    total_loss = 0
    for data in train_loader:
        data = data.to(device)
        optimizer.zero_grad()
        out = model(data)
        loss = criterion(out, data.y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(train_loader)

def test(loader):
    model.eval()
    correct = 0
    with torch.no_grad():
        for data in loader:
            data = data.to(device)
            out = model(data)
            pred = out.argmax(dim=1)
            correct += int((pred == data.y).sum())
    return correct / len(loader.dataset)

print("Starting Training (20 Epochs)...")
for epoch in range(1, 21):
    loss = train()
    train_acc = test(train_loader)
    test_acc = test(test_loader)
    print(f'Epoch: {epoch:02d}, Loss: {loss:.4f}, Train Acc: {train_acc:.4f}, Test Acc: {test_acc:.4f}')

# Save Model
os.makedirs("models", exist_ok=True)
torch.save(model.state_dict(), "models/gnn_rca_model.pt")
print("Model saved to models/gnn_rca_model.pt")

import joblib
joblib.dump(scaler, "models/scaler.pkl")
joblib.dump(label_encoder, "models/label_encoder.pkl")
print("Scaler and Encoder saved.")
