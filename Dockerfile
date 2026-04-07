FROM ghcr.io/browserless/chromium:latest

USER root

RUN apt-get update && apt-get install -y \
    xvfb x11vnc novnc websockify scrot python3-tk python3-dev gnome-screenshot python3-typing-extensions xdotool \
    && rm -rf /var/lib/apt/lists/*

RUN pip install fastapi uvicorn pyautogui pydantic python-multipart opencv-python --ignore-installed --break-system-packages -i https://pypi.tuna.tsinghua.edu.cn/simple

USER blessuser

COPY autogui_serve.py /usr/src/app/autogui_serve.py

RUN sed -i.bak '/export DISPLAY=:99/a   x11vnc -display :99 -forever -listen 0.0.0.0 -rfbport 6080 &\n  if [ ! -f /home/blessuser/.Xauthority ] ; then \n  touch /home/blessuser/.Xauthority\n    chmod 600 /home/blessuser/.Xauthority\n    xauth generate :99 . trusted\n  fi\n  python ./autogui_serve.py & ' ./scripts/start.sh && \
    sed -i 's/-nolisten unix/+extension XTEST/g;s/1024x768x16/1920x1080x16/g' ./scripts/start.sh 

# RUN echo "\nx11vnc -display :99 -forever -listen 0.0.0.0 -rfbport 6080 & \n" >> ./scripts/start.sh

CMD ["./scripts/start.sh"]