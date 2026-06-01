import os
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv, global_mean_pool
import pandas as pd
import numpy as np
import joblib
import json

# Define the exact same model architecture
class RCAGNN(torch.nn.Module):
    def __init__(self, num_node_features, num_classes):
        super(RCAGNN, self).__init__()
        self.conv1 = GCNConv(num_node_features, 64)
        self.conv2 = GCNConv(64, 64)
        self.fc = torch.nn.Linear(64, num_classes)

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = global_mean_pool(x, batch)
        x = self.fc(x)
        return F.softmax(x, dim=1)  # Softmax for probabilities

class GNNCritic:
    def __init__(self, model_dir="C:/Users/PowerX/.gemini/antigravity/scratch/models"):
        self.device = torch.device('cpu')
        self.scaler = joblib.load(f"{model_dir}/scaler.pkl")
        self.label_encoder = joblib.load(f"{model_dir}/label_encoder.pkl")
        
        # Determine shapes
        self.num_classes = len(self.label_encoder.classes_)
        # Determine shapes from scaler
        expected_cols = self.scaler.feature_names_in_
        app_cols = [c for c in expected_cols if c.startswith('app_')]
        k8s_cols = [c for c in expected_cols if c.startswith('node_') or c.startswith('container_') or c.startswith('kube_') or c.startswith('pod_')]
        os_cols = [c for c in expected_cols if c.startswith('os_')]
        mist_cols = [c for c in expected_cols if c.startswith('mist_')]
        
        self.max_features = max(len(app_cols), len(k8s_cols), len(os_cols), len(mist_cols))
        
        self.model = RCAGNN(self.max_features, self.num_classes).to(self.device)
        self.model.load_state_dict(torch.load(f"{model_dir}/gnn_rca_model.pt", map_location=self.device))
        self.model.eval()
        
        # 0: App, 1: K8s, 2: OS, 3: Mist
        self.edge_index = torch.tensor([
            [0, 1, 1, 2, 2, 3],
            [1, 0, 2, 1, 3, 2]
        ], dtype=torch.long)

    def pad_features(self, feature_array):
        pad_width = self.max_features - feature_array.shape[1]
        if pad_width > 0:
            return np.pad(feature_array, ((0,0), (0, pad_width)), mode='constant')
        return feature_array

    def evaluate(self, telemetry_dict):
        """
        Takes a dictionary of telemetry and returns mathematical probabilities of faults.
        """
        # Note: telemetry_dict keys must match exactly the columns from the dataset.
        # For this prototype, we'll construct a mock row matching the dataset structure if keys are missing.
        df = pd.DataFrame([telemetry_dict])
        
        # Dummy fill missing columns (in reality, the live script populates all 54 columns)
        expected_cols = self.scaler.feature_names_in_
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0.0
                
        # Order the columns correctly before scaling
        df = df[expected_cols]
        
        # Scale
        scaled_features = self.scaler.transform(df)
        df_scaled = pd.DataFrame(scaled_features, columns=expected_cols)
        
        # Extract per layer
        app_cols = [c for c in expected_cols if c.startswith('app_')]
        k8s_cols = [c for c in expected_cols if c.startswith('node_') or c.startswith('container_') or c.startswith('kube_') or c.startswith('pod_')]
        os_cols = [c for c in expected_cols if c.startswith('os_')]
        mist_cols = [c for c in expected_cols if c.startswith('mist_')]
        
        app_x = self.pad_features(df_scaled[app_cols].values)
        k8s_x = self.pad_features(df_scaled[k8s_cols].values)
        os_x = self.pad_features(df_scaled[os_cols].values)
        mist_x = self.pad_features(df_scaled[mist_cols].values)
        
        x = torch.tensor(np.vstack([app_x[0], k8s_x[0], os_x[0], mist_x[0]]), dtype=torch.float)
        data = Data(x=x, edge_index=self.edge_index, batch=torch.zeros(4, dtype=torch.long))
        
        with torch.no_grad():
            out = self.model(data)
            probs = out[0].numpy()
            
        results = []
        for i, class_name in enumerate(self.label_encoder.classes_):
            results.append({"fault": class_name, "probability": float(probs[i])})
            
        # Sort by highest probability
        results = sorted(results, key=lambda x: x['probability'], reverse=True)
        return results

if __name__ == "__main__":
    # Test Evaluation with an anomalous input (Simulating high OS CPU)
    critic = GNNCritic()
    
    # We create a sample dict representing high CPU at the OS layer
    sample_telemetry = {
        "os_cpu_util_percentage": 98.5,
        "os_load_1m": 12.0,
        "app_request_latency_ms": 2500, # High latency resulting from the CPU
        "node_cpu_seconds_total": 8.5 # High K8s usage as well
    }
    
    print("Evaluating test telemetry...")
    prediction = critic.evaluate(sample_telemetry)
    
    print("\\n=== GNN MATHEMATICAL CRITIC OUTPUT ===")
    for p in prediction[:3]: # Top 3
        print(f"[{p['probability']*100:.2f}%] -> {p['fault']}")
