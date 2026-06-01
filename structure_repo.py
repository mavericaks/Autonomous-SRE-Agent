import os
import shutil

TARGET_DIR = r"h:\Kolla-Ansible"

def move_dir(src_name, dest_path, dest_name=None):
    src = os.path.join(TARGET_DIR, src_name)
    if not os.path.exists(src):
        return
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    
    final_dest_name = dest_name if dest_name else src_name
    dest = os.path.join(dest_path, final_dest_name)
    
    try:
        shutil.move(src, dest)
        print(f"Moved {src_name} to {dest}")
    except Exception as e:
        print(f"Failed to move {src_name}: {e}")

def move_files(src_names, dest_path):
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    for src_name in src_names:
        src = os.path.join(TARGET_DIR, src_name)
        if os.path.exists(src):
            try:
                shutil.move(src, os.path.join(dest_path, src_name))
                print(f"Moved {src_name} to {dest_path}")
            except Exception as e:
                print(f"Failed to move {src_name}: {e}")

def main():
    # src/
    src_dir = os.path.join(TARGET_DIR, "src")
    move_dir("ai-agent", src_dir, "ai_agent")
    move_dir("chaos_engineering", src_dir)
    move_dir("kubernetes_management", src_dir, "kubernetes_mgmt")
    move_dir("utils", src_dir)

    # data/
    data_dir = os.path.join(TARGET_DIR, "data")
    move_dir("datasets", data_dir)
    move_dir("dataset_generation", data_dir)
    move_dir("models", data_dir)
    move_dir("ml_models", data_dir)

    # docs/
    docs_dir = os.path.join(TARGET_DIR, "docs")
    reports_dir = os.path.join(docs_dir, "reports")
    chapters_dir = os.path.join(docs_dir, "chapters")
    move_dir("Report_Chapters", docs_dir, "chapters")
    move_dir("Research Papers for Minor Project", docs_dir, "papers")
    move_files(["Autonomous_AI_SRE_Final_Report.md", "MINI Project Final Report.pdf"], reports_dir)

    # deployment/
    deploy_dir = os.path.join(TARGET_DIR, "deployment")
    move_dir("openstack_setup", deploy_dir)
    move_dir("openstack-compute1", deploy_dir)
    move_dir("openstack-compute2", deploy_dir)
    move_dir("openstack-controller", deploy_dir)

    # scripts/
    scripts_dir = os.path.join(TARGET_DIR, "scripts")
    move_files(["check_openstack.py", "get_horizon_logs.py"], scripts_dir)
    
    print("Restructuring completed.")

if __name__ == '__main__':
    main()
