from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import pyautogui
import uvicorn
import asyncio
import subprocess
import traceback
import os

app = FastAPI()

async def with_timeout(coro):
    try:
        return await asyncio.wait_for(coro, timeout=5.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Operation timed out")

@app.get("/info")
async def info():
  size = pyautogui.size()
  position = pyautogui.position()
  return {
    "screen": {"width": size.width, "height": size.height},
    "position": {"x": position.x, "y": position.y}
  }

async def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    try:
        with open(destination, "wb") as buffer:
            while chunk := await upload_file.read(1024 * 1024):  # 分块读取（1MB）
                buffer.write(chunk)
        return destination
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

@app.post("/auto/locateOnScreen")
async def locateOnScreen(
    image_file: UploadFile = File(...),
    confidence: float = 0.8,
    grayscale=False,  # 是否转为灰度图加速匹配
    region=None,  # 搜索区域 (left, top, width, height)
    step=1,  # 搜索步长（跳过像素数，加速但可能漏检）
    minSearchTime=0,  # 最小搜索时间（秒），避免过快返回
):
  try:
    file_path = "/tmp/locate_image.png"
    await save_upload_file(image_file, file_path)
    location = pyautogui.locateOnScreen(
      file_path,
      confidence=confidence,
      grayscale=grayscale,
      region=region,
      step=step,
      minSearchTime=minSearchTime
    )
    if location:
      return {"status": "success", "location": {"left": location.left, "top": location.top, "width": location.width, "height": location.height}}
    else:
      raise HTTPException(status_code=500, detail="Image not found")
  except HTTPException as e:
    raise e
  except Exception as e:
    traceback.print_exc()
    raise HTTPException(status_code=500, detail=str(e))

@app.post("/auto/clickImage")
async def clickImage(
    image_file: UploadFile = File(...),
    confidence: float = Form(0.6),
    grayscale: bool = Form(True),  # 是否转为灰度图加速匹配
    region=None,  # 搜索区域 (left, top, width, height)
    step=1,  # 搜索步长（跳过像素数，加速但可能漏检）
    minSearchTime=0,  # 最小搜索时间（秒），避免过快返回
    timeout=10,  # 超时时间（秒），超过则返回未找到
):
  try:
    file_path = "/tmp/locate_image.png"
    await save_upload_file(image_file, file_path)
    print(f"clickImage: confidence={confidence}, grayscale={grayscale}, region={region}, step={step}, minSearchTime={minSearchTime}, timeout={timeout}")
    location = pyautogui.locateOnScreen(
      file_path,
      confidence=confidence,
      grayscale=grayscale,
      region=region,
      step=step,
      minSearchTime=minSearchTime
    )
    if location:
      # location_center_x, location_center_y = pyautogui.center(location)
      location_center_x = int(location.left) + int(location.width / 2)
      location_center_y = int(location.top) + int(location.height / 2)
      print("control_mouse: click at", location, location_center_x, location_center_y)
      pyautogui.click(pyautogui.center(location))
      print("control_mouse: clicked at", location, location_center_x, location_center_y)
      # await control_mouse(MouseCommand(x=location_center_x, y=location_center_y, action="click"))
      return {"status": "success", "location": {"left": int(location.left), "top": int(location.top), "width": int(location.width), "height": int(location.height), "center_x": int(location_center_x), "center_y": int(location_center_y)}}
    else:
      raise HTTPException(status_code=500, detail="Image not found")
  except HTTPException as e:
    raise e
  except Exception as e:
    traceback.print_exc()
    raise HTTPException(status_code=500, detail=str(e))

class ScreenShotCommand(BaseModel):
    region: Optional[List[int]] = None

@app.post("/auto/screenshot")
async def screenshot(command: ScreenShotCommand = None):
  file_path = "/tmp/screenshot.png"
  if command and command.region:
    x, y, width, height = command.region
    screenshot = pyautogui.screenshot(file_path, region=(x, y, width, height))
  else:
    screenshot = pyautogui.screenshot(file_path)

  return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),  # 客户端下载时的文件名
        media_type="image/png"  # MIME 类型（可选，FastAPI 会自动推断）
  )

class HotKeyCommand(BaseModel):
    keys: List[str]

@app.post("/auto/hotkey")
async def hotkey(command: HotKeyCommand):
  pyautogui.hotkey(*command.keys)  # 模拟热键操作
  return {"status": "success", "action": "hotkey", "keys": command.keys}

class KeyboardCommand(BaseModel):
    text: str

@app.post("/auto/keyboard")
async def type_text(command: KeyboardCommand):
    pyautogui.write(command.text)  # 模拟键盘输入
    return {"status": "success", "text": command.text}


# 定义请求数据模型（可选，但推荐）
class MouseCommand(BaseModel):
    x: int
    y: int
    duration: float = 0.25  # 移动持续时间，默认0.25秒
    action: str = "move"  # 可选：move/click/right_click/double_click

@app.post("/auto/mouse")
async def control_mouse(command: MouseCommand):
    try:
        x, y, duration = command.x, command.y, command.duration
        action = command.action.lower()

        # 根据 action 执行不同操作
        if action == "move":
            pyautogui.moveTo(x, y, duration=duration)  # 平滑移动
        elif action == "click":
            pyautogui.click(x=x, y=y, duration=duration)
        elif action == "right_click":
            pyautogui.rightClick(x=x, y=y, duration=duration)
        elif action == "double_click":
            pyautogui.doubleClick(x=x, y=y, duration=duration)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")

        return {"status": "success", "action": action, "x": x, "y": y}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CustomCommand(BaseModel):
    cmd: str
    args: Optional[Dict] = {}

@app.post("/auto/custom")
async def custom(command: CustomCommand):
  try:
    retult = getattr(pyautogui, command.cmd)(**(command.args))
    return {"status": "success", "action": command.cmd, "res": result}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

class XdotoolCommand(BaseModel):
    args: List

@app.post("/auto/xdotool")
async def xdotool(command: XdotoolCommand):
  try:
    retult = subprocess.check_output(["xdotool", *command.args]).decode().strip()
    return {"status": "success", "action": "xdotool", "res": result}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
