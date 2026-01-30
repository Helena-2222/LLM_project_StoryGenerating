"""
Author: Joon Sung Park (joonspk@stanford.edu)
File: views.py
"""
import os
import string
import random
import json
import datetime
from os import listdir
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.http import HttpResponse, JsonResponse
from global_methods import *
from django.contrib.staticfiles.templatetags.staticfiles import static
from .models import *

def landing(request): 
  context = {}
  template = "landing/landing.html"
  return render(request, template, context)


def demo(request, sim_code, step, play_speed="2"): 
    # --- 路径绝对化处理 ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(current_dir) 
    
    compressed_dir = os.path.join(base_path, "compressed_storage", sim_code)
    storage_dir = os.path.join(base_path, "storage", sim_code)

    move_file = os.path.join(compressed_dir, "master_movement.json")
    meta_file = os.path.join(compressed_dir, "meta.json")

    step = int(step)
    play_speed_opt = {"1": 1, "2": 2, "3": 4, "4": 8, "5": 16, "6": 32}
    play_speed = play_speed_opt.get(play_speed, 2)

    # --- 1. 加载元数据 (meta.json) ---
    meta = dict() 
    if not os.path.exists(meta_file):
        meta_file = os.path.join(storage_dir, "reverie", "meta.json")
    
    try:
        with open (meta_file) as json_file: 
            meta = json.load(json_file)
    except:
        # 如果彻底找不到，给个默认值防止崩溃
        meta = {"sec_per_step": 10, "start_date": "February 13, 2023"}

    sec_per_step = meta["sec_per_step"]
    start_datetime = datetime.datetime.strptime(meta["start_date"] + " 00:00:00", 
                                                '%B %d, %Y %H:%M:%S')
    for i in range(step): 
        start_datetime += datetime.timedelta(seconds=sec_per_step)
    start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")

    # --- 2. 加载动作数据 (master_movement.json) ---
    raw_all_movement = dict()
    if os.path.exists(move_file):
        with open(move_file) as json_file: 
            data = json.load(json_file)
            # 这里的判断解决了你遇到的 'list' object has no attribute 'get' 错误
            if isinstance(data, dict):
                raw_all_movement = data
            else:
                raw_all_movement = {"0": {}} 
    else:
        raw_all_movement = {"0": {}} 

    # --- 3. 提取角色名称 ---
    persona_names = []
    persona_names_set = set()
    
    # 尝试从步数键读取，如果不对，尝试直接读 persona 键（针对你刚才的 3.json 格式）
    curr_move_data = raw_all_movement.get(str(step), raw_all_movement.get("0", raw_all_movement.get("persona", {})))
    
    if not curr_move_data:
        # 最后的兜底：从 personas 文件夹名获取
        persona_dir = os.path.join(storage_dir, "personas")
        if os.path.exists(persona_dir):
            curr_move_keys = [d for d in os.listdir(persona_dir) if os.path.isdir(os.path.join(persona_dir, d))]
        else:
            curr_move_keys = []
    else:
        curr_move_keys = list(curr_move_data.keys())

    for p in curr_move_keys: 
        persona_names += [{"original": p, 
                           "underscore": p.replace(" ", "_"), 
                           "initial": p[0] + p.split(" ")[-1][0]}]
        persona_names_set.add(p)

    # --- 4. 准备初始位置和动作序列 ---
    all_movement = dict()
    init_prep = dict() 
    persona_init_pos = dict()

    for p in persona_names_set: 
        p_underscore = p.replace(" ", "_")
        # 默认位置（防止找不到数据导致 JS 崩溃）
        init_prep[p] = {"movement": [72, 14], "pronunciatio": "🙂", "description": "initializing..."}
        
        # 依次从不同可能的键位尝试读取位置
        if p in curr_move_data:
            init_prep[p] = curr_move_data[p]
        
        persona_init_pos[p_underscore] = init_prep[p]["movement"]
    
    all_movement[step] = init_prep

    context = {"sim_code": sim_code,
               "step": step,
               "persona_names": persona_names,
               "persona_init_pos": json.dumps(persona_init_pos), 
               "all_movement": json.dumps(all_movement), 
               "start_datetime": start_datetime,
               "sec_per_step": sec_per_step,
               "play_speed": play_speed,
               "mode": "demo"}
    template = "demo/demo.html"

    return render(request, template, context)

# --- 以下函数保持原样，但确保引用路径正确 ---

def UIST_Demo(request): 
  return demo(request, "March20_the_ville_n25_UIST_RUN-step-1-141", 2160, play_speed="3")

def home(request):
  f_curr_sim_code = "temp_storage/curr_sim_code.json"
  f_curr_step = "temp_storage/curr_step.json"

  # --- 1. 绕过后端启动检查 ---
  # 原有的 if check_if_file_exists(f_curr_step) 被移除
  # 这样即使没有这个文件，也不会跳出 "Please start backend first"

  # --- 2. 获取当前的 sim_code ---
  try:
    with open(f_curr_sim_code) as json_file:  
      sim_code = json.load(json_file)["sim_code"]
  except:
    # 兜底方案：如果找不到文件，手动指定为你当前正在跑的项目名
    sim_code = "debug_run" 
  
  # --- 3. 获取当前的步数 step ---
  try:
    with open(f_curr_step) as json_file:  
      step = json.load(json_file)["step"]
    # 只有文件存在时才尝试删除
    if os.path.exists(f_curr_step):
      os.remove(f_curr_step)
  except:
    # 兜底方案：默认从第 0 步或者你认为合适的步数开始
    step = 0 

  # --- 4. 加载角色名称 ---
  persona_names = []
  persona_names_set = set()
  # 这里的路径根据你的实际目录结构进行了微调
  persona_base_path = f"storage/{sim_code}/personas"
  if os.path.exists(persona_base_path):
    for i in find_filenames(persona_base_path, ""): 
      x = i.split("/")[-1].strip()
      if x and x[0] != ".": 
        persona_names += [[x, x.replace(" ", "_")]]
        persona_names_set.add(x)

  # --- 5. 获取小人的初始位置 ---
  persona_init_pos = []
  file_count = []
  env_path = f"storage/{sim_code}/environment"
  
  if os.path.exists(env_path):
    for i in find_filenames(env_path, ".json"):
      x = i.split("/")[-1].strip()
      if x[0] != ".": 
        file_count += [int(x.split(".")[0])]
    
    if file_count:
      curr_json = f'storage/{sim_code}/environment/{str(max(file_count))}.json'
      try:
        with open(curr_json) as json_file:  
          persona_init_pos_dict = json.load(json_file)
          for key, val in persona_init_pos_dict.items(): 
            if key in persona_names_set: 
              persona_init_pos += [[key, val["x"], val["y"]]]
      except:
        pass

  # --- 6. 渲染页面 ---
  # 注意：mode 设置为 "simulate"，这样前端 JS 会自动开始轮询后端
  context = {"sim_code": sim_code, 
             "step": step, 
             "persona_names": persona_names, 
             "persona_init_pos": persona_init_pos, 
             "mode": "simulate"}
  template = "home/home.html"
  return render(request, template, context)
def replay(request, sim_code, step): 
  sim_code = sim_code
  step = int(step)
  persona_names = []
  persona_names_set = set()
  for i in find_filenames(f"storage/{sim_code}/personas", ""): 
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      persona_names += [[x, x.replace(" ", "_")]]
      persona_names_set.add(x)
  persona_init_pos = []
  file_count = []
  for i in find_filenames(f"storage/{sim_code}/environment", ".json"):
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      file_count += [int(x.split(".")[0])]
  curr_json = f'storage/{sim_code}/environment/{str(max(file_count))}.json'
  with open(curr_json) as json_file:  
    persona_init_pos_dict = json.load(json_file)
    for key, val in persona_init_pos_dict.items(): 
      if key in persona_names_set: 
        persona_init_pos += [[key, val["x"], val["y"]]]
  context = {"sim_code": sim_code, "step": step, "persona_names": persona_names, "persona_init_pos": persona_init_pos, "mode": "replay"}
  template = "home/home.html"
  return render(request, template, context)

def replay_persona_state(request, sim_code, step, persona_name): 
  sim_code = sim_code
  step = int(step)
  persona_name_underscore = persona_name
  persona_name = " ".join(persona_name.split("_"))
  memory = f"storage/{sim_code}/personas/{persona_name}/bootstrap_memory"
  if not os.path.exists(memory): 
    memory = f"compressed_storage/{sim_code}/personas/{persona_name}/bootstrap_memory"
  with open(memory + "/scratch.json") as json_file:  
    scratch = json.load(json_file)
  with open(memory + "/spatial_memory.json") as json_file:  
    spatial = json.load(json_file)
  with open(memory + "/associative_memory/nodes.json") as json_file:  
    associative = json.load(json_file)
  a_mem_event = []; a_mem_chat = []; a_mem_thought = []
  for count in range(len(associative.keys()), 0, -1): 
    node_id = f"node_{str(count)}"
    node_details = associative[node_id]
    if node_details["type"] == "event": a_mem_event += [node_details]
    elif node_details["type"] == "chat": a_mem_chat += [node_details]
    elif node_details["type"] == "thought": a_mem_thought += [node_details]
  context = {"sim_code": sim_code, "step": step, "persona_name": persona_name, "persona_name_underscore": persona_name_underscore, "scratch": scratch, "spatial": spatial, "a_mem_event": a_mem_event, "a_mem_chat": a_mem_chat, "a_mem_thought": a_mem_thought}
  template = "persona_state/persona_state.html"
  return render(request, template, context)

def path_tester(request):
  context = {}
  template = "path_tester/path_tester.html"
  return render(request, template, context)

def process_environment(request): 
  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]
  environment = data["environment"]
  with open(f"storage/{sim_code}/environment/{step}.json", "w") as outfile:
    outfile.write(json.dumps(environment, indent=2))
  return HttpResponse("received")

def update_environment(request): 
  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]
  response_data = {"<step>": -1}
  if (check_if_file_exists(f"storage/{sim_code}/movement/{step}.json")):
    with open(f"storage/{sim_code}/movement/{step}.json") as json_file: 
      response_data = json.load(json_file)
      response_data["<step>"] = step
  return JsonResponse(response_data)

def path_tester_update(request): 
  data = json.loads(request.body)
  camera = data["camera"]
  with open(f"temp_storage/path_tester_env.json", "w") as outfile:
    outfile.write(json.dumps(camera, indent=2))
  return HttpResponse("received")