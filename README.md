# 🕵️‍♂️ Catch the Thief – City Grid Game

A real-time strategy grid game built with **Pygame**, where a police officer must **catch a thief** navigating through a dynamically generated city grid. The game includes **AI pathfinding** using BFS and A\*, **difficulty levels**, **power-ups**, and both **manual** and **auto** police control modes.

![Game Screenshot](preview.gif) <!-- Optionally add a GIF or screenshot of the game -->

---

## 🎮 Features

* 🏙️ **Dynamic Grid:** City map with obstacles and paths regenerated if AI gets stuck
* 🧠 **Smart Thief AI:** Thief uses a mix of A\*, random movement, and evasive behavior
* 🚔 **Police AI:** Uses BFS and A\* to navigate intelligently
* ⚡ **Power-Ups:** Activate speed boost for police on pickup
* 🕹️ **Auto/Manual Control:** Switch police between manual (WASD / arrow keys) and auto mode
* ⏸️ **Pause Feature:** Press `P` to pause/resume the game
* 🎚️ **Difficulty Levels:** Easy, Medium, Hard – affects thief intelligence
* 🔊 **Sound Effects:** Optional generated sound effects on click/capture
* 💡 **Optimized for Desktop & Web:** Handles audio limitations for platforms like WebAssembly

---

## 🚀 Getting Started

### ✅ Requirements

* Python 3.7+
* Pygame
* NumPy

### 📦 Installation

```bash
git clone https://github.com/your-username/catch-the-thief.git
cd catch-the-thief
pip install -r requirements.txt
```

### ▶️ Run the Game

```bash
python main.py
```

---

## 🧠 AI Logic

### Thief Movement

* **Random Walk**: With higher probability in Easy mode
* **A\* Pathfinding**: Used to evade police when nearby
* **Stay Still**: Small chance to stay in place

### Police Movement

* **Auto Mode**: Uses BFS with fallback to A\* if needed
* **Manual Mode**: Controlled by arrow keys / WASD
* **Grid Reset**: Triggers if either character is stuck for 10+ turns

---

## 🎨 Controls

| Key                    | Action                            |
| ---------------------- | --------------------------------- |
| `W/A/S/D` or `↑/←/↓/→` | Move police (manual mode only)    |
| `M`                    | Toggle police auto/manual mode    |
| `P`                    | Pause/resume the game             |
| Mouse                  | Click to select difficulty & play |

---

## 📂 Project Structure

```bash
📁 catch-the-thief/
├── main.py               # Main game file
├── README.md             # Project documentation
└── requirements.txt      # Dependencies
```

## ⚙️ Customization Ideas

* Add sound/music assets
* Include levels or increasing grid size
* Multiplayer or 2-player mode
* Track high scores with a database

