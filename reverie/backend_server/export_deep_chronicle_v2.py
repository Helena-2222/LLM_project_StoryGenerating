import json
import os
import datetime

def load_persona_thoughts(base_path, persona_name):
    nodes_path = os.path.join(base_path, "personas", persona_name, "bootstrap_memory", "associative_memory", "nodes.json")
    thoughts = []
    if os.path.exists(nodes_path):
        with open(nodes_path, "r", encoding="utf-8") as f:
            nodes = json.load(f)
            for node_id, node_data in nodes.items():
                if node_data["type"] == "thought":
                    thoughts.append({
                        "created": node_data["created"],
                        "description": node_data["description"],
                        "poignancy": node_data["poignancy"]
                    })
    return sorted(thoughts, key=lambda x: x["created"])

def get_closest_thoughts(thoughts, current_time_dt, window_minutes=60):
    """寻找在当前时间点之前1小时内产生的心理活动"""
    relevant = []
    for t in thoughts:
        try:
            # 同样兼容 nodes.json 中的时间格式解析
            t_time = datetime.datetime.strptime(t["created"], "%B %d, %Y, %H:%M:%S")
            if t_time <= current_time_dt and (current_time_dt - t_time).total_seconds() < window_minutes * 60:
                relevant.append(t)
        except:
            continue
    return relevant[-3:]

def export_deep_script(sim_code):
    base_storage_path = r"D:\LLM_project_StoryGenerating\code\generative_agents-main_deepseek\environment\frontend_server\storage"
    sim_data_path = os.path.join(base_storage_path, sim_code)
    movement_path = os.path.join(sim_data_path, "movement")
    output_dir = os.path.join(base_storage_path, "script")
    output_file = os.path.join(output_dir, f"{sim_code}_30min_deep_chronicle.md")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(movement_path):
        print(f"❌ 错误：找不到路径 {movement_path}")
        return

    persona_names = [d for d in os.listdir(os.path.join(sim_data_path, "personas"))]
    all_thoughts = {name: load_persona_thoughts(sim_data_path, name) for name in persona_names}
    steps = sorted([int(f.split(".")[0]) for f in os.listdir(movement_path) if f.endswith(".json")])
    
    print(f"🚀 开始生成 30 分钟间隔的深度编年史 (兼容英文时间格式)...")

    last_recorded_time = None
    # 修改后的时间解析格式：对应 'February 13, 2023, 00:00:00'
    TIME_FORMAT = "%B %d, %Y, %H:%M:%S"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# 🎭 深度剧情编年史 (30分钟精简版): {sim_code}\n")
        f.write(f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for step in steps:
            file_path = os.path.join(movement_path, f"{step}.json")
            with open(file_path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
                curr_time_str = data["meta"]["curr_time"]
                
                # 核心修复点：使用正确的时间格式解析
                try:
                    curr_time_dt = datetime.datetime.strptime(curr_time_str, TIME_FORMAT)
                except ValueError:
                    # 如果还有微小差异，尝试容错处理
                    print(f"⚠️ 警告: 步数 {step} 时间格式无法解析: {curr_time_str}")
                    continue

                has_chat = False
                for p_info in data["persona"].values():
                    if p_info.get("chat"):
                        has_chat = True
                        break

                if (last_recorded_time is None or 
                    (curr_time_dt - last_recorded_time).total_seconds() >= 30 * 60 or 
                    has_chat):
                    
                    f.write(f"### 🕒 {curr_time_str} (Step: {step})\n")
                    if has_chat and last_recorded_time and (curr_time_dt - last_recorded_time).total_seconds() < 30 * 60:
                        f.write("> *[触发突发对话记录]* \n")

                    for p_name, info in data["persona"].items():
                        action = info["description"]
                        f.write(f"#### 👤 {p_name}\n")
                        f.write(f"- 🎬 **行动**: {action}\n")
                        
                        # 心理活动匹配
                        p_thoughts = get_closest_thoughts(all_thoughts.get(p_name, []), curr_time_dt)
                        if p_thoughts:
                            f.write(f"- 🧠 **近期内心戏**:\n")
                            for t in p_thoughts:
                                f.write(f"  * *“{t['description']}”* (Poignancy: {t['poignancy']})\n")
                        
                        if info.get("chat") and info["chat"]:
                            f.write(f"- 💬 **现场对话**:\n")
                            for line in info["chat"]:
                                f.write(f"  > **{line[0]}**: {line[1]}\n")
                        f.write("\n")
                    
                    f.write("\n" + "---" * 5 + "\n\n")
                    last_recorded_time = curr_time_dt

    print(f"✅ 搞定！编年史已存至: {output_file}")

if __name__ == "__main__":
    export_deep_script("test_magic1")