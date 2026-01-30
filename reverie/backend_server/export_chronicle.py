import json
import os
import datetime

def export_script(sim_code):
    # --- 路径设置：全部改为 D 盘绝对路径 ---
    base_storage_path = r"D:\LLM_project_StoryGenerating\code\generative_agents-main_deepseek\environment\frontend_server\storage"
    
    # 模拟数据源所在的文件夹
    sim_data_path = os.path.join(base_storage_path, sim_code)
    movement_path = os.path.join(sim_data_path, "movement")
    
    # 编年史输出的目标文件夹
    output_dir = os.path.join(base_storage_path, "script")
    output_file = os.path.join(output_dir, f"{sim_code}_basic_chronicle.md")

    # 自动创建 script 文件夹
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 已创建输出文件夹: {output_dir}")

    if not os.path.exists(movement_path):
        print(f"❌ 错误：找不到路径 {movement_path}")
        return

    # 获取并排序所有步数文件
    steps = sorted([int(f.split(".")[0]) for f in os.listdir(movement_path) if f.endswith(".json")])
    
    print(f"📖 正在扫描 {len(steps)} 个历史片段，生成基础编年史...")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# 模拟基础编年史: {sim_code}\n")
        f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for step in steps:
            file_path = os.path.join(movement_path, f"{step}.json")
            with open(file_path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
                
                curr_time = data["meta"]["curr_time"]
                f.write(f"## 🕒 步数: {step} | 时间: {curr_time}\n")
                
                # 遍历当前步数下所有人的状态
                for p_name, info in data["persona"].items():
                    action = info["description"]
                    f.write(f"- **{p_name}**: {action}\n")
                    
                    # 记录对话
                    if info.get("chat") and info["chat"] is not None:
                        f.write(f"  > 💬 **对话录**:\n")
                        for line in info["chat"]:
                            f.write(f"  > {line[0]}: {line[1]}\n")
                
                f.write("\n" + "-"*30 + "\n\n")

    print(f"✅ 成功！基础编年史已存至: {output_file}")

if __name__ == "__main__":
    # 请确保这里的 "test2" 是你的 sim_code
    export_script("test2")