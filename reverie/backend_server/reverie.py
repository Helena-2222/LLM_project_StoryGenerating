"""
Author: Joon Sung Park (joonspk@stanford.edu)
Modified for DeepSeek Debugging
"""
import json
import numpy
import datetime
import pickle
import time
import math
import os
import shutil
import traceback
import sys
import io

# 强制输出编码，防止中文路径或字符崩溃
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from selenium import webdriver
from global_methods import *
from utils import *
from maze import *
from persona.persona import *

class ReverieServer: 
  def __init__(self, fork_sim_code, sim_code):
    self.fork_sim_code = fork_sim_code
    fork_folder = f"{fs_storage}/{self.fork_sim_code}"
    self.sim_code = sim_code
    sim_folder = f"{fs_storage}/{self.sim_code}"
    
    if not os.path.exists(sim_folder):
        copyanything(fork_folder, sim_folder)

    with open(f"{sim_folder}/reverie/meta.json") as json_file:  
      reverie_meta = json.load(json_file)

    with open(f"{sim_folder}/reverie/meta.json", "w") as outfile: 
      reverie_meta["fork_sim_code"] = fork_sim_code
      outfile.write(json.dumps(reverie_meta, indent=2))

    self.start_time = datetime.datetime.strptime(
                        f"{reverie_meta['start_date']}, 00:00:00",  
                        "%B %d, %Y, %H:%M:%S")
    self.curr_time = datetime.datetime.strptime(reverie_meta['curr_time'], 
                                                "%B %d, %Y, %H:%M:%S")
    self.sec_per_step = reverie_meta['sec_per_step']
    self.maze = Maze(reverie_meta['maze_name'])
    self.step = reverie_meta['step']

    self.personas = dict()
    self.personas_tile = dict()
    
    init_env_file = f"{sim_folder}/environment/{str(self.step)}.json"
    init_env = json.load(open(init_env_file))
    for persona_name in reverie_meta['persona_names']: 
      persona_folder = f"{sim_folder}/personas/{persona_name}"
      p_x = init_env[persona_name]["x"]
      p_y = init_env[persona_name]["y"]
      curr_persona = Persona(persona_name, persona_folder)

      self.personas[persona_name] = curr_persona
      self.personas_tile[persona_name] = (p_x, p_y)
      self.maze.tiles[p_y][p_x]["events"].add(curr_persona.scratch.get_curr_event_and_desc())

    self.server_sleep = 0.1

    curr_sim_code = {"sim_code": self.sim_code}
    with open(f"{fs_temp_storage}/curr_sim_code.json", "w") as outfile: 
      outfile.write(json.dumps(curr_sim_code, indent=2))
    
    curr_step = {"step": self.step}
    with open(f"{fs_temp_storage}/curr_step.json", "w") as outfile: 
      outfile.write(json.dumps(curr_step, indent=2))

  def save(self): 
    sim_folder = f"{fs_storage}/{self.sim_code}"
    reverie_meta = {
        "fork_sim_code": self.fork_sim_code,
        "start_date": self.start_time.strftime("%B %d, %Y"),
        "curr_time": self.curr_time.strftime("%B %d, %Y, %H:%M:%S"),
        "sec_per_step": self.sec_per_step,
        "maze_name": self.maze.maze_name,
        "persona_names": list(self.personas.keys()),
        "step": self.step
    }
    with open(f"{sim_folder}/reverie/meta.json", "w") as outfile: 
      outfile.write(json.dumps(reverie_meta, indent=2))

    for persona_name, persona in self.personas.items(): 
      save_folder = f"{sim_folder}/personas/{persona_name}/bootstrap_memory"
      persona.save(save_folder)

  def start_server(self, int_counter): 
    sim_folder = f"{fs_storage}/{self.sim_code}"
    game_obj_cleanup = dict()

    print(f"开始运行模拟，剩余步数: {int_counter}")

    while (True): 
      if int_counter <= 0: break

      curr_env_file = f"{sim_folder}/environment/{self.step}.json"
      if check_if_file_exists(curr_env_file):
        env_retrieved = False
        try: 
          with open(curr_env_file) as json_file:
            new_env = json.load(json_file)
            env_retrieved = True
        except Exception as e: 
          print(f"读取环境文件失败: {e}")
          traceback.print_exc()
      
        if env_retrieved: 
          try:
            # 清理上一轮物体状态
            for key, val in game_obj_cleanup.items(): 
              self.maze.turn_event_from_tile_idle(key, val)
            game_obj_cleanup = dict()

            # 更新角色位置
            for persona_name, persona in self.personas.items(): 
              curr_tile = self.personas_tile[persona_name]
              new_tile = (new_env[persona_name]["x"], new_env[persona_name]["y"])
              self.personas_tile[persona_name] = new_tile
              self.maze.remove_subject_events_from_tile(persona.name, curr_tile)
              self.maze.add_event_from_tile(persona.scratch.get_curr_event_and_desc(), new_tile)

              if not persona.scratch.planned_path: 
                game_obj_cleanup[persona.scratch.get_curr_obj_event_and_desc()] = new_tile
                self.maze.add_event_from_tile(persona.scratch.get_curr_obj_event_and_desc(), new_tile)
                blank = (persona.scratch.get_curr_obj_event_and_desc()[0], None, None, None)
                self.maze.remove_event_from_tile(blank, new_tile)

            # 核心大脑决策
            movements = {"persona": dict(), "meta": dict()}
            for persona_name, persona in self.personas.items(): 
              print(f"正在计算角色行动: {persona_name}...")
              next_tile, pronunciatio, description = persona.move(
                self.maze, self.personas, self.personas_tile[persona_name], self.curr_time)
              
              movements["persona"][persona_name] = {
                "movement": next_tile,
                "pronunciatio": pronunciatio,
                "description": description,
                "chat": persona.scratch.chat
              }

            movements["meta"]["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")

            # 写入 movement 文件给前端
            curr_move_file = f"{sim_folder}/movement/{self.step}.json"
            with open(curr_move_file, "w") as outfile: 
              outfile.write(json.dumps(movements, indent=2))

            self.step += 1
            self.curr_time += datetime.timedelta(seconds=self.sec_per_step)
            int_counter -= 1
            print(f"完成第 {self.step-1} 步。")
            
          except Exception as e:
            print("!!! 后端运行逻辑崩溃 !!!")
            traceback.print_exc()
            break # 崩溃了就别循环了，直接报错出来

      time.sleep(self.server_sleep)

  def open_server(self): 
    print ("--- 后端服务已启动 ---")
    sim_folder = f"{fs_storage}/{self.sim_code}"

    while True: 
      sim_command = input("Enter option: ").strip()
      try: 
        if sim_command.lower() in ["f", "fin", "save and finish"]: 
          self.save(); break
        elif sim_command.lower() == "exit": 
          shutil.rmtree(sim_folder); break 
        elif sim_command.lower() == "save": 
          self.save()
        elif sim_command[:3].lower() == "run": 
          int_count = int(sim_command.split()[-1])
          self.start_server(int_count) # 修正了原代码中 rs 可能未定义的 bug
        elif "print" in sim_command.lower():
            print("暂不支持调试打印，请先关注 run 逻辑")
      except Exception as e:
        traceback.print_exc()

if __name__ == '__main__':
  origin = input("Enter the name of the forked simulation: ").strip()
  target = input("Enter the name of the new simulation: ").strip()
  rs = ReverieServer(origin, target)
  rs.open_server()