import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
import pandas as pd
import numpy as np
import joblib
from collections import deque

WINDOW_SIZE = 5

class RCA_STGNN(nn.Module):
    def __init__(self, num_node_features, num_classes, window_size):
        super(RCA_STGNN, self).__init__()
        self.conv1 = GCNConv(num_node_features, 64)
        self.conv2 = GCNConv(64, 64)
        self.lstm = nn.LSTM(input_size=64, hidden_size=64, num_layers=1, batch_first=True)
        self.fc = nn.Linear(64, num_classes)

    def forward(self, x_batch, batch_edges):
        batch_size, window_size, num_nodes, features = x_batch.shape
        x_flat = x_batch.view(batch_size * window_size * num_nodes, features)
        
        out = self.conv1(x_flat, batch_edges)
        out = F.relu(out)
        out = self.conv2(out, batch_edges)
        out = F.relu(out)
        
        out = out.view(batch_size * window_size, num_nodes, 64)
        out = out.mean(dim=1)
        out = out.view(batch_size, window_size, 64)
        
        lstm_out, _ = self.lstm(out)
        last_out = lstm_out[:, -1, :]
        logits = self.fc(last_out)
        return F.softmax(logits, dim=1)

class STGNNCritic:
    def __init__(self, model_dir=r"H:\Kolla-Ansible\ml_models\models"):
        self.device = torch.device('cpu')
        self.scaler = joblib.load(f"{model_dir}/scaler.pkl")
        self.label_encoder = joblib.load(f"{model_dir}/label_encoder.pkl")
        
        expected_cols = self.scaler.feature_names_in_
        app_cols = [c for c in expected_cols if c.startswith('app_')]
        k8s_cols = [c for c in expected_cols if c.startswith('node_') or c.startswith('container_') or c.startswith('kube_') or c.startswith('pod_')]
        os_cols = [c for c in expected_cols if c.startswith('os_')]
        mist_cols = [c for c in expected_cols if c.startswith('mist_')]
        self.max_features = max(len(app_cols), len(k8s_cols), len(os_cols), len(mist_cols))
        
        self.model = RCA_STGNN(self.max_features, len(self.label_encoder.classes_), WINDOW_SIZE).to(self.device)
        self.model.load_state_dict(torch.load(f"{model_dir}/stgnn_rca_model.pt", map_location=self.device))
        self.model.eval()
        
        self.base_edge_index = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]], dtype=torch.long)
        
        # Build block diagonal edge index for the single batch of size 1 and window size 5
        edges_list = []
        for i in range(1 * WINDOW_SIZE):
            edges_list.append(self.base_edge_index + (i * 4)) # 4 nodes
        self.batch_edges = torch.cat(edges_list, dim=1).to(self.device)
        
        # Stateful Buffer
        self.telemetry_buffer = deque(maxlen=WINDOW_SIZE)

    def pad_features(self, feature_array):
        pad_width = self.max_features - feature_array.shape[1]
        if pad_width > 0:
            return np.pad(feature_array, ((0,0), (0, pad_width)), mode='constant')
        return feature_array

    def ingest_telemetry(self, telemetry_dict):
        """Adds a single timestep snapshot to the stateful buffer."""
        df = pd.DataFrame([telemetry_dict])
        expected_cols = self.scaler.feature_names_in_
        for col in expected_cols:
            if col not in df.columns: df[col] = 0.0
        df = df[expected_cols]
        
        scaled_features = self.scaler.transform(df)
        df_scaled = pd.DataFrame(scaled_features, columns=expected_cols)
        
        app_cols = [c for c in expected_cols if c.startswith('app_')]
        k8s_cols = [c for c in expected_cols if c.startswith('node_') or c.startswith('container_') or c.startswith('kube_') or c.startswith('pod_')]
        os_cols = [c for c in expected_cols if c.startswith('os_')]
        mist_cols = [c for c in expected_cols if c.startswith('mist_')]
        
        app_x = self.pad_features(df_scaled[app_cols].values)[0]
        k8s_x = self.pad_features(df_scaled[k8s_cols].values)[0]
        os_x = self.pad_features(df_scaled[os_cols].values)[0]
        mist_x = self.pad_features(df_scaled[mist_cols].values)[0]
        
        # Shape: [4, max_features]
        spatial_graph = np.vstack([app_x, k8s_x, os_x, mist_x])
        self.telemetry_buffer.append(spatial_graph)

    def evaluate(self):
        """Evaluates the buffer using the LSTM and returns probabilities."""
        if len(self.telemetry_buffer) < WINDOW_SIZE:
            return [{"fault": "Buffering...", "probability": 0.0}]
            
        # Shape: [1, 5, 4, max_features]
        x_window = np.array(self.telemetry_buffer, dtype=np.float32)
        x_batch = torch.tensor(x_window).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            probs = self.model(x_batch, self.batch_edges)[0].numpy()
            
        results = []
        for i, class_name in enumerate(self.label_encoder.classes_):
            results.append({"fault": class_name, "probability": float(probs[i])})
            
        results = sorted(results, key=lambda x: x['probability'], reverse=True)
        return results

if __name__ == "__main__":
    critic = STGNNCritic()
    
    # Simulate a slow memory leak over 5 ticks
    for i in range(5):
        mem_leak_sim = {
            "app_request_latency_ms": 200 + (i * 200),
            "os_memory_usage_mb": 8000 + (i * 1000)
        }
        critic.ingest_telemetry(mem_leak_sim)
        print(f"Ingested Tick {i+1}...")
        
    print("\\n=== ST-GNN MATHEMATICAL CRITIC OUTPUT ===")
    preds = critic.evaluate()
    for p in preds[:3]:
        print(f"[{p['probability']*100:.2f}%] -> {p['fault']}")
