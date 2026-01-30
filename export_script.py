import json
import os

def generate_script(sim_code):
    movement_path = f"storage/{sim_code}/movement/"
    steps = sorted([int(f.split(".")[0]) for f in os.listdir(movement_path)])
    
    for step in steps:
        with open(f"{movement_path}/{step}.json", "r") as f:
            data = json.load(f)
            curr_time = data["meta"]["curr_time"]
            print(f"\n【时间: {curr_time}】")
            
            for name, info in data["persona"].items():
                print(f"{name}: {info['description']}")
                if info.get('chat'):
                    print(f"  └ 对话: {info['chat']}")